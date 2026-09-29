#!/usr/bin/env python3
"""Workflow hygiene: actions pinned to commit SHAs (release.yml states the policy), token scoped.

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


def test_every_workflow_scopes_its_token():
    """Without a `permissions:` block GITHUB_TOKEN gets the repository default,
    which may be write-all."""
    unscoped = [
        path.name
        for path in sorted(WORKFLOWS.glob("*.yml"))
        if not re.search(r"^\s*permissions:", path.read_text(encoding="utf-8"), re.MULTILINE)
    ]
    assert not unscoped, f"workflows with no permissions block: {unscoped}"


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
