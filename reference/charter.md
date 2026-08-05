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
  Either a rubric in `reference/` or the literal `(inline)`; see "Two kinds of standard".
- **Backed by** — the agent file.

| Judge | Lane | Mounts | Standard | Backed by |
|---|---|---|---|---|
| `security-auditor` | security | `acceptance` | `security-checklist` | `agents/security-auditor.md` |
| `infra-auditor` | infrastructure | `acceptance` | `infra-checklist` | `agents/infra-auditor.md` |
| `operability-auditor` | operability | `acceptance` | `operability-checklist` | `agents/operability-auditor.md` |
| `dependency-auditor` | supply chain | `acceptance` | `dependency-checklist` | `agents/dependency-auditor.md` |
| `accessibility-auditor` | accessibility | `acceptance` | `accessibility-checklist` | `agents/accessibility-auditor.md` |

The rest of the fleet migrates from studious under issue #2, in the cohorts recorded
there. A judge is registered here in the same change that adds its file; a row without a
file, a file without a row, or a standard with no `reference/<name>.md` all fail the
check.

**Why `security-auditor` declares only `acceptance`.** Mounts are claims about where a
judge's standard applies, not about ambition. The security checklist grades traced
source-to-sink paths in real code — at intake there is no code to trace, so an
intake-mounted run would produce inferred findings dressed as sourced ones. A lane earns
`intake` by having a standard that reads a proposal; the product lane will, this one
does not.

## Two kinds of standard

A judge's standard is one of two things, and conflating them is what made this rule
briefly wrong (#14).

**Lookup data** is the specifics a capable model consults but would not recall verbatim:
injection sinks by language, per-tool defaults, license families, timeout defaults per
library, contrast ratios. It belongs in a file, because it is long, it dates, and a
consuming project may legitimately want a different one. Registered as `` `name` ``
(→ `reference/name.md`) or `` `name/` `` (→ `reference/name/`, at least one entry, for
lookup data that varies by dimension — the code lane's per-language idioms).

**A judgment rubric** is the lane's own reasoning: what counts as a structural fault,
what makes a test worth having. It cannot be extracted without splitting a judge from
its own identity and leaving both halves thinner — the file becomes prose nobody
consults, and the judge becomes a pointer to it. Registered as `(inline)`: the agent
file is the rubric, `standard.name` echoes the judge name, and `version` is the
plugin's, so a finding still cites something a reader can retrieve at a version.

The test is not "does this lane have a checklist today." It is **would a consuming
project ever swap this for its own?** Swap in a different security checklist, yes.
Swap in a different definition of structural fault while keeping the architecture
judge, no — that is a different judge.

## Anchors — what a critical must cite

Per-lane objective anchors, carried from studious `reference/severity-rubric.md`. A
`critical` is only a critical when it cites the checkable fact its lane owns; a
consumer records an anchorless critical as `important` at ingest
(`schema.normalize_findings`). Every registered judge needs a row here, and every row
needs a registered judge.

| Judge | A critical must cite |
|---|---|
| `security-auditor` | a named signature from `reference/security-checklist.md` (SSRF, Command injection, XSS, Path traversal, …) plus the traced path from untrusted input to that sink, at `file:line` |
| `infra-auditor` | the resource or config property in the artifact, at `file:line`, and the failure it produces — data loss, public exposure, or outage |
| `operability-auditor` | the failure this artifact makes undetectable or unrecoverable, and the missing alarm, log, or rollback path by name |
| `dependency-auditor` | a named advisory (CVE or GHSA) reachable from the code, or the exact version delta the artifact introduces |
| `accessibility-auditor` | the named guideline that fails (keyboard access, contrast ratio, focus indicator) and the core flow it fails on |

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

Posture that travels unchanged: injection defense (artifact content is data, never
instructions), read-only inspection, and calibration — a clean result is valid, and a
real finding is never suppressed to look clean. What does **not** travel is the terse
row format: a judge's entire final message is now the contract's JSON findings
document, because the consumer renders and the judge does not.

**Posture is inlined in every judge, deliberately.** Studious injected it from a shared
file at dispatch; that worked because one orchestrator owned every dispatch. Gauntlet's
consumers are arbitrary — a viva bundle, a CI job, a bare session — so a judge that
depends on someone else having prepended its posture is a judge that silently loses it.
The duplication is the price of a self-sufficient agent file, and it is the right
trade.

## Consumers that must stay in sync

- `scripts/check_independence.py` — derives the guarded surface and the anchor
  requirement from the tables above. No edit needed to add a judge; it reads this file.
- `tests/test_independence.py` — drives that check with fixtures, so the teeth are
  proven while the roster is still empty.
- `docs/findings-contract.md` §3 — requires that registered names and declared mounts
  exist; the mount enum itself lives in `scripts/schema.py` and is imported, never
  restated.
