#!/usr/bin/env python3
"""Changeset simplicity and diff-vs-intent belong to exorcist, not these lanes (#89).

Each ceded check is gone from its lane's rubric and output enum, and each lane names
the boundary so it escalates rather than hunts; the README tells a consumer without
exorcist what goes unchecked (#92). product-reviewer keeps `spec-fidelity`, and its
intake `simplicity` stays. Self-running:
`python3 tests/test_ceded_checks.py` prints OK.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENTS = ROOT / "agents"


def _text(judge):
    return (AGENTS / f"{judge}.md").read_text(encoding="utf-8")


def _checks(text):
    """The check ids a rubric lists: `N. **Name** (`id`)`."""
    return re.findall(r"^\d+\. \*\*[^*]+\*\* \(`([a-z-]+)`\)", text, re.MULTILINE)


def _enum(text):
    match = re.search(r'"dimension": "([a-z| -]+)"', text)
    assert match, "no dimension enum in the output example"
    return [d.strip() for d in match.group(1).split("|")]


def _section(text, heading):
    start = text.index(heading)
    end = text.find("\n## ", start + 1)
    return text[start:end]


def test_architecture_cedes_simplicity():
    text = _text("architecture-auditor")
    expected = ["pattern-fit", "coupling", "complexity", "data-migrations"]
    assert _checks(text) == expected, _checks(text)
    assert _enum(text) == expected, _enum(text)
    assert "the four dimensions below" in text
    assert "simplicity" not in text.split("---")[1], "frontmatter still claims it"


def test_code_keeps_complexity_and_drops_the_overlap():
    text = _text("code-auditor")
    assert "complexity" in _checks(text)
    maintainability = next(
        line for line in text.splitlines() if "(`maintainability`)" in line
    )
    body = _section(text, "## What you check")
    for gone in ("duplicate logic", "unused exports", "dead code", "`simplicity`"):
        assert gone not in body, gone
    assert "god files" in maintainability



def test_code_separates_what_stays_from_what_exorcist_owns():
    text = _text("code-auditor")
    boundary = " ".join(text.split("## Posture")[0].split())
    assert "An unused local variable (`hygiene`) and a branch whose own condition" in boundary
    assert "a symbol with no caller and a path the change left dead" in boundary
    assert "unused local variables" in " ".join(_section(text, "## What you check").split())

def test_product_acceptance_keeps_spec_fidelity():
    # exorcist's trace passed an unrequested PRODUCT.md edit with the issue as intent
    # (docs/verification/cede-simplicity-before-after-2026-09-27.md), so it stays here.
    acceptance = _section(_text("product-reviewer"), "## What you check at `acceptance`")
    assert "spec-fidelity" in _checks(acceptance), _checks(acceptance)


def test_product_intake_keeps_simplicity():
    intake = _section(_text("product-reviewer"), "## What you check at `intake`")
    assert "simplicity" in _checks(intake)


def test_each_ceding_lane_names_the_owner():
    for judge in ("architecture-auditor", "code-auditor"):
        assert "exorcist" in _text(judge), judge


def test_readme_names_what_exorcist_owns_on_a_changeset():
    readme = " ".join((ROOT / "README.md").read_text(encoding="utf-8").split())
    assert "gauntlet no longer checks for duplicated logic" in readme
    assert "`/exorcist:exorcise`" in readme

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
