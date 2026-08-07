#!/usr/bin/env python3
"""Unit tests for scripts/schema.py — contract v1 validators and ingest rules.

Self-running (viva's convention): `python3 tests/test_schema.py` prints OK.
"""
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import schema


def _invocation():
    return {
        "contract_version": 1,
        "judge": "security-auditor",
        "mount": "acceptance",
        "artifact": {"kind": "changeset", "base": "a1b2c3d", "head": "e4f5a6b"},
        "standard": {"name": "security-checklist", "version": "2026-07"},
    }


# The compact example from docs/findings-contract.md §4, verbatim — if the doc's
# own example stops validating, doc and code have drifted.
def _findings_doc():
    return {
        "contract_version": 1,
        "judge": "security-auditor",
        "mount": "acceptance",
        "artifact": {"kind": "changeset", "base": "a1b2c3d", "head": "e4f5a6b"},
        "standard": {"name": "security-checklist", "version": "2026-07"},
        "findings": [
            {
                "dimension": "injection",
                "tier": "critical",
                "summary": "Unsanitized branch name reaches shell in release script",
                "locus": {"path": "scripts/release.sh", "line": 42},
                "anchor": (
                    "Command injection (security-checklist): $BRANCH interpolated "
                    "into eval at scripts/release.sh:42, reachable from PR title"
                ),
                "basis": "sourced",
                "level": "high",
                "failure_scenario": (
                    "PR titled `x; rm -rf .` becomes the branch slug; "
                    "release run executes it"
                ),
                "recommendation": (
                    "Quote the variable and validate the slug against "
                    "^[a-z0-9-]+$ at entry"
                ),
                "receipts": ["sha256:9f2c..."],
            }
        ],
        "coverage": (
            "Reviewed both modified scripts and the workflow file. Auth and "
            "secrets surfaces unchanged; did not execute the target. No receipts "
            "existed for the lint run cited in the PR body."
        ),
    }


def _raises(fn, arg, fragment):
    try:
        fn(arg)
    except ValueError as e:
        assert fragment in str(e), f"expected {fragment!r} in {e}"
        return
    raise AssertionError(f"expected ValueError containing {fragment!r}")


# ── validate_invocation ───────────────────────────────────────────────────────
def test_valid_invocation_passes():
    schema.validate_invocation(_invocation())


def test_invocation_optional_fields():
    inv = _invocation()
    inv["artifact"]["pr"] = "https://github.com/jacquardlabs/gauntlet/pull/9"
    inv["artifact"]["root"] = "/tmp/worktree"
    inv["context"] = ["PRODUCT.md", "CLAUDE.md"]
    inv["receipts_path"] = ".evidence/branch.jsonl"
    schema.validate_invocation(inv)


def test_invocation_document_artifact():
    inv = _invocation()
    inv["artifact"] = {"kind": "document", "path": "docs/design/auth.md"}
    inv["mount"] = "intake"
    schema.validate_invocation(inv)


def test_invocation_repository_artifact_at_posture():
    inv = _invocation()
    inv["artifact"] = {"kind": "repository", "ref": "a1b2c3d", "root": "/srv/repo"}
    inv["mount"] = "posture"
    schema.validate_invocation(inv)


#: The required field each artifact kind owns. Keyed by kind so a kind added to
#: the enum without a branch in `_validate_artifact` fails here rather than
#: inheriting whatever the previous branch happened to check.
REQUIRED_BY_KIND = {
    "changeset": "artifact.base",
    "document": "artifact.path",
    "repository": "artifact.ref",
}


def test_every_artifact_kind_validates_its_own_required_field():
    assert set(REQUIRED_BY_KIND) == set(schema.ARTIFACT_KINDS), (
        "an artifact kind was added to the enum without deciding what it requires"
    )
    for kind, fragment in REQUIRED_BY_KIND.items():
        inv = _invocation()
        inv["artifact"] = {"kind": kind}
        _raises(schema.validate_invocation, inv, fragment)


def test_repository_artifact_is_not_validated_as_a_document():
    """The regression the explicit branches exist for: while `document` was the
    fall-through, a repository artifact was checked for `path` and a `ref`-only
    payload was rejected for the wrong reason."""
    inv = _invocation()
    inv["artifact"] = {"kind": "repository", "path": "docs/design/auth.md"}
    _raises(schema.validate_invocation, inv, "artifact.ref")


