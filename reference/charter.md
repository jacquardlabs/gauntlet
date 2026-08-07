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

**One grant the check deliberately does not cover: `Bash`.** Every judge declares it,
because reading a repository at a ref is `git` and `grep`; adding it to `MUTATION_TOOLS`
would disarm the whole fleet. So the residual is real — a judge induced past its
injection-defense clause can write, read `~/.ssh`, or reach the network through the
shell. What holds that line is the prompt clause in every judge, not the check.

Both rules are about credibility, not purity. Findings land in the left margin of a
consumer's workspace as machine facts; a fact whose author had a stake in the outcome
is not a fact.

## Judges

The roster. Columns are load-bearing:

- **Judge** — the registered name a consumer passes as `judge` in the invocation
  (`docs/findings-contract.md` §3).
- **Lane** — the one concern it owns. One judge, one lane; a judge that finds something
  outside its lane escalates in `coverage`, never hunts.
- **Mounts** — which question it may be asked: `intake` (judging a proposal),
  `acceptance` (judging what was produced), `posture` (judging a whole repository as it
  stands), or any combination. A consumer never requests an undeclared mount. The enum
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
| `code-auditor` | code quality | `acceptance` | `idioms/` | `agents/code-auditor.md` |
| `test-auditor` | test adequacy | `acceptance` | (inline) | `agents/test-auditor.md` |
| `architecture-auditor` | structural fit | `acceptance` | (inline) | `agents/architecture-auditor.md` |
| `doc-auditor` | documentation | `acceptance` | (inline) | `agents/doc-auditor.md` |
| `frontend-reviewer` | frontend quality | `acceptance` | (inline) | `agents/frontend-reviewer.md` |
| `ux-reviewer` | user experience | `acceptance` | (inline) | `agents/ux-reviewer.md` |
| `product-reviewer` | product fit | `intake`, `acceptance` | (inline) | `agents/product-reviewer.md` |
| `premortem-auditor` | pre-mortem register | `acceptance` | `premortem-format` | `agents/premortem-auditor.md` |
| `prompt-auditor` | model-facing instructions | `acceptance` | `prompt-checklist` | `agents/prompt-auditor.md` |
| `falsifiability-auditor` | falsifiability | `intake` | (inline) | `agents/falsifiability-auditor.md` |
| `trade-study-auditor` | trade study | `intake` | `trade-study-format` | `agents/trade-study-auditor.md` |
| `security-posture-auditor` | security posture | `posture` | `security-checklist` | `agents/security-posture-auditor.md` |
| `codebase-posture-auditor` | codebase posture | `posture` | `idioms/` | `agents/codebase-posture-auditor.md` |
| `architecture-posture-auditor` | structural posture | `posture` | (inline) | `agents/architecture-posture-auditor.md` |
| `prompt-posture-auditor` | prompt-surface posture | `posture` | `prompt-checklist` | `agents/prompt-posture-auditor.md` |
| `docs-posture-auditor` | documentation posture | `posture` | (inline) | `agents/docs-posture-auditor.md` |
| `product-posture-reviewer` | product posture | `posture` | (inline) | `agents/product-posture-reviewer.md` |
| `interface-posture-reviewer` | interface posture | `posture` | (inline) | `agents/interface-posture-reviewer.md` |

The rest of the fleet migrates from studious under issue #2, in the cohorts recorded
there. A judge is registered here in the same change that adds its file; a row without a
file, a file without a row, or a standard that resolves to nothing all fail the check —
see "Two kinds of standard" for what a Standard cell may resolve to.

**Why `product-reviewer` declares both mounts, and no one else does yet.** Its question
has two genuinely different forms: at intake, "does this solve a real problem for a named
persona"; at acceptance, "does what shipped deliver that". Same lane, same standard, two
question sets — which is what a mount is for. This is the case the security ruling below
predicted.

**Why `security-auditor` declares only `acceptance`.** Mounts are claims about where a
judge's standard applies, not about ambition. The security checklist grades traced
source-to-sink paths in real code — at intake there is no code to trace, so an
intake-mounted run would produce inferred findings dressed as sourced ones. A lane earns
`intake` by having a standard that reads a proposal; the product lane will, this one
does not.

