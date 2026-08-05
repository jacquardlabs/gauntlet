#!/usr/bin/env python3
"""Unit tests for scripts/check_independence.py.

Two halves: fixtures that prove each rule has teeth — including against the
actual contamination the studious fleet carries today, a `Write` tool in the
periodic reviewers and ~30 door references — and a pass over the real roster,
so a migrated judge is held to the same rules in the same suite that defines
them.

Self-running: `python3 tests/test_independence.py` prints OK.
"""
import json
import re
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import check_independence as check  # noqa: E402 — sys.path must be set first
import schema  # noqa: E402

CLEAN_JUDGE = """---
name: security-auditor
description: Judges a changeset against the security checklist.
tools: Read, Grep, Glob, Bash
model: opus
---

Inspect read-only. Report findings in the contract shape; the consumer persists
them. Cite receipts from the evidence log when a claim depends on a command
having run.
"""


def _charter(rows="", anchors=""):
    return (
        "# Charter\n\n## Judges\n\n"
        "| Judge | Lane | Mounts | Standard | Backed by |\n|---|---|---|---|---|\n"
        f"{rows}\n"
        "## Anchors — what a critical must cite\n\n"
        "| Judge | A critical must cite |\n|---|---|\n"
        f"{anchors}\n"
    )


ROW = (
    "| `security-auditor` | security | `acceptance` | `security-checklist` "
    "| `agents/security-auditor.md` |\n"
)
ANCHOR = "| `security-auditor` | a named signature plus the traced path at file:line |\n"


def _has(problems, fragment):
    assert any(fragment in p for p in problems), (
        f"expected a problem containing {fragment!r}, got: {problems}"
    )


# ── charter parsing ───────────────────────────────────────────────────────────
def test_empty_roster_parses_clean():
    judges, anchors = check.parse_charter(_charter())
    assert judges == [] and anchors == {}
    assert check.charter_problems(_charter()) == []


def test_real_charter_is_internally_consistent():
    text = (REPO / "reference/charter.md").read_text()
    assert check.charter_problems(text) == []


def test_every_registered_judge_exists_and_is_clean():
    """The real roster, held to the same rules as the fixtures.

    `main()` covers this in CI, but only as a pass/fail line. Asserting it here
    means a judge that acquires a Write tool or a door reference fails in the
    same suite that defines what those rules mean.
    """
    judges, _ = check.parse_charter((REPO / "reference/charter.md").read_text())
    for j in judges:
        path = REPO / j["path"]
        assert path.is_file(), f"{j['judge']} registered as {j['path']}, which is missing"
        assert check.scan(j["path"], path.read_text()) == []


def test_roster_row_parses_every_column():
    judges, anchors = check.parse_charter(_charter(ROW, ANCHOR))
    assert len(judges) == 1
    j = judges[0]
    assert j["judge"] == "security-auditor"
    assert j["lane"] == "security"
    assert j["path"] == "agents/security-auditor.md"
    assert check._cell_tokens(j["mounts"]) == ["acceptance"]
    assert check._cell_tokens(j["standard"]) == ["security-checklist"]
    assert set(anchors) == {"security-auditor"}


def test_roster_row_never_parses_as_an_anchor_row():
    _, anchors = check.parse_charter(_charter(ROW))
    assert anchors == {}, "a five-column roster row must not match ANCHOR_ROW"


def test_both_mounts_declared():
    row = (
        "| `product-reviewer` | product | `intake`, `acceptance` | `product-rubric` "
        "| `agents/product-reviewer.md` |\n"
    )
    judges, _ = check.parse_charter(_charter(row))
    assert check._cell_tokens(judges[0]["mounts"]) == list(schema.MOUNTS)


# ── charter integrity ─────────────────────────────────────────────────────────
def test_unknown_mount_rejected():
    row = ROW.replace("`acceptance`", "`postmortem`")
    _has(check.charter_problems(_charter(row, ANCHOR)), "not in the contract's enum")


def test_missing_mount_rejected():
    row = ROW.replace("`acceptance`", "sometimes")
    _has(check.charter_problems(_charter(row, ANCHOR)), "declares no mount")


def test_missing_standard_rejected():
    row = ROW.replace("`security-checklist`", "the usual")
    _has(check.charter_problems(_charter(row, ANCHOR)), "names no standard")


def test_standard_without_a_rubric_file_rejected():
    row = ROW.replace("`security-checklist`", "`vibes`")
    _has(
        check.charter_problems(_charter(row, ANCHOR)),
        "reference/vibes.md does not exist",
    )


def test_missing_anchor_row_rejected():
    _has(check.charter_problems(_charter(ROW)), "has no anchor row")


def test_orphan_anchor_row_rejected():
    _has(check.charter_problems(_charter("", ANCHOR)), "not on the roster")


def test_duplicate_registration_rejected():
    _has(
        check.charter_problems(_charter(ROW + ROW, ANCHOR)),
        "is registered 2 times",
    )


# ── the three prohibitions ────────────────────────────────────────────────────
def test_clean_judge_passes():
    assert check.scan("agents/security-auditor.md", CLEAN_JUDGE) == []


def test_write_tool_rejected():
    # Exactly what the eight periodic review-* agents carry today.
    text = CLEAN_JUDGE.replace(
        "tools: Read, Grep, Glob, Bash", "tools: Read, Glob, Grep, Bash, Write"
    )
    _has(check.scan("agents/review-codebase-health.md", text), "declares the Write tool")


