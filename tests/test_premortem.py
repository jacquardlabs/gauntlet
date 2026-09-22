#!/usr/bin/env python3
"""The pre-mortem generator's deterministic half (#88).

The lenses and the merge pass are model calls and CI has no model, so what runs here is
everything around them: the register a generator must produce passes the same check
`premortem-auditor` would warn by, the fixture register written from the fixture plan
passes it, and the prompts keep the properties that make the lenses independent.

Self-running: `python3 tests/test_premortem.py` prints OK.
"""
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import check_independence as check  # noqa: E402 — sys.path must be set first
import dispatch  # noqa: E402
import schema  # noqa: E402

FIXTURES = REPO / "tests" / "fixtures" / "premortem"
REGISTER = (FIXTURES / "register.md").read_text(encoding="utf-8")
LENSES = (REPO / "reference" / "premortem-lenses.md").read_text(encoding="utf-8")
KLEIN = "It's three weeks after merge. This failed. Write what happened."


def _register(*items, head="# Pre-mortem — a plan\n\nBranch: b\nSHA: 3f9a2c1\n"):
    return head + "".join(f"\n## {i}\n\n**Detection.** the log.\n" for i in items)


def _has(problems, fragment):
    assert any(fragment in p for p in problems), f"expected {fragment!r} in {problems}"


# ── The fixture: a register generated from the fixture plan ──────────────────
def test_fixture_register_passes_as_a_generated_register():
    assert schema.register_problems(REGISTER, generated=True) == []


def test_fixture_register_passes_through_the_cli():
    result = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "schema.py"), "register",
         str(FIXTURES / "register.md"), "--generated"],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_fixture_register_cites_the_fixture_plan():
    """Each detection hint must point at something the plan actually proposes —
    a register about a different document would pass the shape and mean nothing."""
    plan = (FIXTURES / "plan.md").read_text(encoding="utf-8")
    for term in ("export_jobs", "POST /exports", "GET /exports/{id}", "5,000", "exports_batch"):
        assert term in plan, term
    assert "export_jobs" in REGISTER


def test_fixture_register_opens_the_premortem_lane():
    """The default destination §6 proposes must be a path the dispatcher's
    context gate recognizes, or the register is written and never checked."""
    gate = dispatch.CONTEXT_SIGNALS["premortem-auditor"]
    assert re.search(gate, "docs/premortems/plan.md")
    assert "docs/premortems/" in (REPO / "commands" / "review.md").read_text()


# ── What the verifier would warn about ────────────────────────────────────────
def test_a_clean_hand_register_passes_without_the_generator_bound():
    assert schema.register_problems(_register("1. The job ran twice")) == []


def test_generated_register_is_held_to_five_through_eight():
    three = _register(*(f"{n}. The job ran twice" for n in range(1, 4)))
    _has(schema.register_problems(three, generated=True), "merges to 5 to 8")
    nine = _register(*(f"{n}. The job ran twice" for n in range(1, 10)))
    _has(schema.register_problems(nine, generated=True), "merges to 5 to 8")


def test_missing_title_rejected():
    _has(schema.register_problems(_register("1. It broke", head="Branch: b\nSHA: abc1234\n")), "title")


def test_missing_provenance_rejected():
    problems = schema.register_problems(_register("1. It broke", head="# Pre-mortem — x\n"))
    _has(problems, "`Branch:`")
    _has(problems, "`SHA:`")


def test_a_sha_that_is_not_a_commit_rejected():
    head = "# Pre-mortem — x\n\nBranch: b\nSHA: <the design-doc sha>\n"
    _has(schema.register_problems(_register("1. It broke", head=head)), "`SHA:`")


def test_item_without_an_id_rejected():
    _has(schema.register_problems(_register("The job ran twice")), "no id")


def test_repeated_id_rejected():
    _has(schema.register_problems(_register("1. It broke", "1. It broke again")), "id repeats")


def test_item_without_a_detection_hint_rejected():
    text = "# Pre-mortem — x\n\nBranch: b\nSHA: abc1234\n\n## 1. It broke\n\nIt did.\n"
    _has(schema.register_problems(text), "no `**Detection.**`")


