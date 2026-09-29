#!/usr/bin/env python3
"""Rules inside judge prompts that a model reads literally.

Self-running: `python3 tests/test_judge_prompts.py` prints OK.
"""
from pathlib import Path

AGENTS = Path(__file__).resolve().parent.parent / "agents"


def test_an_observed_anchor_says_how_a_read_only_judge_observes():
    """Judges never run the target, so a critical anchor asking for "the observed one"
    must say what observed means, or the model invents an observation or never files
    a valid critical."""
    unexplained = [
        path.name
        for path in sorted(AGENTS.glob("*.md"))
        if "the observed one" in (text := path.read_text(encoding="utf-8"))
        and "Since you" not in text
    ]
    assert not unexplained, f"observed anchor with no read-only reading: {unexplained}"


def test_codebase_posture_names_package_manager_audits():
    """Sonnet 5.5 read "osv-scanner, pip-audit, or the repo's equivalent" as two tools,
    found neither, and reported could-not-verify on a pnpm repo."""
    text = (AGENTS / "codebase-posture-auditor.md").read_text(encoding="utf-8")
    for tool in ("npm audit", "pnpm audit", "cargo audit"):
        assert f"`{tool}`" in text, tool


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
