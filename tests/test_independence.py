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


#: The same judge, declared as a YAML block sequence. Ordinary YAML, and the form
#: the tools check was blind to until #57.
BLOCK_JUDGE = """---
name: security-auditor
description: Judges a changeset against the security checklist.
tools:
  - Read
  - Grep
  - Glob
  - Bash
model: opus
---

Inspect read-only. Report findings in the contract shape; the consumer persists
them.
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


#: The dispatcher flag that builds each artifact kind. A kind is reachable only
#: through the flag that produces it, so this is what "the command can run this
#: kind" reduces to. A changeset takes shas rather than a kind flag.
KIND_FLAGS = {
    "changeset": "--base",
    "document": "--document",
    "repository": "--ref",
}

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
    # The tokens the cell declares — not `schema.MOUNTS`, which this once
    # compared against only because the enum happened to hold exactly these two.
    assert check._cell_tokens(judges[0]["mounts"]) == ["intake", "acceptance"]


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


# ── the two kinds of standard (#14) ───────────────────────────────────────────
def test_inline_standard_needs_no_file():
    row = ROW.replace("`security-checklist`", "(inline)")
    assert check.charter_problems(_charter(row, ANCHOR)) == []


def test_inline_plus_a_file_rejected():
    row = ROW.replace("`security-checklist`", "(inline), `security-checklist`")
    _has(check.charter_problems(_charter(row, ANCHOR)), "not two")


def test_directory_standard_accepted_when_populated():
    row = ROW.replace("`security-checklist`", "`idioms/`")
    with tempfile.TemporaryDirectory() as tmp:
        idioms = Path(tmp) / "reference" / "idioms"
        idioms.mkdir(parents=True)
        (idioms / "python.md").write_text("# idioms")
        real, check.REPO = check.REPO, Path(tmp)
        try:
            assert check.charter_problems(_charter(row, ANCHOR)) == []
        finally:
            check.REPO = real


def test_two_rubric_files_rejected():
    row = ROW.replace("`security-checklist`", "`security-checklist`, `idioms/`")
    _has(check.charter_problems(_charter(row, ANCHOR)), "not two")


def test_standard_cannot_escape_reference():
    for escape in ("../../etc/passwd", "/etc/passwd"):
        row = ROW.replace("`security-checklist`", f"`{escape}`")
        _has(check.charter_problems(_charter(row, ANCHOR)), "escapes reference/")


def test_inline_is_not_matched_inside_a_parenthetical():
    # The token parse must not fire on prose that merely mentions the word.
    row = ROW.replace(
        "`security-checklist`", "`security-checklist` (inlined rules apply)"
    )
    assert check.charter_problems(_charter(row, ANCHOR)) == []


def test_directory_standard_rejected_when_missing_or_empty():
    row = ROW.replace("`security-checklist`", "`idioms/`")
    with tempfile.TemporaryDirectory() as tmp:
        real, check.REPO = check.REPO, Path(tmp)
        try:
            _has(check.charter_problems(_charter(row, ANCHOR)), "is not a directory")
            (Path(tmp) / "reference" / "idioms").mkdir(parents=True)
            _has(check.charter_problems(_charter(row, ANCHOR)), "holds no rubric files")
        finally:
            check.REPO = real


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


def test_block_style_tools_are_read_past_the_first_entry():
    """#57: `^tools:\\s*(?P<tools>.+)$` captured `- Read` and stopped, so a judge
    declaring `Write` and `Task` as list entries 2 and 3 reported zero problems."""
    text = BLOCK_JUDGE.replace("  - Grep\n", "  - Write\n  - Task\n")
    problems = check.scan("agents/rogue-auditor.md", text)
    _has(problems, "declares the Write tool")
    _has(problems, "declares the Task tool")
    # Same file with CRLF terminators. A frontmatter pattern that stops the
    # closing `---` at `[ \t]*$` matches nothing here, and no frontmatter parses
    # to no tools — a fail-open in the one check that must not have one.
    _has(check.scan("agents/rogue-auditor.md", text.replace("\n", "\r\n")), "Write tool")


def test_block_style_read_only_judge_passes():
    assert check.scan("agents/security-auditor.md", BLOCK_JUDGE) == []


def test_bracketed_inline_tools_are_read():
    text = CLEAN_JUDGE.replace(
        "tools: Read, Grep, Glob, Bash", "tools: [Read, Grep, Write]"
    )
    _has(check.scan("agents/x.md", text), "declares the Write tool")


def test_a_block_list_never_escapes_the_frontmatter():
    """The list ends at the next key; the parse ends at the closing `---`. A body
    bullet naming a tool is prose, and a body `tools:` line is documentation."""
    text = BLOCK_JUDGE + (
        "\nWhat this judge never does:\n\n"
        "- Write the fix it recommends.\n"
        "- Task another agent to apply one.\n\n"
        "A producer would declare tools: Read, Write, Edit. You are not one.\n"
    )
    assert check.scan("agents/x.md", text) == []


def test_missing_tools_key_rejected():
    """The laziest frontmatter is the most permissive one: an omitted `tools:`
    key inherits every tool available to subagents, `Write` and `Task` among
    them. Parsed to `[]` and passed clean until the guard failed closed (#62)."""
    text = "---\nname: security-auditor\nmodel: opus\n---\n\nInspect read-only.\n"
    _has(check.scan("agents/x.md", text), "declares no `tools:` key")


def test_unparseable_frontmatter_rejected():
    for text in (
        "# Security lane\n\nInspect read-only.\n",  # no frontmatter at all
        "---\nname: security-auditor\ntools: Read, Grep\n",  # never terminated
    ):
        _has(check.scan("agents/x.md", text), "no terminated `---` frontmatter")


def test_tools_key_naming_nothing_readable_rejected():
    """Three ways to write a declaration this parser cannot resolve. Each once
    yielded silence, which is what a judge declaring only read tools yields."""
    for value in ("", " []", " [Read,"):
        text = CLEAN_JUDGE.replace("tools: Read, Grep, Glob, Bash", f"tools:{value}")
        _has(check.scan("agents/x.md", text), "naming no tool this check can read")


def test_a_comment_never_truncates_a_block_list():
    """A comment or blank line interrupts a block sequence without ending it;
    stopping there drops every entry below, which is the original bug's shape."""
    text = BLOCK_JUDGE.replace("  - Grep\n", "  # the read set\n\n  - Write\n")
    _has(check.scan("agents/x.md", text), "declares the Write tool")
    trailing = BLOCK_JUDGE.replace("  - Grep\n", "  - Write  # for the fix\n")
    _has(check.scan("agents/x.md", trailing), "declares the Write tool")


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

    The prose beside the template carries §4's omit-not-null rule verbatim, and
    that copy is checked against the contract's own bytes: a rule paraphrased
    down to one field teaches the omit case for that field alone, which is how
    #52's `locus.line` fix left `anchor` to recur as #72.
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
    contract = " ".join((REPO / "docs/findings-contract.md").read_text().split())
    omit_rule = re.search(r"An optional field[^.]*\.", contract)
    assert omit_rule, (
        "§4 no longer states the omit-not-null rule in the form the fleet copies — "
        "this guard derives the sentence from the contract so the copies cannot drift"
    )
    judges, _ = check.parse_charter((REPO / "reference/charter.md").read_text())
    for j in judges:
        text = (REPO / j["path"]).read_text()
        assert omit_rule.group(0) in " ".join(text.split()), (
            f"{j['judge']} does not state §4's general omit rule verbatim: "
            f"{omit_rule.group(0)!r}. A rule scoped to one field teaches the omit "
            f"case for that field only — #52 taught it for `locus.line`, and #72 "
            f"was a judge sending `anchor: null`, losing eight findings and a "
            f"critical. Every optional field is exposed identically"
        )
        blocks = re.findall(r"```json\n(.*?)```", text, re.DOTALL)
        assert blocks, f"{j['judge']} documents no JSON output template"
        doc = json.loads(blocks[-1])
        assert set(doc) == required_top, f"{j['judge']} template keys: {set(doc)}"
        assert doc["contract_version"] == schema.CONTRACT_VERSION
        assert doc["judge"] == j["judge"]
        assert set(doc["findings"][0]) <= finding_fields, (
            f"{j['judge']} template has a finding field the contract does not define"
        )
        rec = doc["findings"][0].get("recommendation", "")
        assert "≤25 words" in rec, (
            f"{j['judge']}'s template must state the recommendation cap — a field "
            f"with no stated cap drifts (measured: summary caps at 15 and lands at "
            f"11; recommendation capped at nothing landed at 42)"
        )
        if "line" in doc["findings"][0]["locus"]:
            assert re.search(
                r"omits? .{0,40}?`(?:locus\.)?line`|`(?:locus\.)?line`.{0,40}?\bomits?\b",
                " ".join(text.split()),
            ), (
                f"{j['judge']}'s template shows locus.line populated and never says to "
                f"omit it — the shape a judge with a whole-file or absence finding "
                f"reaches for is `null`, which fails validation and loses the entire "
                f"findings document (#52)"
            )
        for enum, field in ((schema.TIERS, "tier"), (schema.BASES, "basis")):
            offered = {v.strip() for v in doc["findings"][0][field].split("|")}
            assert offered == set(enum), (
                f"{j['judge']} offers {field} values {offered}, contract has {set(enum)}"
            )


def test_every_intake_lane_states_the_document_quote_rule():
    """Quote-or-demote matches only spans inside double quotation marks, and
    `scripts/dispatch.py` mounts a `--document` run at `intake` — so the intake
    declarers are today exactly the lanes that face the rule. A new declarer
    means this guard covers one more lane, not that it is stale.

    A lane told to quote the document but not to delimit the quote, or told to
    quote some other file and never the artifact, files a compliant critical
    that ingest demotes as a fabrication every time (#59). Both the agent file
    and the charter's anchor row must say it: the rule living in three places
    with the copies drifting is the defect this test exists for.
    """
    judges, anchors = check.parse_charter((REPO / "reference/charter.md").read_text())
    intake = [j for j in judges if "intake" in check._cell_tokens(j["mounts"])]
    assert intake, "no intake lane is registered — this guard has gone vacuous"
    for j in intake:
        text = " ".join((REPO / j["path"]).read_text().split())
        assert "double quotation marks" in text, (
            f"{j['judge']} judges a document at intake and never states that the "
            f"anchor's quote goes inside double quotation marks — a verbatim but "
            f"undelimited anchor demotes as a fabrication"
        )
        assert re.search(r"quot\w+[^.]{0,140}document|document[^.]{0,140}quot\w+", text), (
            f"{j['judge']} never says the anchor quotes the judged document — the "
            f"quote rule keys on artifact kind, so a lane citing only another file "
            f"demotes on every document run"
        )
        assert "double quotation marks" in anchors[j["judge"]], (
            f"the charter's anchor row for {j['judge']} omits the delimiter its "
            f"agent file states — the copies have drifted"
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


def test_readme_lane_table_matches_the_roster():
    """The README lists the lanes for a reader, which duplicates roster data —
    the drift this whole file exists to prevent, one document over."""
    judges, _ = check.parse_charter((REPO / "reference/charter.md").read_text())
    registered = {j["judge"] for j in judges}
    named = set(
        re.findall(r"`([a-z][a-z-]*(?:auditor|reviewer))`", (REPO / "README.md").read_text())
    )
    assert registered - named == set(), f"README omits {registered - named}"
    assert named - registered == set(), f"README names unregistered {named - registered}"


def test_the_command_can_dispatch_every_artifact_kind():
    """The entrypoint is the only thing a human can run, so a kind the contract
    defines and the command never dispatches is a lane with no runnable path —
    which is what `repository` was for five releases, stranding 7 of 23 judges
    (#58). The `repository` kind reached `dispatch.py`, `schema.py`, `report.py`,
    the charter, and the contract in #38, and nothing failed when it missed the
    one file that runs them."""
    text = (REPO / "commands/review.md").read_text()
    unmapped = set(schema.ARTIFACT_KINDS) - set(KIND_FLAGS)
    assert not unmapped, f"KIND_FLAGS names no dispatcher flag for {unmapped}"
    for kind, flag in KIND_FLAGS.items():
        assert flag in text, (
            f"commands/review.md never passes {flag}, so no human can run a "
            f"{kind} artifact through the gauntlet"
        )


def test_every_dispatch_block_passes_the_worktree_root():
    """§1 builds a worktree so judges read the tree they are judging; a dispatch
    block that drops `--root` spends the checkout and then judges whatever is on
    disk, which is the failure the worktree was added to prevent (#28).

    A document run is the one exemption, ruled in §1 — it names one file and
    builds no worktree, so it has no root to pass and the human's working
    directory is the right default.
    """
    blocks = [
        block
        for block in re.findall(
            r"```bash\n(.*?)```", (REPO / "commands/review.md").read_text(), re.DOTALL
        )
        if "dispatch.py" in block
    ]
    assert blocks, "commands/review.md shows no dispatch call at all"
    for block in blocks:
        assert "--root" in block or "--document" in block, (
            f"this dispatch block never passes --root, so its judges read the "
            f"working directory rather than the tree §1 resolved:\n{block}"
        )


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