def test_every_mutation_tool_rejected():
    for tool in check.MUTATION_TOOLS:
        text = CLEAN_JUDGE.replace("tools: Read", f"tools: {tool}, Read")
        _has(check.scan("agents/x.md", text), f"declares the {tool} tool")


def test_slash_command_rejected_in_backticks():
    # The dominant form in the studious fleet: gate-invoked (`/review`).
    text = CLEAN_JUDGE + "\nDiff-scoped and gate-invoked (`/review`).\n"
    _has(check.scan("agents/x.md", text), "names the slash command /review")


def test_slash_command_rejected_in_parens_and_frontmatter():
    text = CLEAN_JUDGE.replace(
        "Judges a changeset", "Gate-invoked (/review); judges a changeset"
    )
    _has(check.scan("agents/x.md", text), "/review")
    _has(check.scan("agents/x.md", CLEAN_JUDGE + "\nRun /retro quarterly.\n"), "/retro")


def test_paths_and_urls_are_not_slash_commands():
    text = CLEAN_JUDGE + (
        "\nRead docs/findings-contract.md and agents/x.md; see "
        "https://api.github.com/repos/o/r for the API. Write to /tmp/scratch "
        "if needed. Applies to input and/or output. N/A otherwise.\n"
    )
    assert check.scan("agents/x.md", text) == []


def test_quoted_command_with_arguments_still_caught():
    # `/review --delivery` and `/retro <area>` are both live studious forms; an
    # earlier tightening of the pattern let exactly these slip through.
    for form in ("`/review --delivery`", "`/retro <area>`", "`/review`", "`/next`'s"):
        text = CLEAN_JUDGE + f"\nThe {form} door dispatches this agent.\n"
        _has(check.scan("agents/x.md", text), "names the slash command /")


def test_closing_backtick_before_a_slash_is_prose_not_a_command():
    # Regression: found by dry-running the real studious fleet. A backtick may
    # precede a slash in two unrelated ways — `/review` (a door) and
    # `git`/`grep`/file reads (prose) — and only the first is a finding.
    text = CLEAN_JUDGE + "\nUse `git`/`grep`/file reads; never execute the target.\n"
    assert check.scan("agents/x.md", text) == []
    braced = CLEAN_JUDGE + "\nRead `${PLUGIN_ROOT}/reference/prompt-contract.md`.\n"
    assert check.scan("agents/x.md", braced) == []


def test_producer_artifact_rejected():
    for artifact in ("PLAN.md", ".studious/build-evidence", "docs/jig/evidence"):
        text = CLEAN_JUDGE + f"\nRead {artifact} for the checkpoint blocks.\n"
        _has(check.scan("agents/x.md", text), f"requires {artifact}")


def test_problems_carry_line_numbers():
    text = CLEAN_JUDGE + "\nRead PLAN.md.\n"
    problem = check.scan("agents/x.md", text)[0]
    assert problem.startswith("agents/x.md:"), problem


def test_every_judge_output_template_matches_the_contract():
    """A judge's JSON template is its half of the contract; drift here is drift
    the validators only catch at runtime, on a real dispatch, in a consumer.

    The template's placeholders are all strings, so it parses as JSON and its
    key set can be compared directly against what §4 requires.
    """
    required_top = {
        "contract_version",
        "judge",
        "mount",
        "artifact",
        "standard",
        "findings",
        "coverage",
    }
    finding_fields = {
        "dimension",
        "tier",
        "summary",
        "locus",
        "anchor",
        "basis",
        "level",
        "failure_scenario",
        "recommendation",
        "receipts",
    }
    judges, _ = check.parse_charter((REPO / "reference/charter.md").read_text())
    for j in judges:
        text = (REPO / j["path"]).read_text()
        blocks = re.findall(r"```json\n(.*?)```", text, re.DOTALL)
        assert blocks, f"{j['judge']} documents no JSON output template"
        doc = json.loads(blocks[-1])
        assert set(doc) == required_top, f"{j['judge']} template keys: {set(doc)}"
        assert doc["contract_version"] == schema.CONTRACT_VERSION
        assert doc["judge"] == j["judge"]
        assert set(doc["findings"][0]) <= finding_fields, (
            f"{j['judge']} template has a finding field the contract does not define"
        )
        for enum, field in ((schema.TIERS, "tier"), (schema.BASES, "basis")):
            offered = {v.strip() for v in doc["findings"][0][field].split("|")}
            assert offered == set(enum), (
                f"{j['judge']} offers {field} values {offered}, contract has {set(enum)}"
            )


def test_unregistered_agent_file_rejected():
    judges, _ = check.parse_charter(_charter(ROW, ANCHOR))
    with tempfile.TemporaryDirectory() as tmp:
        agents = Path(tmp)
        (agents / "security-auditor.md").write_text(CLEAN_JUDGE)
        assert check.unregistered_agents(judges, agents) == []
        (agents / "rogue-auditor.md").write_text(CLEAN_JUDGE)
        _has(check.unregistered_agents(judges, agents), "registered on no charter row")


def test_no_agents_directory_is_not_a_violation():
    with tempfile.TemporaryDirectory() as tmp:
        assert check.unregistered_agents([], Path(tmp) / "absent") == []


def test_real_agents_directory_is_fully_registered():
    judges, _ = check.parse_charter((REPO / "reference/charter.md").read_text())
    assert check.unregistered_agents(judges) == []


def test_surface_is_derived_from_the_roster():
    judges, _ = check.parse_charter(_charter(ROW, ANCHOR))
    paths = check.surface_paths(judges)
    assert [p.name for p in paths] == ["security-auditor.md"]


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
