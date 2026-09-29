#!/usr/bin/env python3
"""Unit tests for scripts/run_judges.py — replies land without anyone retyping them.

A fake `claude` stands in for the CLI: it reads the prompt on stdin, finds the
judge in it, and prints whatever reply that judge is scripted to give. That keeps
the tests off the network while driving the real subprocess path.

Self-running: `python3 tests/test_run_judges.py` prints OK.
"""
import json
import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import report  # noqa: E402 — sys.path must be set first
import run_judges  # noqa: E402

#: The fake CLI. `REPLIES` maps a judge to (exit code, stdout); the argv it was
#: called with is recorded next to the script so a test can read the grant.
FAKE = """#!{python}
import json, sys
from pathlib import Path
here = Path(__file__).parent
replies = json.loads((here / "replies.json").read_text())
prompt = sys.stdin.read()
judge = json.loads(prompt.split("\\n\\n", 1)[1])["judge"]
(here / (judge + ".argv")).write_text(json.dumps(sys.argv[1:]))
(here / (judge + ".prompt")).write_text(prompt)
(here / (judge + ".cwd")).write_text(str(Path.cwd().resolve()))
code, out = replies[judge]
sys.stdout.write(out)
sys.exit(code)
"""


def _invocation(judge):
    return {
        "contract_version": 1,
        "judge": judge,
        "mount": "acceptance",
        "artifact": {"kind": "changeset", "base": "a1b2c3d4e5f6", "head": "f6e5d4c3b2a1"},
        "standard": {"name": judge},
    }


def _result(text, is_error=False):
    return {"type": "result", "subtype": "success", "is_error": is_error, "result": text}


def _setup(tmp, replies):
    """A fake CLI in `tmp/bin` scripted with `replies`, and the invocations file."""
    bin_dir = Path(tmp) / "bin"
    bin_dir.mkdir()
    fake = bin_dir / "claude"
    fake.write_text(FAKE.format(python=sys.executable))
    fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
    (bin_dir / "replies.json").write_text(json.dumps(replies))
    invocations = Path(tmp) / "invocations.json"
    invocations.write_text(json.dumps([_invocation(j) for j in replies]))
    return fake, invocations, Path(tmp) / "findings"


def _run(*args, env=None):
    return subprocess.run(
        [sys.executable, str(REPO / "scripts/run_judges.py"), *args],
        capture_output=True, text=True, env=env,
    )


def _doc(judge):
    return json.dumps({
        "contract_version": 1,
        "judge": judge,
        "mount": "acceptance",
        "artifact": {"kind": "changeset", "base": "a1b2c3d4e5f6", "head": "f6e5d4c3b2a1"},
        "standard": {"name": judge},
        "findings": [],
        "coverage": "Checked it — em dash included.",
    })


def test_each_reply_lands_byte_for_byte_in_its_own_file():
    security, docs = _doc("security-auditor"), _doc("doc-auditor")
    with tempfile.TemporaryDirectory() as tmp:
        fake, invocations, findings = _setup(tmp, {
            # Both shapes the CLI prints: the bare result, and the verbose list.
            "security-auditor": [0, json.dumps(_result(security))],
            "doc-auditor": [0, json.dumps([{"type": "system"}, _result(docs)])],
        })
        proc = _run("--invocations", str(invocations), "--findings", str(findings),
                    "--claude", str(fake))
        assert proc.returncode == 0, proc.stderr
        assert (findings / "security-auditor.json").read_bytes() == security.encode()
        assert (findings / "doc-auditor.json").read_bytes() == docs.encode()


def test_a_fenced_reply_is_written_as_it_came_not_repaired():
    fenced = f"```json\n{_doc('security-auditor')}\n```"
    with tempfile.TemporaryDirectory() as tmp:
        fake, invocations, findings = _setup(tmp, {
            "security-auditor": [0, json.dumps(_result(fenced))],
        })
        _run("--invocations", str(invocations), "--findings", str(findings),
             "--claude", str(fake))
        assert (findings / "security-auditor.json").read_text() == fenced


def test_the_grant_is_exactly_the_agent_files_declared_tools():
    with tempfile.TemporaryDirectory() as tmp:
        fake, invocations, findings = _setup(tmp, {
            "security-auditor": [0, json.dumps(_result(_doc("security-auditor")))],
        })
        _run("--invocations", str(invocations), "--findings", str(findings),
             "--claude", str(fake), "--", "--plugin-dir", "/somewhere")
        argv = json.loads((fake.parent / "security-auditor.argv").read_text())
        declared = run_judges.declared_tools(REPO / "agents/security-auditor.md")
        assert argv[argv.index("--allowedTools") + 1] == ",".join(declared)
        assert "Write" not in declared and "Edit" not in declared
        assert argv[argv.index("--agent") + 1] == "gauntlet:security-auditor"
        assert argv[-2:] == ["--plugin-dir", "/somewhere"]


