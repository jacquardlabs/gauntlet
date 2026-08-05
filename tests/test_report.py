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


def test_documents_must_agree_about_the_artifact():
    other = _doc("test-auditor")
    other["artifact"] = {"kind": "changeset", "base": "999999999999", "head": "888888888888"}
    with tempfile.TemporaryDirectory() as tmp:
        _write(tmp, _doc("security-auditor"), other)
        docs, _, failures = report.load(Path(tmp))
        assert [d["judge"] for d in docs] == ["security-auditor"]
        _has(failures, "judged a different artifact")


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
    findings = report.flatten([_doc(findings=[_finding("critical"), _finding("track")])])
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


def test_markdown_names_demotions():
    out = report.render_markdown([_doc()], ["security-auditor: anchor-or-demote: x"], [])
    assert "## Recorded differently than claimed" in out
    assert "anchor-or-demote" in out


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


# ── pr comments ───────────────────────────────────────────────────────────────
def test_pr_comments_anchor_to_path_and_line():
    payload = json.loads(report.render_pr_comments(
        [_doc(findings=[_finding("critical")])], [], []))
    assert len(payload["comments"]) == 1
    comment = payload["comments"][0]
    assert comment["path"] == "src/a.py" and comment["line"] == 10
    assert "CRITICAL" in comment["body"] and "security-auditor" in comment["body"]


def test_unanchored_findings_ride_in_the_summary_rather_than_vanishing():
    doc = _doc(findings=[{
        "dimension": "fit", "tier": "important", "summary": "brief omits rollback",
        "locus": {"section": "Rollback"}, "basis": "inferred",
    }])
    payload = json.loads(report.render_pr_comments([doc], [], []))
    assert payload["comments"] == []
    assert "Not anchored to a line" in payload["summary"]
    assert "brief omits rollback" in payload["summary"]


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
