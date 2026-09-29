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
        "artifact": {"kind": "changeset", "base": "a1b2c3d4e5f6", "head": "f6e5d4c3b2a1",
                     "root": str(REPO)},
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


def test_the_session_reaches_the_artifact_root_without_starting_in_it():
    """A session started inside a PR's worktree would load that tree's CLAUDE.md
    and hooks as trusted config; the tree is granted by --add-dir instead."""
    with tempfile.TemporaryDirectory() as tmp:
        fake, invocations, findings = _setup(tmp, {
            "security-auditor": [0, json.dumps(_result(_doc("security-auditor")))],
        })
        tree = Path(tmp) / "tree"
        tree.mkdir()
        invocation = _invocation("security-auditor")
        invocation["artifact"]["root"] = str(tree)
        invocations.write_text(json.dumps([invocation]))
        subprocess.run(
            [sys.executable, str(REPO / "scripts/run_judges.py"),
             "--invocations", str(invocations), "--findings", str(findings),
             "--claude", str(fake)],
            capture_output=True, text=True, cwd=tmp,
        )
        cwd = Path((fake.parent / "security-auditor.cwd").read_text())
        assert cwd not in (Path(tmp).resolve(), tree.resolve()), cwd
        argv = json.loads((fake.parent / "security-auditor.argv").read_text())
        assert argv[argv.index("--add-dir") + 1] == str(tree)
        # --add-dir still loads the tree's .claude/skills/; only this flag keeps a
        # PR's skill out of the judge's context.
        assert "--disable-slash-commands" in argv


def test_an_invocation_without_an_absolute_root_is_refused_before_any_session():
    """A judge runs from an empty scratch directory, so a missing or relative root
    would point it at nothing; starting it in the checkout instead would load the
    judged tree's CLAUDE.md and hooks. The runner refuses the batch."""
    with tempfile.TemporaryDirectory() as tmp:
        fake, invocations, findings = _setup(tmp, {
            "security-auditor": [0, json.dumps(_result(_doc("security-auditor")))],
        })
        for root in (None, "relative/tree"):
            invocation = _invocation("security-auditor")
            invocation["artifact"].pop("root", None)
            if root:
                invocation["artifact"]["root"] = root
            invocations.write_text(json.dumps([invocation]))
            proc = subprocess.run(
                [sys.executable, str(REPO / "scripts/run_judges.py"),
                 "--invocations", str(invocations), "--findings", str(findings),
                 "--claude", str(fake)],
                capture_output=True, text=True, cwd=tmp,
            )
            assert proc.returncode == 1, (root, proc.returncode, proc.stderr)
            assert "absolute artifact.root" in proc.stderr, proc.stderr
            assert not (fake.parent / "security-auditor.argv").exists(), "a session started"


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


def test_a_missing_cli_exits_3_and_runs_nothing():
    """Not 2: argparse exits 2 on a usage error, which must not read as no CLI."""
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


def test_a_reused_directory_never_passes_off_an_earlier_reply():
    with tempfile.TemporaryDirectory() as tmp:
        fake, invocations, findings = _setup(tmp, {"security-auditor": [1, ""]})
        findings.mkdir()
        (findings / "security-auditor.json").write_text(_doc("security-auditor"))
        proc = _run("--invocations", str(invocations), "--findings", str(findings),
                    "--claude", str(fake))
        assert proc.returncode == 1
        assert not (findings / "security-auditor.json").exists()
        _, _, failures = report.load(findings, ["security-auditor"])
        assert "security-auditor: dispatched but wrote no findings document" in failures


def test_a_reply_that_cannot_be_written_is_that_lanes_problem_not_the_runs():
    with tempfile.TemporaryDirectory() as tmp:
        fake, _, _ = _setup(tmp, {
            "security-auditor": [0, json.dumps(_result(_doc("security-auditor")))],
        })
        not_a_dir = Path(tmp) / "findings"
        not_a_dir.write_text("")  # writing <findings>/<judge>.json under a file fails
        judge, problem = run_judges.run_one(
            _invocation("security-auditor"), ["Read"], not_a_dir, str(fake), [], 30, tmp
        )
        assert judge == "security-auditor"
        assert problem.startswith("replied, but the reply could not be written")


def test_an_unreadable_invocations_file_is_an_error_line_not_a_traceback():
    with tempfile.TemporaryDirectory() as tmp:
        fake, invocations, findings = _setup(tmp, {"security-auditor": [0, ""]})
        for content in ("{not json", json.dumps({"judge": "x"}), json.dumps([{}])):
            invocations.write_text(content)
            proc = _run("--invocations", str(invocations), "--findings", str(findings),
                        "--claude", str(fake))
            assert proc.returncode == 1
            assert "gauntlet: no judge was run" in proc.stderr
            assert "Traceback" not in proc.stderr
        proc = _run("--invocations", str(Path(tmp) / "absent.json"),
                    "--findings", str(findings), "--claude", str(fake))
        assert proc.returncode == 1 and "Traceback" not in proc.stderr


def test_a_hung_judge_is_abandoned_at_the_timeout():
    with tempfile.TemporaryDirectory() as tmp:
        fake, invocations, findings = _setup(tmp, {"security-auditor": [0, ""]})
        fake.write_text(f"#!{sys.executable}\nimport time\ntime.sleep(30)\n")
        proc = _run("--invocations", str(invocations), "--findings", str(findings),
                    "--claude", str(fake), "--timeout", "0.5")
        assert proc.returncode == 1
        assert "security-auditor: timed out after 0.5s" in proc.stderr
        assert not (findings / "security-auditor.json").exists()


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


def test_review_starts_the_runner_in_the_background_not_under_the_bash_timeout():
    # Claude Code's Bash tool kills a foreground command at 120s by default and 600s
    # at most; a real 11-lane run has taken 167s, and each lane may take 1800s.
    text = (REPO / "commands" / "review.md").read_text(encoding="utf-8")
    dispatch = text.split("## 3. Dispatch", 1)[1].split("## 4.", 1)[0]
    primary = dispatch.split("**Exit 3", 1)[0]
    assert "run_in_background" in primary, (
        "§3 must start the runner in the background: a foreground Bash call is killed "
        "at the tool's timeout, mid-run, with lanes unwritten and no exit code"
    )
    assert "wait for it to exit before §4" in primary


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
