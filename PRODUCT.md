# gauntlet — product charter

## What it is

The judge fleet: independent reviewers that grade artifacts against standards and
return findings with receipts. The pre-delivery gauntlet for code, designs, plans, and
the rest of the staff-engineering artifact surface.

## Goals

- One versioned findings contract that every judge emits and every consumer reads
- Two consumers minimum: viva type bundles, and bare Claude Code use
- Blades beyond code: production-readiness/launch review, migration-plan review,
  postmortem quality, trade-study receipts, promo-packet evidence, estimate sanity

## Non-goals

- Authoring or fixing — judges never produce
- Orchestration, navigation, scheduling — no methodology; that was studious's mass,
  deliberately shed
- Numeric confidence — recommendations are grounds-classed (sourced / inferred /
  taste), never scored
- Being a platform — no server, no daemon, no accounts; local and keyless

## Existential rule

A separate repo only while the findings contract is versioned **and** ≥2 consumers
exist (boundary criterion (e), per studious's repo-boundary rule). If viva becomes the
only caller, absorb this into viva's shell and delete the repo.