def test_invocation_rejections():
    _raises(schema.validate_invocation, [], "JSON object")
    for mutate, fragment in [
        (lambda d: d.update(contract_version=2), "does not match"),
        (lambda d: d.update(contract_version=True), "must be an integer"),
        (lambda d: d.update(judge=""), "invocation.judge"),
        (lambda d: d.update(mount="review"), "invocation.mount"),
        (lambda d: d.update(artifact={"kind": "pr"}), "artifact.kind"),
        (lambda d: d["artifact"].pop("head"), "artifact.head"),
        (lambda d: d.update(artifact={"kind": "document"}), "artifact.path"),
        (lambda d: d.update(standard={}), "standard.name"),
        (lambda d: d.update(context="PRODUCT.md"), "list of strings"),
    ]:
        inv = _invocation()
        mutate(inv)
        _raises(schema.validate_invocation, inv, fragment)


# ── validate_findings ─────────────────────────────────────────────────────────
def test_doc_example_validates():
    schema.validate_findings(_findings_doc())


def test_clean_result_is_valid():
    doc = _findings_doc()
    doc["findings"] = []
    schema.validate_findings(doc)


def test_document_locus_variants():
    doc = _findings_doc()
    doc["findings"][0]["locus"] = {"section": "Rollback plan"}
    schema.validate_findings(doc)
    doc["findings"][0]["locus"] = {"section": "Options", "cell": "cost:Auth0"}
    schema.validate_findings(doc)


def test_findings_rejections():
    for mutate, fragment in [
        (lambda d: d.pop("coverage"), "findings.coverage"),
        (lambda d: d.update(findings={}), "must be a list"),
        (lambda d: d["findings"][0].pop("dimension"), "dimension"),
        (lambda d: d["findings"][0].update(tier="blocker"), "tier"),
        (lambda d: d["findings"][0].update(basis="confirmed"), "basis"),
        (lambda d: d["findings"][0].update(level="certain"), "level"),
        (lambda d: d["findings"][0].update(locus={}), "at least one"),
        (lambda d: d["findings"][0]["locus"].update(line="42"), "locus.line"),
        (lambda d: d["findings"][0].update(receipts="sha256:x"), "receipts"),
    ]:
        doc = _findings_doc()
        mutate(doc)
        _raises(schema.validate_findings, doc, fragment)


# ── normalize_findings ────────────────────────────────────────────────────────
def test_anchored_critical_untouched():
    doc = _findings_doc()
    out, notes = schema.normalize_findings(doc)
    assert out["findings"][0]["tier"] == "critical"
    assert notes == []


def test_anchorless_critical_demoted():
    doc = _findings_doc()
    doc["findings"][0]["anchor"] = "   "
    out, notes = schema.normalize_findings(doc)
    assert out["findings"][0]["tier"] == "important"
    assert len(notes) == 1 and "anchor-or-demote" in notes[0]


def test_taste_caps_at_track():
    doc = _findings_doc()
    doc["findings"][0].update(basis="taste", tier="important")
    out, notes = schema.normalize_findings(doc)
    assert out["findings"][0]["tier"] == "track"
    assert len(notes) == 1 and "taste-caps-at-track" in notes[0]


def test_taste_critical_lands_at_track_with_both_notes():
    doc = _findings_doc()
    doc["findings"][0].update(basis="taste")
    doc["findings"][0].pop("anchor")
    out, notes = schema.normalize_findings(doc)
    assert out["findings"][0]["tier"] == "track"
    assert len(notes) == 2


def test_taste_at_track_needs_no_note():
    doc = _findings_doc()
    doc["findings"][0].update(basis="taste", tier="track")
    out, notes = schema.normalize_findings(doc)
    assert out["findings"][0]["tier"] == "track"
    assert notes == []


def test_normalize_is_pure():
    doc = _findings_doc()
    doc["findings"][0]["anchor"] = ""
    before = copy.deepcopy(doc)
    schema.normalize_findings(doc)
    assert doc == before


# ── quote-or-demote (document artifacts, #44) ─────────────────────────────────
DOCUMENT_TEXT = (
    "# Migration plan\n"
    "\n"
    "## Step 3 — cutover\n"
    "\n"
    "Flip the read path to the new store\n"
    "and watch error rates for one hour.\n"
)


def _document_findings_doc(anchor):
    doc = _findings_doc()
    doc["mount"] = "intake"
    doc["artifact"] = {"kind": "document", "path": "docs/plan.md"}
    doc["findings"][0]["locus"] = {"section": "Step 3 — cutover"}
    doc["findings"][0]["anchor"] = anchor
    return doc


