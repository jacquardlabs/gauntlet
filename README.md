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

Standing up (2026-08-04). Contract first, then the charter, then the fleet:

| Piece | Where | State |
|---|---|---|
| Findings contract | `docs/findings-contract.md`, `scripts/schema.py` | v1 |
| Charter — roster, mounts, anchors | `reference/charter.md` | 1 judge registered |
| Independence check | `scripts/check_independence.py` | enforced in CI |
| Plugin manifest | `.claude-plugin/plugin.json` | v0.1.0, unreleased |
| The judges | `agents/` | security lane migrated; 20 to go (#2) |

Local checks, all stdlib:

```bash
for t in tests/test_*.py; do python3 "$t"; done
python3 scripts/check_independence.py
python3 scripts/validate_plugin.py
uv run --no-project --with ruff==0.16.0 ruff check scripts tests
```

This repo reclaims the name of an earlier, unrelated Jacquard Labs project whose remote
was retired.
