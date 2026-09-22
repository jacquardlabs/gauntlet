#!/usr/bin/env python3
"""`bin/gauntlet` is how a co-installed consumer finds gauntlet (#87).

Claude Code puts an enabled plugin's `bin/` on the Bash tool's PATH, so the file must
be executable, `root` must print the install root, and `dispatch`/`report` must hand
their arguments and exit codes through untouched. Every call here runs the file
itself, never `python3 bin/gauntlet`, so the shebang and the exec bit are under test
too. Self-running: `python3 tests/test_bin_gauntlet.py` prints OK.
"""
import json
import os
import shutil
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BIN = REPO / "bin" / "gauntlet"
CONTRACT = REPO / "docs" / "findings-contract.md"
# The interpreter bin/gauntlet's shebang resolves, so argparse output compares like for like.
PYTHON3 = shutil.which("python3")


def _run(*args, **kwargs):
    return subprocess.run([str(BIN), *args], capture_output=True, text=True, **kwargs)


def _script(name, *args):
    return subprocess.run(
        [PYTHON3, str(REPO / "scripts" / name), *args], capture_output=True, text=True
    )


def test_the_entrypoint_is_executable():
    assert os.access(BIN, os.X_OK), "bin/gauntlet lands on PATH but cannot run"


def test_command_v_finds_it_on_path():
    env = {**os.environ, "PATH": f"{BIN.parent}{os.pathsep}{os.environ['PATH']}"}
    found = subprocess.run(
        ["sh", "-c", "command -v gauntlet"], capture_output=True, text=True, env=env
    )
    assert found.stdout.strip() == str(BIN), found


def test_root_prints_the_install_root():
    result = _run("root")
    assert result.returncode == 0, result
    assert result.stdout == f"{REPO}\n", result.stdout


def test_root_resolves_from_any_directory():
    result = _run("root", cwd="/")
    assert result.stdout == f"{REPO}\n", result.stdout


def test_dispatch_passes_arguments_through():
    for args in (["--help"], ["--mount", "nonsense"]):
        ours, theirs = _run("dispatch", *args), _script("dispatch.py", *args)
        assert (ours.returncode, ours.stdout, ours.stderr) == (
            theirs.returncode,
            theirs.stdout,
            theirs.stderr,
        ), args


def test_report_passes_arguments_through():
    for args in (["--help"], ["--no-such-flag"]):
        ours, theirs = _run("report", *args), _script("report.py", *args)
        assert (ours.returncode, ours.stdout, ours.stderr) == (
            theirs.returncode,
            theirs.stdout,
            theirs.stderr,
        ), args


def test_passthrough_keeps_the_targets_failure_code():
    result = _run("report", "--no-such-flag")
    assert result.returncode == 2, result


def test_unknown_verb_exits_2():
    result = _run("where")
    assert result.returncode == 2, result
    assert "unknown verb 'where'" in result.stderr
    assert "usage: gauntlet" in result.stderr


def test_no_verb_exits_2_with_usage():
    result = _run()
    assert result.returncode == 2, result
    assert "usage: gauntlet" in result.stderr


def test_help_names_every_verb():
    for flag in ("-h", "--help", "help"):
        result = _run(flag)
        assert result.returncode == 0, result
        for verb in ("root", "dispatch", "report"):
            assert verb in result.stdout, (flag, verb)


def test_version_is_the_manifests():
    manifest = json.loads((REPO / ".claude-plugin" / "plugin.json").read_text())
    result = _run("--version")
    assert result.returncode == 0, result
    assert result.stdout == f"{manifest['version']}\n", result.stdout


def test_the_contract_names_the_entrypoint():
    text = CONTRACT.read_text(encoding="utf-8")
    for call in ("command -v gauntlet", "gauntlet root", "gauntlet dispatch", "gauntlet report"):
        assert call in text, call
    assert "gauntlet:where" not in text


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