def test_document_critical_with_verbatim_quote_untouched():
    doc = _document_findings_doc(
        'Step names no rollback: "Flip the read path to the new store" is one-way'
    )
    out, notes = schema.normalize_findings(doc, DOCUMENT_TEXT)
    assert out["findings"][0]["tier"] == "critical"
    assert notes == []


def test_document_critical_with_unquoted_anchor_demoted():
    doc = _document_findings_doc(
        "Step 3 names no rollback path and no abort criterion"
    )
    out, notes = schema.normalize_findings(doc, DOCUMENT_TEXT)
    assert out["findings"][0]["tier"] == "important"
    assert len(notes) == 1 and "quote-or-demote" in notes[0]
    assert "quotes nothing" in notes[0]


def test_document_critical_with_fabricated_quote_demoted():
    doc = _document_findings_doc(
        'Plan promises "roll back within five minutes" but names no mechanism'
    )
    out, notes = schema.normalize_findings(doc, DOCUMENT_TEXT)
    assert out["findings"][0]["tier"] == "important"
    assert len(notes) == 1 and "quote-or-demote" in notes[0]
    assert "does not appear" in notes[0]


def test_reflowed_quote_still_matches():
    """The document breaks the line mid-sentence; the judge quotes it as one
    line. A hard string match would demote a true quote over a reflow."""
    doc = _document_findings_doc(
        'No success signal: "Flip the read path to the new store and watch '
        'error rates for one hour." commits to nothing checkable'
    )
    out, notes = schema.normalize_findings(doc, DOCUMENT_TEXT)
    assert out["findings"][0]["tier"] == "critical"
    assert notes == []


def test_curly_quotes_match_too():
    doc = _document_findings_doc(
        "No success signal: “watch error rates for one hour” names no threshold"
    )
    out, notes = schema.normalize_findings(doc, DOCUMENT_TEXT)
    assert out["findings"][0]["tier"] == "critical"
    assert notes == []


def test_one_true_quote_suffices_beside_a_foreign_one():
    """A drifted-seam anchor quotes both sides; the side from another file is
    not in the document and must not demote the finding."""
    doc = _document_findings_doc(
        'Plan says "watch error rates for one hour" but the runbook says '
        '"page after five minutes"'
    )
    out, notes = schema.normalize_findings(doc, DOCUMENT_TEXT)
    assert out["findings"][0]["tier"] == "critical"
    assert notes == []


def test_quote_rule_skipped_without_document_text():
    """An unreadable document skips the check — demoting every critical against
    text nobody saw would be the checker fabricating, not the judge."""
    doc = _document_findings_doc("Step 3 names no rollback path")
    out, notes = schema.normalize_findings(doc)
    assert out["findings"][0]["tier"] == "critical"
    assert notes == []


def test_quote_rule_never_fires_on_changeset_or_repository():
    for artifact in (
        {"kind": "changeset", "base": "a1b2c3d", "head": "e4f5a6b"},
        {"kind": "repository", "ref": "a1b2c3d"},
    ):
        doc = _findings_doc()
        doc["artifact"] = artifact
        doc["findings"][0]["anchor"] = "an anchor with no quoted span at all"
        out, notes = schema.normalize_findings(doc, DOCUMENT_TEXT)
        assert out["findings"][0]["tier"] == "critical", artifact["kind"]
        assert notes == []


def test_anchorless_document_critical_gets_the_presence_note_only():
    doc = _document_findings_doc("   ")
    out, notes = schema.normalize_findings(doc, DOCUMENT_TEXT)
    assert out["findings"][0]["tier"] == "important"
    assert len(notes) == 1 and "anchor-or-demote" in notes[0]


def test_taste_document_critical_lands_at_track_after_quote_demotion():
    doc = _document_findings_doc("Step 3 names no rollback path")
    doc["findings"][0]["basis"] = "taste"
    out, notes = schema.normalize_findings(doc, DOCUMENT_TEXT)
    assert out["findings"][0]["tier"] == "track"
    assert len(notes) == 2


def main():
    tests = [
        (name, fn)
        for name, fn in sorted(globals().items())
        if name.startswith("test_") and callable(fn)
    ]
    for name, fn in tests:
        fn()
        print(f"  {name}")
    print(f"OK ({len(tests)} tests)")


if __name__ == "__main__":
    main()
