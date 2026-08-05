# Findings contract — v0 (draft)

The one interface every gauntlet judge emits and every consumer reads. This file
reaches v1 **before** the fleet migrates from studious — split on a contract, never a
convention (the jig lesson, studious#148: format agreements renegotiated in two repos
at once are the cost that forces a merge).

Status: **DRAFT**. Consolidates four sources:

- studious `reference/severity-rubric.md` — the three-tier ladder (Critical /
  Important / Track), per-lane objective anchors, and the anchor-or-demote rule ("a
  Critical that cites no anchor is recorded Important")
- studious `reference/evidence-format.md` — the receipts shape: in-toto test-result
  predicate, capturer provenance (capturer ≠ claimant stays checkable), output digests
- studious `reference/prompt-contract.md` — the fleet's shared posture, output format,
  and calibration
- viva `docs/headless-contract.md` — the model for what a versioned local contract
  looks like: schema validators called at the boundary, tests around them

## What v1 must pin

1. **Finding shape** — lane, tier, objective anchor, artifact locus (`file:line` for
   code; section/cell for documents), summary, failure scenario, receipt references.
2. **Tier ladder** — three tiers, never a fourth; anchor-or-demote carried over
   verbatim.
3. **Receipt shape** — the evidence records a finding may cite, with capturer
   provenance.
4. **Invocation** — how a consumer names a judge and hands it an artifact plus a
   standard. viva bundles need this; bare Claude Code use needs the same one.
5. **Mount points** — a judge declares where it fires: intake, acceptance, or both.
   Same judge, different mounts per bundle (ruled on viva#165/#169, 2026-08-04).
6. **Grounds classing** — sourced / inferred / taste on every recommendation, aligned
   with viva's `basis`/`level` annotation schema. Never numeric confidence.

## Open questions

- Validation mechanism: viva ships Python schema validators at the boundary; mirror
  that here, or publish JSON Schema and let consumers validate?
- Version negotiation: what a bundle pinned to contract v1 does when a judge speaks v2.
- Whether telemetry (studious `reference/telemetry-format.md`) is part of this contract
  or a private implementation detail.
