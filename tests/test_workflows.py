#!/usr/bin/env python3
"""Every GitHub Actions step is pinned to a commit SHA (release.yml states the policy).

Self-running: `python3 tests/test_workflows.py` prints OK.
"""
import re
from pathlib import Path

WORKFLOWS = Path(__file__).resolve().parent.parent / ".github" / "workflows"
USES = re.compile(r"^\s*-?\s*uses:\s*(\S+)", re.MULTILINE)
PINNED = re.compile(r"^[^@\s]+@[0-9a-f]{40}$")


def test_every_action_is_pinned_to_a_commit_sha():
    refs = [
        (path.name, ref)
        for path in sorted(WORKFLOWS.glob("*.yml"))
        for ref in USES.findall(path.read_text(encoding="utf-8"))
    ]
    assert refs, "no workflow steps found"
    floating = [f"{name}: {ref}" for name, ref in refs if not PINNED.match(ref)]
    assert not floating, f"actions on a mutable ref: {floating}"


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
