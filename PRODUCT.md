# gauntlet — product charter

## What it is

The judge fleet: independent reviewers that grade artifacts against standards and
return findings with receipts. The pre-delivery gauntlet for code, designs, plans, and
the rest of the staff-engineering artifact surface.

## Goals

- One versioned findings contract that every judge emits and every consumer reads
- Two consumers minimum: a Claude Code entrypoint here, and viva type bundles there
- Blades beyond code: code at `acceptance`, documents at `intake`, repositories at
  `posture` — one predicate across all three. The document surface grows by standards,
  not lanes (charter, "How the document surface grows"; ruled in #37)

## Non-goals

- Authoring or fixing — judges never produce
- Methodology — gates, episodes, ledgers, retry policy, routing between doors. That
  was studious's mass, deliberately shed. See "Consumers are thin" for the line
- Numeric confidence — recommendations are grounds-classed (sourced / inferred /
  taste), never scored
- Being a platform — no server, no daemon, no accounts; local and keyless
- The parts of the job that are not artifacts — mentoring, org navigation, meetings
- Checks a deterministic tool does better: docs-command execution, alert→runbook lint,
  live-metrics backtesting. A lane exists only where judgment has no mechanical
  incumbent (#37)
- Tracker maintenance — backlog hygiene, triage, prioritization. The tracker
  coordinates work rather than being work under review, and every answer it wants is a
  disposition: close this, merge that, do this first. Judges emit findings and never
  dispositions, which is the same wall `review-outcomes` hit (#2, #15, #39)

## Consumers are thin

A fleet nothing can dispatch is not a product, so gauntlet ships entrypoints. A consumer
selects the judges that apply, dispatches them, validates and normalizes their findings
through `scripts/schema.py`, and renders the result. Every side effect it has is one the
human confirmed in that same invocation.

What makes it thin is what it does **not** do: **a consumer never decides what happens
next.** No verdict of its own, no gate, no ledger, no retry policy, no episode state, no
routing onward to some other door. Anything that must remember a previous run belongs to
whoever called it. The test is durability — a consumer that needs to write state to work
a second time has become a methodology, and that is the mass this repo exists without.

This is the line the methodology non-goal draws, not an exception to it.

## Existential rule

A separate repo only while the findings contract is versioned **and** ≥2 consumers
exist (boundary criterion (e), per studious's repo-boundary rule). If viva becomes the
only caller, absorb this into viva's shell and delete the repo.
