#!/usr/bin/env python3
"""Unit tests for scripts/report.py — the consumer's bookkeeping half.

Self-running: `python3 tests/test_report.py` prints OK.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import report  # noqa: E402 — sys.path must be set first


def _doc(judge="security-auditor", findings=None, coverage="Checked both files."):
    return {
        "contract_version": 1,
        "judge": judge,
        "mount": "acceptance",
        "artifact": {"kind": "changeset", "base": "a1b2c3d4e5f6", "head": "f6e5d4c3b2a1"},
        "standard": {"name": "security-checklist"},
        "findings": findings if findings is not None else [],
        "coverage": coverage,
    }


def _finding(tier="important", judge_dim="injection", path="src/a.py", line=10, **kw):
    finding = {
        "dimension": judge_dim,
        "tier": tier,
        "summary": f"a {tier} thing",
        "locus": {"path": path, "line": line},
        "basis": "sourced",
    }
    if tier == "critical":
        finding["anchor"] = "a checkable fact at src/a.py:10"
    finding.update(kw)
    return finding


def _write(directory, *docs):
    for i, doc in enumerate(docs):
        (Path(directory) / f"{i}-{doc['judge']}.json").write_text(json.dumps(doc))


def _has(items, fragment):
    assert any(fragment in i for i in items), f"expected {fragment!r} in {items}"


# ── load ──────────────────────────────────────────────────────────────────────
def test_loads_and_normalizes():
    with tempfile.TemporaryDirectory() as tmp:
        _write(tmp, _doc(findings=[_finding()]))
        docs, notes, failures = report.load(Path(tmp))
        assert len(docs) == 1 and notes == [] and failures == []


def test_ingest_rules_run_at_load_and_are_reported():
    unanchored = _finding(tier="critical")
    del unanchored["anchor"]
    with tempfile.TemporaryDirectory() as tmp:
        _write(tmp, _doc(findings=[unanchored]))
        docs, notes, _ = report.load(Path(tmp))
        assert docs[0]["findings"][0]["tier"] == "important"
        _has(notes, "anchor-or-demote")
        _has(notes, "security-auditor:")


def test_malformed_document_is_a_failure_not_a_silent_drop():
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "broken.json").write_text("{not json")
        (Path(tmp) / "invalid.json").write_text(json.dumps({"contract_version": 1}))
        # A reply truncated mid-multibyte: UnicodeDecodeError is a ValueError, not
        # an OSError, and used to escape load() and take every other lane with it.
        (Path(tmp) / "truncated.json").write_bytes(b'{"summary": "em dash \xe2\x80')
        docs, _, failures = report.load(Path(tmp))
        assert docs == []
        assert len(failures) == 3
        _has(failures, "could not be read as JSON")
        _has(failures, "does not satisfy the findings contract")


def test_a_judge_that_wrote_nothing_is_a_failure_not_an_absence():
    with tempfile.TemporaryDirectory() as tmp:
        _write(tmp, _doc("security-auditor"))
        docs, _, failures = report.load(
            Path(tmp), ["security-auditor", "test-auditor"]
        )
        assert len(docs) == 1
        _has(failures, "test-auditor: dispatched but wrote no findings document")


def _document_run(tmp, anchor, text="The plan promises a rollback in one step.\n"):
    """A findings dir plus the judged document it cites, under one root."""
    (Path(tmp) / "plan.md").write_text(text)
    finding = _finding(tier="critical", path=None)
    finding["locus"] = {"section": "Rollback"}
    finding["anchor"] = anchor
    doc = _doc("product-reviewer", [finding])
    doc["mount"] = "intake"
    doc["artifact"] = {"kind": "document", "path": "plan.md", "root": tmp}
    findings_dir = Path(tmp) / "findings"
    findings_dir.mkdir()
    _write(findings_dir, doc)
    return findings_dir


def test_load_verifies_a_document_quote_against_artifact_root():
    with tempfile.TemporaryDirectory() as tmp:
        dir_ = _document_run(tmp, 'Plan claims "a rollback in one step" untested')
        docs, notes, failures = report.load(dir_)
        assert docs[0]["findings"][0]["tier"] == "critical"
        assert notes == [] and failures == []


def test_load_demotes_a_fabricated_document_quote():
    with tempfile.TemporaryDirectory() as tmp:
        dir_ = _document_run(tmp, 'Plan claims "we can revert instantly" untested')
        docs, notes, failures = report.load(dir_)
        assert docs[0]["findings"][0]["tier"] == "important"
        _has(notes, "quote-or-demote")
        _has(notes, "product-reviewer:")
        assert failures == []


def test_an_unreadable_document_skips_the_quote_check_and_names_the_skip():
    """#68. The fail-open is right — demoting every critical against text nobody
    saw would be the checker fabricating. Rendering that run identically to one
    where every anchor was checked and passed is not: this used to assert
    `notes == []`, which pinned exactly that silence."""
    with tempfile.TemporaryDirectory() as tmp:
        dir_ = _document_run(tmp, 'Plan claims "we can revert instantly" untested')
        (Path(tmp) / "plan.md").unlink()
        docs, notes, failures = report.load(dir_)
        assert docs[0]["findings"][0]["tier"] == "critical", "the fail-open stands"
        assert failures == [], "a skipped check is not an unjudged lane"
        _has(notes, "quote-check-skipped")
        _has(notes, "product-reviewer:")
        _has(notes, "plan.md")
        _has(notes, "No such file or directory")


def test_an_undecodable_document_names_why_it_could_not_be_read():
    """The other read failure: a latin-1 document raises UnicodeDecodeError, not
    OSError, and the reader is owed which one happened."""
    with tempfile.TemporaryDirectory() as tmp:
        dir_ = _document_run(tmp, 'Plan claims "we can revert instantly" untested')
        (Path(tmp) / "plan.md").write_bytes(b"rollback in one \xe9tape\n")
        _, notes, failures = report.load(dir_)
        assert failures == []
        _has(notes, "quote-check-skipped")
        _has(notes, "codec can't decode")


# ── de-framing a fenced reply (#61) ───────────────────────────────────────────
def _fenced(text, info="json", lead="", tail=""):
    return f"{lead}```{info}\n{text}\n```\n{tail}"


def test_a_fenced_reply_is_unwrapped_and_the_unwrap_is_named():
    """#61: two lanes in fifteen were total losses to a fence, at opus and
    sonnet alike, with 23 byte-identical copies of the instruction already
    forbidding it. A fence is transport packaging, which the contract puts out
    of scope — so it is stripped, and named, because a silent unwrap would
    recover the lane by trading one invisible accommodation for another."""
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "test-auditor.json").write_text(
            _fenced(
                json.dumps(_doc("test-auditor", [_finding()]), indent=2),
                lead="Here is the findings document:\n\n",
            )
        )
        docs, notes, failures = report.load(Path(tmp), ["test-auditor"])
        assert failures == [], "the lane is recovered, not lost"
        assert docs[0]["findings"][0]["summary"] == "a important thing"
        _has(notes, "fence-unwrapped")
        _has(notes, "test-auditor:")


def test_a_bare_fence_with_no_info_string_is_a_wrapper_too():
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "a.json").write_text(_fenced(json.dumps(_doc()), info=""))
        docs, notes, failures = report.load(Path(tmp))
        assert len(docs) == 1 and failures == []
        _has(notes, "fence-unwrapped")


def test_a_bare_valid_document_is_untouched_by_the_unwrap():
    """Parse first, de-frame only on a parse failure. The ordinary path is the
    one it always was, byte for byte, and no note claims an accommodation that
    never happened."""
    with tempfile.TemporaryDirectory() as tmp:
        _write(tmp, _doc(findings=[_finding()]))
        docs, notes, failures = report.load(Path(tmp))
        assert len(docs) == 1 and notes == [] and failures == []
        assert docs[0]["findings"][0] == _finding(), "no bytes altered"


def test_a_reply_that_still_does_not_parse_after_unwrapping_is_a_failure():
    """Unwrapping is de-framing, never repair: what was inside the fence is
    parsed as it came, and a lane whose document is malformed is lost exactly as
    it is today."""
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "a.json").write_text(_fenced('{"judge": '))
        docs, notes, failures = report.load(Path(tmp))
        assert docs == [] and notes == []
        _has(failures, "even after unwrapping")


def test_a_fence_that_does_not_wrap_the_whole_reply_is_named_not_stripped():
    """Content after the close is the judge's own, and dropping it would be the
    repair this deliberately is not. The failure says a fence was seen, so a
    shape this ruling did not cover surfaces in the next run's report rather
    than reading as an ordinary parse failure."""
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "a.json").write_text(
            _fenced(json.dumps(_doc()), tail="\nLet me know if you want more detail.\n")
        )
        docs, _, failures = report.load(Path(tmp))
        assert docs == []
        _has(failures, "did not wrap the whole reply")


def test_an_unfenced_unparseable_reply_reads_the_same_as_before():
    """No fence anywhere, so nothing about fences enters the failure line."""
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "a.json").write_text("{not json")
        _, _, failures = report.load(Path(tmp))
        _has(failures, "could not be read as JSON")
        assert "code fence" not in failures[0]


def test_a_lane_nobody_dispatched_is_ingested_and_named():
    """The mirror of the missing-lane failure. A scratch directory reused across
    runs leaves a stale document behind; it agrees about the artifact, so the
    artifact guard never sees it, and its findings join the tally unannounced."""
    with tempfile.TemporaryDirectory() as tmp:
        _write(tmp, _doc("security-auditor"), _doc("test-auditor"))
        docs, notes, failures = report.load(Path(tmp), ["security-auditor"])
        assert len(docs) == 2 and failures == [], "the findings are kept, not dropped"
        _has(notes, "undispatched-lane")
        _has(notes, "test-auditor:")
        _, no_roster, _ = report.load(Path(tmp))
        assert no_roster == [], "without a roster there is nothing to compare against"


def test_a_mistyped_document_root_is_a_failure_not_a_crash():
    """Regression: `{"root": 123}` used to pass validate_findings, then
    Path(123) raised TypeError inside load() — one bad lane taking every
    other lane's findings down with it."""
    with tempfile.TemporaryDirectory() as tmp:
        doc = _doc("product-reviewer")
        doc["artifact"] = {"kind": "document", "path": "plan.md", "root": 123}
        _write(tmp, doc)
        docs, _, failures = report.load(Path(tmp))
        assert docs == []
        _has(failures, "does not satisfy the findings contract")
        _has(failures, "artifact.root")


