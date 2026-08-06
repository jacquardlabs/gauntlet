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
why. A Python-only changeset costs six judges; a `.tsx` and `.css` changeset costs nine.

## The lanes

Fourteen today, each with one concern and its own standard.

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
| `premortem-auditor` | every failure mode recorded at design time, checked against what was built | your pre-mortem register |
| `prompt-auditor` | trigger reliability, instruction conflicts, contract drift, duplication, injection safety, token economy | `prompt-checklist` |

`product-reviewer` is the only lane that fires **before** the work as well as after —
at intake it judges a proposal, at acceptance it judges what shipped. Every other lane
judges the finished thing.

A judge whose lane your change does not touch returns nothing and says so. That is a
complete result, not a failure — and it is reported, so a lane that never ran can never
be mistaken for a lane that found nothing.

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