def test_the_judge_is_given_its_invocation_verbatim():
    with tempfile.TemporaryDirectory() as tmp:
        fake, invocations, findings = _setup(tmp, {
            "security-auditor": [0, json.dumps(_result(_doc("security-auditor")))],
        })
        _run("--invocations", str(invocations), "--findings", str(findings),
             "--claude", str(fake))
        sent = (fake.parent / "security-auditor.prompt").read_text()
        head, body = sent.split("\n\n", 1)
        assert head == run_judges.INSTRUCTION
        assert json.loads(body) == _invocation("security-auditor")


def test_the_session_starts_in_the_artifact_root():
    with tempfile.TemporaryDirectory() as tmp:
        fake, invocations, findings = _setup(tmp, {
            "security-auditor": [0, json.dumps(_result(_doc("security-auditor")))],
        })
        tree = Path(tmp) / "tree"
        tree.mkdir()
        invocation = _invocation("security-auditor")
        invocation["artifact"]["root"] = str(tree)
        invocations.write_text(json.dumps([invocation]))
        _run("--invocations", str(invocations), "--findings", str(findings),
             "--claude", str(fake))
        assert (fake.parent / "security-auditor.cwd").read_text() == str(tree.resolve())


def test_an_empty_reply_is_a_lane_that_did_not_report():
    with tempfile.TemporaryDirectory() as tmp:
        fake, invocations, findings = _setup(tmp, {
            "security-auditor": [0, json.dumps(_result(""))],
        })
        proc = _run("--invocations", str(invocations), "--findings", str(findings),
                    "--claude", str(fake))
        assert proc.returncode == 0, proc.stderr
        assert (findings / "security-auditor.json").read_bytes() == b""
        docs, _, failures = report.load(findings, ["security-auditor"])
        assert docs == []
        assert any("security-auditor.json: could not be read as JSON" in f for f in failures)


def test_a_truncated_reply_is_a_lane_that_did_not_report():
    cut = _doc("security-auditor")[:60]
    with tempfile.TemporaryDirectory() as tmp:
        fake, invocations, findings = _setup(tmp, {
            "security-auditor": [0, json.dumps(_result(cut))],
        })
        _run("--invocations", str(invocations), "--findings", str(findings),
             "--claude", str(fake))
        assert (findings / "security-auditor.json").read_text() == cut
        docs, _, failures = report.load(findings, ["security-auditor"])
        assert docs == []
        assert any("could not be read as JSON" in f for f in failures)


def test_a_failed_session_writes_nothing_and_report_names_the_lane():
    with tempfile.TemporaryDirectory() as tmp:
        fake, invocations, findings = _setup(tmp, {
            "security-auditor": [0, json.dumps(_result(_doc("security-auditor")))],
            "doc-auditor": [1, "not json at all"],
            "test-auditor": [0, json.dumps(_result("API Error: overloaded", True))],
        })
        proc = _run("--invocations", str(invocations), "--findings", str(findings),
                    "--claude", str(fake))
        assert proc.returncode == 1
        assert "doc-auditor: exited 1" in proc.stderr
        assert "test-auditor: exited 0 with no reply" in proc.stderr
        assert sorted(p.name for p in findings.iterdir()) == ["security-auditor.json"]
        expect = ["security-auditor", "doc-auditor", "test-auditor"]
        _, _, failures = report.load(findings, expect)
        for judge in ("doc-auditor", "test-auditor"):
            assert f"{judge}: dispatched but wrote no findings document" in failures


def test_a_missing_cli_exits_2_and_runs_nothing():
    with tempfile.TemporaryDirectory() as tmp:
        _, invocations, findings = _setup(tmp, {"security-auditor": [0, ""]})
        proc = _run("--invocations", str(invocations), "--findings", str(findings),
                    "--claude", str(Path(tmp) / "no-such-claude"))
        assert proc.returncode == run_judges.NO_CLI
        assert "not found" in proc.stderr
        assert not findings.exists()


def test_the_cli_is_found_on_path_by_default():
    with tempfile.TemporaryDirectory() as tmp:
        fake, invocations, findings = _setup(tmp, {
            "security-auditor": [0, json.dumps(_result(_doc("security-auditor")))],
        })
        env = dict(os.environ, PATH=f"{fake.parent}{os.pathsep}{os.environ['PATH']}")
        proc = _run("--invocations", str(invocations), "--findings", str(findings),
                    env=env)
        assert proc.returncode == 0, proc.stderr
        assert (findings / "security-auditor.json").exists()


def test_an_unregistered_judge_is_refused_before_anything_runs():
    with tempfile.TemporaryDirectory() as tmp:
        fake, invocations, findings = _setup(tmp, {"no-such-judge": [0, ""]})
        proc = _run("--invocations", str(invocations), "--findings", str(findings),
                    "--claude", str(fake))
        assert proc.returncode == 1
        assert "not a registered judge: no-such-judge" in proc.stderr
        assert not (fake.parent / "no-such-judge.argv").exists()


def test_reply_reads_both_output_shapes_and_refuses_the_rest():
    assert run_judges.reply(json.dumps(_result("x"))) == "x"
    assert run_judges.reply(json.dumps([{"type": "system"}, _result("y")])) == "y"
    assert run_judges.reply(json.dumps(_result("boom", is_error=True))) is None
    assert run_judges.reply(json.dumps([{"type": "system"}])) is None
    assert run_judges.reply("") is None


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