def test_changeset_criticals_never_face_the_quote_rule():
    """An anchor with no quoted span is fine on code — the quote rule is a
    document-artifact rule, not a new anchor grammar for the fleet."""
    with tempfile.TemporaryDirectory() as tmp:
        _write(tmp, _doc(findings=[_finding(tier="critical")]))
        docs, notes, _ = report.load(Path(tmp))
        assert docs[0]["findings"][0]["tier"] == "critical"
        assert notes == []


def test_documents_must_agree_about_the_artifact():
    other = _doc("test-auditor")
    other["artifact"] = {"kind": "changeset", "base": "999999999999", "head": "888888888888"}
    with tempfile.TemporaryDirectory() as tmp:
        _write(tmp, _doc("security-auditor"), other)
        docs, _, failures = report.load(Path(tmp))
        assert [d["judge"] for d in docs] == ["security-auditor"]
        _has(failures, "judged a different artifact")


# ── merging across lanes ──────────────────────────────────────────────────────
def test_two_lanes_on_one_locus_become_one_finding():
    a = _doc("code-auditor", [_finding("critical", path="src/a.py", line=10)])
    b = _doc("operability-auditor", [_finding("important", path="src/a.py", line=10)])
    merged = report.flatten([a, b])
    assert len(merged) == 1
    assert merged[0]["tier"] == "critical", "the most severe tier survives"
    assert merged[0]["judges"] == ["code-auditor", "operability-auditor"]


