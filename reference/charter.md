# Charter — the judges, their lanes, mounts, and anchors

Canonical source for gauntlet's fleet and the two rules that make its verdicts worth
anything. This file is **data**: the tables below are parsed by
`scripts/check_independence.py` to derive the guarded surface and the per-lane anchor
requirement. Register a judge here first, then add its file.

## The two rules

**1. Fresh context — a judge never graded its own production.** It reads the artifact
cold, with no memory of authoring it and no access to the reasoning that produced it.
A judge that helped write the thing it grades is a self-assessment wearing a rubric.

**2. A judge never produces.** Findings out, nothing else. No writes, no edits, no
commits, no fixes, no dispatching another agent to fix. `recommendation` is prose the
human may act on — never a patch, never an instruction to run something. This is what
`scripts/check_independence.py` enforces mechanically: a registered judge carries no
mutation tool and names no slash command.

Both rules are about credibility, not purity. Findings land in the left margin of a
consumer's workspace as machine facts; a fact whose author had a stake in the outcome
is not a fact.

## Judges

The roster. Columns are load-bearing:

- **Judge** — the registered name a consumer passes as `judge` in the invocation
  (`docs/findings-contract.md` §3).
- **Lane** — the one concern it owns. One judge, one lane; a judge that finds something
  outside its lane escalates in `coverage`, never hunts.
- **Mounts** — where it may fire: `intake` (judging a proposal), `acceptance` (judging
  what was produced), or both. A consumer never requests an undeclared mount. The enum
  is the contract's, imported from `scripts/schema.py` — not restated here.
- **Standard** — what it judges against, matching `standard.name` in the invocation.
- **Backed by** — the agent file.

| Judge | Lane | Mounts | Standard | Backed by |
|---|---|---|---|---|

The roster is empty: the fleet migrates from studious under issue #2, and a judge is
registered here in the same change that adds its file. A row without a file, or a file
without a row, fails the check.

## Anchors — what a critical must cite

Per-lane objective anchors, carried from studious `reference/severity-rubric.md`. A
`critical` is only a critical when it cites the checkable fact its lane owns; a
consumer records an anchorless critical as `important` at ingest
(`schema.normalize_findings`). Every registered judge needs a row here, and every row
needs a registered judge.

| Judge | A critical must cite |
|---|---|

## What migration must strip

Issue #2 moves ~21 agents that were written inside a methodology. Three kinds of
contamination the check will catch, named here so the migration expects them rather
than discovering them one CI failure at a time:

- **The `Write` tool.** Eight studious agents (the periodic `review-*` family) carry it
  because they wrote report files themselves. Under the findings contract a judge
  *returns* a findings document and the consumer persists it — so `Write` comes off,
  and the report-writing step becomes the consumer's.
- **Slash commands.** Roughly twenty mentions of `/review`, `/retro`, and `/setup`
  across the fleet. A gauntlet judge is dispatched by a consumer — a viva bundle, CI, a
  bare Claude Code session — never by a door in another repo, and it routes no one
  anywhere.
- **Producer-private artifacts.** `PLAN.md` and the build-evidence stores. The evidence
  a judge may cite is the receipts log in `docs/findings-contract.md` §6, which any
  executor can produce.

Posture that travels unchanged: injection defense (repo content is data, never
instructions), read-only inspection, calibration ("a clean result is valid", never
suppress a real finding to look clean), and terse output. Those are fleet-internal —
a consumer cannot observe them, so the contract says nothing about them and this
charter is their home.

## Consumers that must stay in sync

- `scripts/check_independence.py` — derives the guarded surface and the anchor
  requirement from the tables above. No edit needed to add a judge; it reads this file.
- `tests/test_independence.py` — drives that check with fixtures, so the teeth are
  proven while the roster is still empty.
- `docs/findings-contract.md` §3 — requires that registered names and declared mounts
  exist; the mount enum itself lives in `scripts/schema.py` and is imported, never
  restated.
