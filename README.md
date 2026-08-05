# gauntlet

Independent judges for pre-delivery artifacts. Run a changeset, design doc, migration
plan, or promo packet through the gauntlet: each judge grades it against a standard it
owns and returns findings with receipts.

One predicate governs every blade: **judges an artifact against a standard, with
receipts.** Two disciplines make the verdicts credible:

- **Fresh context** — a judge never graded its own production; it reads the artifact cold.
- **Judge never produces** — no blade fixes, authors, or orchestrates. Findings out,
  nothing else.

## Composition

Two consumers, by design:

- **[viva](https://github.com/jacquardlabs/viva)** — type bundles name gauntlet checkers
  per document type (design doc, packet, brief, trade study) through the findings
  contract.
- **Bare Claude Code** — install the plugin and run the fleet against a changeset
  directly.

## Status

Standing up (2026-08-04). Contract first: `docs/findings-contract.md` versions the
findings/receipts/invocation shape **before** any fleet migrates. The fleet itself —
21 review/audit agents — lives in [studious](https://github.com/jacquardlabs/studious)
and moves only after the contract reaches v1.

This repo reclaims the name of an earlier, unrelated gauntlet project (remote deleted;
sole local copy archived at `~/Projects/gauntlet-v1-archive`).