def test_merge_keeps_the_other_lanes_recommendation():
    a = _doc("code-auditor", [_finding("important", path="a.py", recommendation="do X")])
    b = _doc("test-auditor", [_finding("important", path="a.py", recommendation="do Y")])
    merged = report.flatten([a, b])[0]
    assert merged["recommendation"] in ("do X", "do Y")
    assert merged["also_recommended"], "the losing lane's advice is not discarded"


def test_merge_prefers_the_anchored_finding_among_equals():
    plain = _finding("important", path="a.py")
    anchored = _finding("important", path="a.py")
    anchored["anchor"] = "a checkable fact"
    merged = report.flatten([_doc("x-auditor", [plain]), _doc("y-auditor", [anchored])])[0]
    assert merged.get("anchor") == "a checkable fact"


def test_different_lines_are_never_merged():
    a = _doc("code-auditor", [_finding(path="a.py", line=10)])
    b = _doc("test-auditor", [_finding(path="a.py", line=11)])
    assert len(report.flatten([a, b])) == 2


def test_document_loci_are_never_merged():
    """A section name is too coarse to prove two lanes mean the same defect."""
    def mk(judge):
        return _doc(judge, [{
            "dimension": "fit", "tier": "important", "summary": f"{judge} says so",
            "locus": {"section": "Rollback"}, "basis": "inferred",
        }])

    assert len(report.flatten([mk("a-auditor"), mk("b-auditor")])) == 2


