#!/usr/bin/env python3
"""`commands/where.md` is the consumer-transport contract's one command (#80).

A co-installed consumer learns gauntlet's root by loading it: its body must be the
substituted-on-load `${CLAUDE_PLUGIN_ROOT}` and the two script entrypoints the contract
names, nothing else. Self-running: `python3 tests/test_where.py` prints OK.
"""
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
WHERE = REPO / "commands" / "where.md"
CONTRACT = REPO / "docs" / "findings-contract.md"


def _body():
    text = WHERE.read_text(encoding="utf-8")
    match = re.match(r"---\n(.*?)\n---\n(.*)", text, re.DOTALL)
    assert match, "where.md needs frontmatter"
    return match.group(1), match.group(2).strip().splitlines()


def test_frontmatter_describes_the_command():
    front, _ = _body()
    assert "description:" in front


def test_body_is_the_root_and_the_two_entrypoints():
    _, lines = _body()
    assert lines == [
        "${CLAUDE_PLUGIN_ROOT}",
        "${CLAUDE_PLUGIN_ROOT}/scripts/dispatch.py",
        "${CLAUDE_PLUGIN_ROOT}/scripts/report.py",
    ], lines


def test_the_entrypoints_exist():
    _, lines = _body()
    for line in lines[1:]:
        assert (REPO / line.replace("${CLAUDE_PLUGIN_ROOT}/", "")).is_file(), line


def test_the_contract_names_the_command():
    assert "/gauntlet:where" in CONTRACT.read_text(encoding="utf-8")


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