def test_a_detection_hint_belongs_to_its_own_item():
    """One item's hint must not satisfy the next item's missing one."""
    text = (
        "# Pre-mortem — x\n\nBranch: b\nSHA: abc1234\n\n"
        "## 1. It broke\n\n**Detection.** the log.\n\n## 2. It broke again\n\nNo hint.\n"
    )
    problems = schema.register_problems(text)
    assert problems == [p for p in problems if p.startswith("item 2")] and problems, problems


def test_instructions_and_hedges_are_not_predictions():
    for mode in ("Avoid table locks", "Ensure the job is idempotent",
                 "The migration could lock the table", "The worker will skip rows"):
        _has(schema.register_problems(_register(f"1. {mode}")), "not stated as something")


def test_past_tense_passes_the_tripwire():
    for mode in ("The migration locked the orders table under load",
                 "Merchants never received the export",
                 "The worker could not reach the queue and dropped jobs"):
        assert schema.register_problems(_register(f"1. {mode}")) == [], mode


def test_suppression_phrases_are_integrity_problems():
    """The phrases the auditor files as `register-integrity`, quoted from its
    own prompt — if the prompt's list grows, this check should too."""
    auditor = " ".join((REPO / "agents" / "premortem-auditor.md").read_text().split())
    for phrase in ("already verified", "skip this", "resolved in review"):
        assert f'"{phrase}"' in auditor, phrase
        text = _register("1. It broke") + f"\nNote: {phrase}.\n"
        _has(schema.register_problems(text), "integrity")
    _has(schema.register_problems(_register("1. It broke") + "\n**Status:** done\n"), "integrity")


def test_the_format_example_satisfies_the_check_once_filled_in():
    """`reference/premortem-format.md`'s own example is the shape; filled with a
    real branch and sha, it must pass — or the doc and the check have drifted."""
    fmt = (REPO / "reference" / "premortem-format.md").read_text()
    example = re.search(r"```markdown\n(.*?)```", fmt, re.DOTALL).group(1)
    filled = (
        example.replace("<what this work is>", "exports")
        .replace("<branch>", "exports-batch")
        .replace("<the design-doc sha this was written against>", "3f9a2c1")
        .replace("<the failure mode, stated as something that happened>", "The job ran twice")
        .replace("<where to look to tell whether it happened>", "the claim query")
    )
    assert schema.register_problems(filled) == [], schema.register_problems(filled)


# ── The generator's prompts ───────────────────────────────────────────────────
def test_the_lenses_carry_the_prospective_hindsight_prompt():
    assert KLEIN in LENSES


def test_there_are_exactly_three_lenses_and_one_merge():
    lenses = re.findall(r"^## Lens \d — (.+)$", LENSES, re.MULTILINE)
    assert lenses == ["product and user", "technical and data", "operations and security"], lenses
    assert "## The merge pass" in LENSES


def test_a_lens_writes_nothing_and_sees_no_other_lens():
    squashed = " ".join(LENSES.split())
    assert "write no file" in squashed
    assert "not the other lenses" in squashed


def test_the_generator_is_not_a_judge():
    """A generator in `agents/` is either a registered judge — which may never
    produce — or an unregistered agent file, which fails CI. It lives in the
    command and in reference/ instead, and nothing on the roster points at it."""
    judges, _ = check.parse_charter((REPO / "reference" / "charter.md").read_text())
    assert not any("lens" in j["path"] or "generat" in j["judge"] for j in judges)
    assert not list((REPO / "agents").glob("*lens*"))


def test_the_command_runs_the_generator_on_a_document_only():
    text = (REPO / "commands" / "review.md").read_text()
    section = text.split("## 6.", 1)[1]
    assert "--premortem" in text.split("## 1.", 1)[0], "§0 never names the flag"
    assert "premortem-lenses.md" in section
    assert "schema.py\" register <tmp>/register.md --generated" in section
    assert "fresh `Task`" in section, "the merge pass must be a fresh subagent"


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