# ── ordering ──────────────────────────────────────────────────────────────────
def test_flatten_orders_by_tier_then_judge_then_locus():
    docs = [
        _doc("test-auditor", [_finding("track", path="z.py"), _finding("critical")]),
        _doc("code-auditor", [_finding("important", path="b.py"),
                              _finding("important", path="a.py")]),
    ]
    order = [(f["tier"], f["_judge"], f["locus"]["path"]) for f in report.flatten(docs)]
    assert order == [
        ("critical", "test-auditor", "src/a.py"),
        ("important", "code-auditor", "a.py"),
        ("important", "code-auditor", "b.py"),
        ("track", "test-auditor", "z.py"),
    ]


def test_ordering_does_not_depend_on_input_order():
    """The old version of this compared one pure call to itself, which passes
    under any deterministic key including a wrong one."""
    a = _doc("b-judge", [_finding(path="y.py"), _finding("critical")])
    b = _doc("a-judge", [_finding("track", path="z.py"), _finding(path="x.py")])
    forward = [(f["_judge"], f["locus"]["path"]) for f in report.flatten([a, b])]
    reverse = [(f["_judge"], f["locus"]["path"]) for f in report.flatten([b, a])]
    assert forward == reverse
    assert forward[0] == ("b-judge", "src/a.py"), "critical must sort first"


def test_counts_covers_every_tier():
    # Distinct loci: same-locus findings now merge, which is a different test.
    findings = report.flatten([_doc(findings=[
        _finding("critical", path="a.py", line=1),
        _finding("track", path="b.py", line=2),
    ])])
    assert report.counts(findings) == {"critical": 1, "important": 0, "track": 1}


# ── markdown ──────────────────────────────────────────────────────────────────
def test_markdown_reports_tally_judges_and_coverage():
    out = report.render_markdown([_doc(findings=[_finding("critical")])], [], [])
    assert "1 critical · 0 important · 0 track" in out
    assert "security-auditor" in out
    assert "## Coverage" in out
    assert "Checked both files." in out


def test_markdown_names_unjudged_lanes_loudly():
    out = report.render_markdown([_doc()], [], ["x.json: exploded"])
    assert "## Judges that did not report" in out
    assert "Absence of findings here is not a clean result" in out


def test_markdown_names_demotions_and_checks_that_did_not_run():
    """One section for every ingest accommodation. The heading is no longer
    "Recorded differently than claimed": a check that never ran did not record
    anything differently, and filing it under that heading would hide it."""
    out = report.render_markdown([_doc()], [
        "security-auditor: anchor-or-demote: x",
        "product-reviewer: quote-check-skipped: 'plan.md' was not read at ingest",
        "test-auditor: fence-unwrapped: test-auditor.json arrived inside a code fence",
    ], [])
    assert "## What ingest changed or could not check" in out
    for note in ("anchor-or-demote", "quote-check-skipped", "fence-unwrapped"):
        assert note in out


def test_markdown_survives_a_document_locus():
    doc = _doc(findings=[{
        "dimension": "grounds", "tier": "track", "summary": "cell has no receipt",
        "locus": {"section": "Options", "cell": "cost:Auth0"}, "basis": "inferred",
    }])
    assert "Options · cost:Auth0" in report.render_markdown([doc], [], [])


def test_empty_findings_still_renders_coverage():
    out = report.render_markdown([_doc()], [], [])
    assert "0 critical · 0 important · 0 track" in out
    assert "Checked both files." in out


def test_markdown_headers_a_posture_run_with_its_ref():
    """A repository artifact carries no base/head and no path, so the header
    would have read `?` if it fell through to the document branch."""
    doc = _doc()
    doc["mount"] = "posture"
    doc["artifact"] = {"kind": "repository", "ref": "a1b2c3d4e5f6a7b8"}
    out = report.render_markdown([doc], [], [])
    assert "# Gauntlet — repository at a1b2c3d4e5f6" in out
    assert "?" not in out.splitlines()[0]


def test_posture_findings_never_try_to_anchor_to_a_diff():
    """`render_pr_comments` resolves anchorable lines from base..head; a
    repository artifact has neither, so every finding rides in the summary
    rather than being posted against a diff that was never computed."""
    doc = _doc(findings=[_finding(tier="critical", anchor="a real anchor")])
    doc["mount"] = "posture"
    doc["artifact"] = {"kind": "repository", "ref": "a1b2c3d4e5f6"}
    payload = json.loads(report.render_pr_comments([doc], [], []))
    assert payload["comments"] == []
    assert "a critical thing" in payload["summary"]