**Why `posture` is a mount and not a cadence (#13).** The periodic `review-*` family
asks a third question — not "should this be built" and not "does this deliver", but
"what is the state of this repository". That is a mount. What it is *not* is a schedule:
the family was named `periodic` in studious after how it was triggered, and carrying
that name into a payload would have put a calendar in the contract. Two consumers
running the same standing review weekly and quarterly ask an identical question, and a
judge cannot tell them apart — so cadence stays with the consumer that owns the
scheduling, and the mount names the question.

**Why `product-posture-reviewer` has no context gate and `product-reviewer` does.**
`scripts/dispatch.py` drops `product-reviewer` when no PRODUCT.md is supplied, because a
lane judging a change against a product definition that does not exist can only produce
preference. The posture lane inverts that: **the absence of a stated product intent is
its most valuable finding**, and gating it would guarantee the projects that most need
to hear it never do. It runs, falls back to the README as a proxy, marks everything
`inferred`, and reports the gap.

A `posture` judge reads a `repository` artifact (contract §3) rather than a changeset,
which is what makes the migration mechanical: the eight studious `review-*` agents lose
`Write`, their report-writing step becomes the consumer's, and the diff-scoping their
prompts assume becomes a whole-repo read at one `ref`.

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

## How the document surface grows (#37)

Most document types fail one way: the document makes no claim that could later be shown
wrong. A plan step with no success signal, a design doc with no stated rollback, an
experiment with no stopping rule — the same finding in different clothes. So the
document surface is factored around that question, not around document types:

- **One falsifiability lane** owns "what does this commit to, and how would we know it
  was wrong?" for any document at `intake`. Plans are its primary dispatch; design
  docs, RFCs, postmortems, experiment designs, and ADRs ride it with a type standard.
- **Type depth is data, not architecture.** Per-type specifics arrive as a standard:
  one gauntlet owns in `reference/` (the premortem pattern) or one the consumer
  supplies through `context` (the product-reviewer pattern — anything an org would
  swap: RFC templates, postmortem formats, launch checklists). Adding a document type
  is a standard plus a dispatch row, never an agent file.
- **A bespoke lane is earned when the type changes what verification means**, not its
  vocabulary. `premortem-auditor` clears the bar (register ids, three-verdict
  semantics); `trade-study-auditor` does (`cell` locus, recommendation derived from
  the matrix — the contract pre-wired both); a deprecation plan, SLO doc, or runbook
  does not.
- **Documents are named, never sniffed.** Changeset judges are selected from changed
  paths; a document has no diff, so the consumer names the artifact and the lane — the
  `CONTEXT_SIGNALS` shape in `scripts/dispatch.py`, never a second `PATH_SIGNALS`
  (#43).
- **A new lane or dimension is earned by a realized failure**, not a plausible
  category — the SRE launch-review substantiation rule, and the pre-mortem register is
  the machinery that records realized failures. The fleet grows under its own evidence
  discipline.
- **No lane where a deterministic tool is the incumbent.** Commands-that-work is
  execution, alert-has-runbook is lint, SLI-measurable-today needs live metrics. A
  document lane owns semantic judgment nothing mechanical checks — "code owns
  bookkeeping, prompts own judgment", pointed outward.

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
| `code-auditor` | a behavior delta: the input, the code path at `file:line`, and the wrong output or crash it produces |
| `test-auditor` | a named test or command whose result the artifact changes, or a load-bearing behavior with no test at all, named |
| `architecture-auditor` | the contract that broke and the downstream consumer that relies on it, named by path |
| `doc-auditor` | a command or path the docs state, quoted, that does not exist or does not work as written |
| `frontend-reviewer` | a reproducible broken flow: the steps, the expected result, the observed one |
| `ux-reviewer` | a reproducible broken flow: the steps, the expected result, the observed one |
| `product-reviewer` | the stated criterion, principle, persona, or journey — quoted from PRODUCT.md inside double quotation marks — that the artifact does not deliver; on a `document` artifact, plus the failing span quoted the same way from the judged document, each quote named for its source |
| `premortem-auditor` | the register item, by id, marked REALIZED, plus the evidence that realized it |
| `prompt-auditor` | the instruction or invariant the prompt surface contradicts, quoted, with the file it comes from |
| `falsifiability-auditor` | the commitment quoted verbatim from the document, inside double quotation marks, that cannot be checked as written — or, for an absence, the enclosing step or section quoted the same way, so a reader can verify nothing in it commits |
| `trade-study-auditor` | the cell or recommendation quoted verbatim from the document, inside double quotation marks, plus the checkable fact it misstates or omits — a whole-matrix finding (a weight with no stated reason, a criterion only the winner satisfies) quotes the recommendation or criterion row it indicts |
| `security-posture-auditor` | a named signature from `reference/security-checklist.md` plus the traced path from untrusted input to that sink at `file:line`, or the commit sha that exposed credential material and whether it is live at the judged ref |
| `codebase-posture-auditor` | the measured total and the specific instance that makes it urgent, at `file:line` — a count alone is a metric, not a critical |
| `architecture-posture-auditor` | both ends of the structural edge, the verified import or call that proves it, and the development cost it currently imposes |
| `prompt-posture-auditor` | the instruction or invariant the prompt surface contradicts, quoted, with the file it comes from — both sides quoted when the finding is a drifted seam |
| `docs-posture-auditor` | the command, path, or claim the docs state, quoted, plus the evidence it does not exist or does not work as written |
| `product-posture-reviewer` | the documented claim — persona, principle, not-building entry, or known problem — quoted from PRODUCT.md, plus the evidence that contradicts it |
| `interface-posture-reviewer` | a reproducible broken flow (steps, expected, observed), or the concept and each surface's differing rendering quoted at `file:line` |

Documents are the most taste-exposed surface the fleet judges, and an anchor is cheaper
to fake there than on code. So on a `document` artifact a critical's anchor must contain
a verbatim quote from the artifact **inside double quotation marks**, and ingest verifies
the quote appears — a fabricated anchor demotes the same way a missing one does, and so
does a true quote nobody delimited (#44). An absence finding ("this step names no success
signal") quotes the enclosing unit it indicts, which the same check covers.

The rule keys on artifact kind, never on lane, and an anchor may carry more than one
quoted span — one span matching the artifact satisfies it. That is how a lane whose
anchor cites a second file still clears the check rather than being exempted from it:
`product-reviewer` quotes the PRODUCT.md criterion and the document span that fails it,
each named for its source (#59).

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
- `README.md` — lists the lanes for a reader, which duplicates roster data;
  `tests/test_independence.py` fails if the two disagree in either direction.
- `scripts/dispatch.py` — reads this roster at runtime to select judges and resolve each
  Standard cell into a citable `standard`. Its `PATH_SIGNALS` table is keyed by
  registered judge name so it joins to the roster rather than to prose, and
  `tests/test_dispatch.py` fails if a key is not a registered judge. A judge with no rule
  there runs unconditionally — the safe default is to dispatch a lane and let it
  self-skip, never to drop one because nobody wrote its rule.
