# gauntlet

Run a changeset through a row of independent judges. Each one owns a single lane, grades
what it sees against a standard it owns, and returns findings you can check — never a
verdict, never a fix.

```text
/gauntlet:review 142
```

```text
# Gauntlet — https://github.com/you/app/pull/142 a1b2c3d4e5f6..f6e5d4c3b2a1

2 critical · 9 important · 10 track — from 6 judges: architecture-auditor,
code-auditor, dependency-auditor, doc-auditor, security-auditor, test-auditor

## Critical — blocks the stamp

### Unsanitized branch name reaches shell in release script

`security-auditor` · injection · scripts/release.sh:42 · sourced/high

**Anchor.** Command injection (security-checklist): $BRANCH interpolated into eval
at scripts/release.sh:42, reachable from the PR title.

**Fails when.** A PR titled `x; rm -rf .` becomes the branch slug; the release run
executes it.

**Do.** Quote the variable and validate the slug against ^[a-z0-9-]+$ at entry.
```

Findings are yours to act on. Gauntlet never decides whether that ships.

## Install

```text
/plugin marketplace add jacquardlabs/marketplace
/plugin install gauntlet@jacquardlabs-marketplace
```

Until the marketplace entry lands ([#6](https://github.com/jacquardlabs/gauntlet/issues/6)),
clone the repo and add the checkout as a local plugin directory.

Nothing to configure. Judges read whatever context docs your project already has —
CLAUDE.md, DESIGN.md, PRODUCT.md — and say in `coverage` when one they wanted was
missing.

## Use

**Review the current branch** against its merge-base:

```text
/gauntlet:review
```

**Review a pull request** — it resolves the PR, checks the head out so judges read the
PR's tree rather than whatever is on your disk, and offers to post the findings as review
comments once you have read them:

```text
/gauntlet:review 142
/gauntlet:review https://github.com/you/app/pull/142
```

Posting is comments only, after you say yes. Gauntlet will not approve a PR or request
changes on one — that verdict is yours to give, and a tool that posted it would be
laundering a tally into a judgment nobody made.

Only the lanes your changes touch are dispatched, and the run says which it skipped and
why. A Python-only changeset costs eight judges; a `.tsx` and `.css` changeset costs eleven.

## The lanes

Twenty-three today, each with one concern and its own standard. Fourteen judge a
changeset; seven judge a whole repository as it stands (see "Standing reviews" below);
two judge a document before the work exists (see "Judging documents" below).

| Judge | Judges | Standard |
|---|---|---|
| `security-auditor` | injection, auth, authorization, secrets, headers, CSRF, data exposure, unsafe dependency use | `security-checklist` |
| `code-auditor` | type safety, complexity, maintainability, consistency, idioms, error handling, hygiene | `idioms/<language>` |
| `test-auditor` | coverage of the change, assertion quality, regression tests on fixes, weakened or skipped tests | its own prompt |
| `architecture-auditor` | pattern fit, coupling, complexity distribution, backend performance, data and migrations | its own prompt |
| `infra-auditor` | IaC misconfiguration, blast radius, CI/CD pipeline risk, container hygiene, cost signals | `infra-checklist` |
| `operability-auditor` | failure signal, resilience, runtime hygiene, concurrency safety, ops commitments | `operability-checklist` |
| `dependency-auditor` | new and updated packages, known vulnerabilities, licenses, maintenance signal, lockfile drift | `dependency-checklist` |
| `accessibility-auditor` | keyboard access, contrast, focus management, semantic HTML | `accessibility-checklist` |
| `frontend-reviewer` | component architecture, state, data fetching, render performance, bundle, error handling | its own prompt |
| `ux-reviewer` | hierarchy, spacing, component consistency, interaction clarity, responsive behavior, polish | your DESIGN.md |
| `doc-auditor` | comments and docstrings, API and type docs, README drift, TODO hygiene | its own prompt |
| `product-reviewer` | problem validity, principles, journeys, scope, simplicity — then whether what shipped delivers it | your PRODUCT.md |
| `premortem-auditor` | every failure mode recorded at design time, checked against what was built | `premortem-format` |
| `prompt-auditor` | trigger reliability, instruction conflicts, contract drift, duplication, injection safety, token economy | `prompt-checklist` |

Two lanes need something beyond the code and stay silent without it: `product-reviewer`
wants your PRODUCT.md, and `premortem-auditor` wants a pre-mortem register — plain
markdown, three fields, written by whoever you like. Gauntlet never writes one: a judge
that invents the failure modes and then checks them finds exactly the ones it thought of.
Keep neither and neither lane is ever dispatched.

`product-reviewer` is the only lane that fires **before** the work as well as after —
at intake it judges a proposal, at acceptance it judges what shipped. Every other lane
in that table judges the finished change.

A judge whose lane your change does not touch returns nothing and says so. That is a
complete result, not a failure — and it is reported, so a lane that never ran can never
be mistaken for a lane that found nothing.

## Standing reviews

Every lane above judges a change. Seven judge the repository itself, at one ref, with no
diff in sight — which is the only way to reach a defect sitting in code no recent branch
has touched, or an inconsistency that only shows up when you look at every surface at
once.

| Judge | Judges | Standard |
|---|---|---|
| `security-posture-auditor` | pre-existing vulnerabilities, secrets anywhere in git history, security-config baseline, dependency confusion | `security-checklist` |
| `codebase-posture-auditor` | debt totals, dead code, dependency health, test health, interface consistency — as aggregates and direction | `idioms/<language>` |
| `architecture-posture-auditor` | boundaries, complexity distribution, evolution readiness, data layer — against what the code actually does | its own prompt |
| `prompt-posture-auditor` | trigger coverage, instruction conflicts, contract drift across seams, duplication, injection posture, token economy | `prompt-checklist` |
| `docs-posture-auditor` | stale claims, missing capabilities, commands and paths that do not resolve, voice drift, structure gaps | its own prompt |
| `product-posture-reviewer` | whether PRODUCT.md is still true — personas, principles, scope creep, stale known problems — and whether the product still coheres | its own prompt |
| `interface-posture-reviewer` | cross-surface consistency, per-surface design-system adherence, accessibility, responsive behavior | its own prompt |

These answer a third question. `intake` asks whether a thing should be built and
`acceptance` asks whether what shipped delivers; **`posture` asks what state the
repository is in**. The mount is named for the question, not for a schedule — run them
weekly or once a quarter, the question is identical and the cadence is yours.

They read a whole repository at a `ref` rather than a changeset, so they cost more than
a review and are worth running on a trunk, not a branch:

```text
git ls-files | python3 scripts/dispatch.py --ref HEAD --paths -
```

**Every run is a baseline, and that is the design.** These lanes measure the repository
as it stands; they do not remember the last run, because a judge that kept its own
history would need a report store, and judges do not write. Continuity belongs in your
issue tracker — file what you intend to act on, and the tracker holds the trend across
cycles where you can actually work it.

If a consumer does keep prior findings, passing them in the invocation's `context` lets
a lane name what is new, persistent, or resolved. That is a convenience, not the
intended flow: nothing in gauntlet expects a report directory to exist.

## Judging documents

Everything above judges work — a change, or the repository it landed in. Two lanes
judge the document that proposes work, before any exists:

```text
/gauntlet:review docs/migration-plan.md
```

`falsifiability-auditor` reads the named file at `intake` and asks one question: what
does this document commit to, and how would we know it was wrong? A step consuming the
output of a later step, a step with no success signal, an irreversible step with no
stated recovery, a scope the named design never agreed to — and, first among them, a
document that commits to nothing at all. Plausible prose with nothing checkable in it
is the finding, not evidence of health: fluency is exactly what a reviewer is most
inclined to wave through.

Plans and migration plans need nothing beyond the file. Design docs, RFCs, postmortems,
experiment designs, and ADRs ride the same lane with a type standard your project
supplies as context — what a postmortem must commit to (action items with owners) is
not what an experiment design must (a stopping rule stated before it runs). Adding a
document type is a standard, never a new judge — unless the type changes what
verification means, which is what earns the second lane:

`trade-study-auditor` fires when the document decides by comparison — named options
scored against criteria, a recommendation claiming to follow. It checks that every
load-bearing cell carries a citation a reader can check, that the recommendation
derives from the matrix rather than sitting beside it, and that each losing option was
engaged at its strongest. A weight with no stated reason, a criterion only the winner
satisfies, a strawmanned runner-up — a matrix arranged to reach its answer is the
lane's defining finding. Findings land on a cell (`Cost at 10k rps × DynamoDB`), the
locus no other lane uses; `reference/trade-study-format.md` is the minimal shape it
judges against, and a document with no matrix costs the lane a self-skip and nothing
else.

On a document, a critical's anchor is a verbatim quote, and ingest checks that the
quote actually appears — a fabricated anchor demotes the same way a missing one does.

## How to read a finding

Three things on every finding are worth knowing how to read.

**Tier** — `critical` blocks the stamp, `important` is this cycle's work, `track` is
logged and revisited. Three tiers, never a fourth.

**Anchor** — a `critical` must cite the checkable fact its lane owns: a named
vulnerability signature plus the traced path to the sink, a behavior delta with its input
and wrong output, the contract that broke and who depends on it. **A critical citing no
anchor is recorded `important`**, and the report says so under *Recorded differently than
claimed*. A tier is a claim about your code, not about how the reviewer feels about it.

**Grounds** — `sourced` cites something you can go check; `inferred` was reasoned from
the artifact without a direct citation; `taste` is preference, labelled as preference and
never ranked above `track`. There are no confidence percentages, because a number would
imply a precision nobody has.

## Composition

Gauntlet is judges plus thin consumers. Two consumers exist by design:

- **`/gauntlet:review`** — the Claude Code entrypoint above.
- **[viva](https://github.com/jacquardlabs/viva)** — type bundles name gauntlet judges per
  document type (design doc, packet, brief, trade study) through the same contract.

Both cross the same boundary: `docs/findings-contract.md`, versioned, with schema
validators called on dispatch and on ingest. A judge emits findings; a consumer selects,
dispatches, validates, and renders. **A consumer never decides what happens next** — no
gate, no ledger, no retry policy, no episode state.

## Why the findings are worth anything

Two rules, and `scripts/check_independence.py` enforces the mechanically checkable half
of them in CI:

- **Fresh context.** A judge never graded its own production. It reads the artifact cold,
  with no memory of authoring it.
- **A judge never produces.** No writes, no edits, no commits, no fixes, no dispatching
  something else to fix. A registered judge carries no mutation tool and names no slash
  command, and CI fails if one acquires either.

Findings land as machine facts. A fact whose author had a stake in the outcome is not a
fact.

## Contributing

`CONTRIBUTING.md` has the local check suite, the repo settings, and the rule that a judge
is registered in `reference/charter.md` before its file exists.

This repo reclaims the name of an earlier, unrelated Jacquard Labs project whose remote
was retired.