# ── diff anchoring ────────────────────────────────────────────────────────────
def _repo_with_diff(tmp):
    """A throwaway repo whose HEAD diff touches src/a.py line 10 only."""

    def run(*args):
        return subprocess.run(args, cwd=tmp, capture_output=True, check=True)

    def sha():
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=tmp, capture_output=True, text=True
        ).stdout.strip()

    run("git", "init", "-q")
    run("git", "config", "user.email", "t@t")
    run("git", "config", "user.name", "t")
    src = Path(tmp) / "src"
    src.mkdir()
    (src / "a.py").write_text("\n".join(f"line {i}" for i in range(1, 21)) + "\n")
    (Path(tmp) / "untouched.md").write_text("stable\n" * 5)
    run("git", "add", "-A")
    run("git", "commit", "-qm", "base")
    base = sha()

    lines = (src / "a.py").read_text().splitlines()
    lines[9] = "line 10 CHANGED"
    (src / "a.py").write_text("\n".join(lines) + "\n")
    run("git", "commit", "-aqm", "head")
    return base, sha()


def test_diff_lines_reports_only_changed_lines():
    with tempfile.TemporaryDirectory() as tmp:
        base, head = _repo_with_diff(tmp)
        valid = report.diff_lines(base, head, tmp)
        assert valid["src/a.py"] == {10}
        assert "untouched.md" not in valid


def test_diff_lines_is_empty_when_git_cannot_run():
    """Empty means anchor nothing, never anchor everything — a bad guess here
    422s the entire review, losing every finding rather than one."""
    with tempfile.TemporaryDirectory() as tmp:
        assert report.diff_lines("nope", "alsonope", tmp) == {}


# ── pr comments ───────────────────────────────────────────────────────────────
def test_pr_comments_anchor_only_to_lines_the_diff_contains():
    with tempfile.TemporaryDirectory() as tmp:
        base, head = _repo_with_diff(tmp)
        artifact = {"kind": "changeset", "base": base, "head": head, "root": tmp}
        on_diff = _finding("critical", path="src/a.py", line=10)
        off_diff = _finding("critical", path="src/a.py", line=17)
        doc = _doc(findings=[on_diff, off_diff])
        doc["artifact"] = artifact
        payload = json.loads(report.render_pr_comments([doc], [], []))
        assert len(payload["comments"]) == 1
        assert payload["comments"][0]["line"] == 10
        assert "src/a.py:17" in payload["summary"]


def test_comment_leads_with_the_claim_then_the_fix():
    f = dict(_finding("important", path="a.py"), recommendation="do the thing")
    f["_judge"] = "code-auditor"
    body = report._comment_body(f)
    assert body.startswith("**a important thing**"), "the claim leads, not the metadata"
    visible = body.split("<details>")[0]
    assert "do the thing" in visible, "the fix is visible without clicking"


def test_the_anchor_reaches_the_reader():
    """Regression: the renderer used to drop `anchor` entirely, leaving a
    merge-blocking verdict with its evidence invisible."""
    f = dict(_finding("critical", path="a.py"), _judge="security-auditor")
    body = report._comment_body(f)
    assert "**Anchor.**" in body
    assert f["anchor"] in body


def test_long_evidence_is_collapsed_not_deleted():
    f = dict(_finding("important", path="a.py"), _judge="x-auditor",
             failure_scenario="a" * 400)
    body = report._comment_body(f)
    assert "<details>" in body
    assert "a" * 400 in body, "collapsed, never dropped"
    assert "a" * 400 not in body.split("<details>")[0]


def test_grounds_and_lanes_ride_on_the_disclosure_line():
    f = dict(_finding("important", path="a.py"), _judge="code-auditor",
             judges=["code-auditor", "test-auditor"], level="low", basis="taste",
             failure_scenario="something breaks")
    body = report._comment_body(f)
    caption = body.split("<summary>")[1].split("</summary>")[0]
    assert "code-auditor + test-auditor" in caption
    assert "taste/low" in caption and "important" in caption


def test_a_finding_with_no_evidence_needs_no_disclosure():
    f = {"dimension": "d", "tier": "track", "summary": "small thing",
         "locus": {"path": "a.py", "line": 1}, "basis": "taste", "_judge": "x-auditor"}
    body = report._comment_body(f)
    assert "<details>" not in body
    assert "_x-auditor · track" in body


def test_track_findings_never_post_inline():
    """A tier contradicting its own channel: `track` means revisit later, an
    inline comment demands attention on that line now."""
    with tempfile.TemporaryDirectory() as tmp:
        base, head = _repo_with_diff(tmp)
        doc = _doc(findings=[
            _finding("track", path="src/a.py", line=10),
            _finding("important", path="src/a.py", line=10, judge_dim="other"),
        ])
        doc["artifact"] = {"kind": "changeset", "base": base, "head": head, "root": tmp}
        payload = json.loads(report.render_pr_comments([doc], [], []))
        assert all("TRACK" not in c["body"] for c in payload["comments"])


def test_a_finding_about_an_unchanged_file_rides_in_the_summary():
    """The case that matters: 'you changed X and never updated Y' has no diff
    line, and is exactly where the highest-tier findings live."""
    with tempfile.TemporaryDirectory() as tmp:
        base, head = _repo_with_diff(tmp)
        doc = _doc(findings=[_finding("critical", path="untouched.md", line=3)])
        doc["artifact"] = {"kind": "changeset", "base": base, "head": head, "root": tmp}
        payload = json.loads(report.render_pr_comments([doc], [], []))
        assert payload["comments"] == []
        assert "no diff line to anchor to" in payload["summary"]
        assert "CRITICAL" in payload["summary"]
        assert "untouched.md:3" in payload["summary"]


def test_unanchored_findings_ride_in_the_summary_rather_than_vanishing():
    doc = _doc(findings=[{
        "dimension": "fit", "tier": "important", "summary": "brief omits rollback",
        "locus": {"section": "Rollback"}, "basis": "inferred",
        "recommendation": "name the rollback path",
    }])
    payload = json.loads(report.render_pr_comments([doc], [], []))
    assert payload["comments"] == []
    assert "no diff line to anchor to" in payload["summary"]
    assert "brief omits rollback" in payload["summary"]
    assert "name the rollback path" in payload["summary"]


def test_pr_summary_carries_failures_notes_and_coverage():
    payload = json.loads(report.render_pr_comments(
        [_doc()], ["security-auditor: taste-caps-at-track: x"], ["y.json: exploded"]))
    assert "did not report" in payload["summary"]
    assert "taste-caps-at-track" in payload["summary"]
    assert "Coverage" in payload["summary"]


# ── the CLI ───────────────────────────────────────────────────────────────────
def _run(*args):
    proc = subprocess.run(
        [sys.executable, str(REPO / "scripts/report.py"), *args],
        capture_output=True, text=True,
    )
    return proc.returncode, proc.stdout


def test_cli_exits_zero_when_every_lane_reported():
    with tempfile.TemporaryDirectory() as tmp:
        _write(tmp, _doc(findings=[_finding()]))
        code, out = _run("--findings", tmp)
        assert code == 0, out
        assert "0 critical · 1 important" in out


def test_cli_exits_nonzero_when_a_lane_did_not_report():
    """The command tells its caller a non-zero exit means an unjudged lane, so a
    caller that checks only the status must not read a partial run as complete."""
    with tempfile.TemporaryDirectory() as tmp:
        _write(tmp, _doc())
        (Path(tmp) / "broken.json").write_text("{not json")
        code, out = _run("--findings", tmp)
        assert code == 1
        assert "Judges that did not report" in out


def test_cli_exits_nonzero_for_a_missing_expected_judge():
    with tempfile.TemporaryDirectory() as tmp:
        _write(tmp, _doc("security-auditor"))
        code, out = _run("--findings", tmp, "--expect", "security-auditor,test-auditor")
        assert code == 1
        assert "test-auditor" in out


def test_cli_pr_comments_format_emits_parseable_json():
    with tempfile.TemporaryDirectory() as tmp:
        _write(tmp, _doc(findings=[_finding()]))
        code, out = _run("--findings", tmp, "--format", "pr-comments")
        assert code == 0
        assert set(json.loads(out)) == {"summary", "comments"}


def test_cli_rejects_a_missing_or_empty_directory():
    code, _ = _run("--findings", "/nonexistent/gauntlet-findings")
    assert code == 1
    with tempfile.TemporaryDirectory() as tmp:
        code, _ = _run("--findings", tmp)
        assert code == 1


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
