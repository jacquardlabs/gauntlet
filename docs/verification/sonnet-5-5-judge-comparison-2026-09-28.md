# Sonnet 5.5 vs Opus 5.5 — judge comparison

## Method
- **Arms:** each of 9 lanes ran once on `opus` (Opus 5.5) and once with a `sonnet` override (Sonnet 5.5). Frontmatter `effort: medium` held for both. Sonnet 5.5's API default is `high`, and its effort levels are recalibrated from Sonnet 5, so this tests Sonnet at one level below its own default. The transcripts confirm the served model IDs (`claude-opus-5-5`, `claude-sonnet-5-5`). Plugin 0.17.3.
- **Candidates:** the 3 posture lanes #86 moved off sonnet (codebase, interface, prompt), plus 6 change lanes that do more mechanical checks (frontend, ux, accessibility, doc, dependency, infra). Security, code, architecture, test, operability, product, premortem, falsifiability, trade-study and docs-posture were out of scope.
- **Artifacts:**
  - jacquardlabs/winnow `9120a04..4ef29e9` (#55, UI views, +1526/-24, 17 files): frontend, ux, accessibility, doc.
  - winnow `eea4513..0dc1276` (better-sqlite3 added): dependency.
  - winnow `3071c6a..3bc4bf4` (CI workflow added): infra.
  - gauntlet posture at `4448859`: codebase, prompt.
  - winnow posture at `4ef29e9`: interface.
- **Invocations:** built by `scripts/dispatch.py` and read from detached worktrees.
- **Matching:** I compared findings by defect, not wording. When the arms disagreed, I checked the claim against the tree.

## Cost and speed

| Lane | Opus tokens / tools / s | Sonnet tokens / tools / s |
|---|---|---|
| frontend-reviewer | 33,101 / 6 / 48 | 26,424 / 2 / 25 |
| ux-reviewer | 56,869 / 10 / 201 | 33,624 / 4 / 41 |
| accessibility-auditor | 45,029 / 8 / 94 | 29,873 / 5 / 33 |
| doc-auditor | 34,755 / 6 / 44 | 20,269 / 4 / 21 |
| dependency-auditor | 24,746 / 8 / 58 | 19,687 / 5 / 20 |
| infra-auditor | 16,589 / 3 / 21 | 13,739 / 2 / 10 |
| codebase-posture-auditor | 29,163 / 9 / 54 | 16,947 / 4 / 16 |
| prompt-posture-auditor | 92,236 / 28 / 321 | 44,867 / 12 / 49 |
| interface-posture-reviewer | 94,840 / 20 / 279 | 27,728 / 6 / 29 |
| **Total** | **427,328 / 98 / 1,120** | **233,158 / 44 / 243** |

Sonnet used 55% of Opus's tokens and 22% of its summed runtime. Run in parallel, the slowest lane took 49s on Sonnet and 321s on Opus. At list prices, that is about 27% of Opus's cost.

Fewer tool calls tracked lost findings. Sonnet read about half as much, and on the lanes with the most to find it found about half as much.

## Results

| Lane | Opus / Sonnet findings (critical + important) | Verdict | Evidence |
|---|---|---|---|
| infra-auditor | 2 (0) / 2 (0) | **parity** | The same 2 pipeline findings on both arms. Opus adds `persist-credentials: false` to the fix. |
| frontend-reviewer | 6 (3) / 5 (2) | **near parity** | Both carry the swallowed static-edges failure and the unmemoized transcript. Sonnet rates refetch-on-view-switch as `track`, not `important`, and misses the unselectable "Off the flow" island. |
| doc-auditor | 2 (0) / 3 (0) | **near parity** | Opus alone flags `DESIGN.md`, which calls itself "the only interaction spec" but omits the new views and the 1/2/3 keys. Sonnet alone flags PRODUCT.md, which Opus correctly classed as older debt. |
| dependency-auditor | 2 (0) / 2 (0) | **Sonnet loses** | Sonnet misses that `better-sqlite3` ^11 is a major behind the maintained 12.x, and that `prebuild-install` fetches a binary the lockfile's hashes don't cover. Sonnet queried osv.dev for 11 of 38 new packages. It also claims "the project's MIT LICENSE", which is false: the tree has no LICENSE file and no `license` field. |
| accessibility-auditor | 10 (7) / 7 (5) | **Sonnet loses** | Sonnet misses 3 important findings: focus dropped to body after a chip click (`FlowView.tsx:311`), focus stranded by a view switch (`App.tsx:540`), and claim text available only in a tooltip (`TranscriptView.tsx:50`). It also misses 2 measured contrast shortfalls. |
| ux-reviewer | 14 (7) / 8 (4) | **Sonnet loses** | Sonnet misses that `a` approves, and `v` logs zoom, in views that show no claims or zoom (confirmed at `App.tsx:315-325`). It also misses that status and verdict bypass the `palette.ts` badges. |
| codebase-posture-auditor | 3 (0) / 2 (0) | **Sonnet loses** | Sonnet misses that `ci.yml` floats 6 action tags against `release.yml`'s stated pin policy, and that `dispatch.py` calls the private `_cell_tokens` at lines 106, 269 and 393. It states "no file over 500 lines", which is false: `scripts/report.py` has 717. It skipped dead code. |
| prompt-posture-auditor | 8 (2) / 4 (1) | **Sonnet loses** | Sonnet misses 2 confirmed important findings. The prompt-auditor path signals omit `prompt_templates/` and `*.prompt`, which the checklist lists (`dispatch.py:61`, `prompt-checklist.md:96`). And `frontend-reviewer` both forbids execution and demands an "observed" result (lines 34 and 98). Sonnet alone found the hardcoded `--context` at `review.md:119,132,148`, which I confirmed. |
| interface-posture-reviewer | 17 (11) / 7 (4) | **Sonnet loses** | Sonnet misses the only critical in the run: the receipt certifies hunk-depth zoom that was never rendered. `keymap.ts:38` sends zoom from any view and `receipt.ts:106` prints it. Sonnet also misses the zod errors that escape as 500s and the unmapped bucket's rendering on 3 surfaces. |

**Counts:** 9 lanes: 1 parity, 2 near parity, 6 losses. Sonnet made 2 false factual claims; Opus made 0 that I found. Opus's "only file over 500" misses 3 test files, but its point about the shipped script holds.

## Sonnet 5.5 at `high`
- **Arm:** the 6 lanes Sonnet lost at `medium` ran once more on Sonnet 5.5 at `high`, on the same invocations and trees. The session did not load new agent files mid-run, so each ran headless: `claude -p --agent <copy> --model sonnet --effort high`. The copies were the 0.17.3 agent files with `model`/`effort` changed and `${CLAUDE_PLUGIN_ROOT}` made absolute.
- **Confound:** these ran as a main session, not a subagent. The user's CLAUDE.md and output style were loaded, and every reply carried a `[hh:mm:ss]` prefix, which I stripped. Token counts from the two harnesses aren't comparable, so this table reports tool calls and time only.

| Lane | Opus tools / s | Sonnet `medium` tools / s | Sonnet `high` tools / s |
|---|---|---|---|
| dependency-auditor | 8 / 58 | 5 / 20 | 6 / 40 |
| accessibility-auditor | 8 / 94 | 5 / 33 | 10 / 88 |
| ux-reviewer | 10 / 201 | 4 / 41 | 11 / 106 |
| codebase-posture-auditor | 9 / 54 | 4 / 16 | 7 / 36 |
| prompt-posture-auditor | 28 / 321 | 12 / 49 | 13 / 67 |
| interface-posture-reviewer | 20 / 279 | 6 / 29 | 13 / 89 |
| **Total** | **83 / 1,007** | **36 / 188** | **60 / 426** |

At `high`, Sonnet made 72% of Opus's tool calls in 42% of its summed time. Run in parallel, the slowest lane took 106s against 321s. The API-equivalent cost of the 6 runs was $1.89.

| Lane | Opus / Sonnet `high` findings (critical + important) | Verdict | Evidence |
|---|---|---|---|
| dependency-auditor | 2 (0) / 3 (1) | **parity** | Both carry the deprecated `prebuild-install` and the stale ^11 major; Sonnet rates the first `important`. Its license statement is now accurate: better-sqlite3 is MIT, and the project license is TBD. |
| ux-reviewer | 14 (7) / 13 (7) | **parity** | Sonnet carries approve-without-claims, the badge bypass, high risk shown as medium, and the Vocabulary relabel. It misses claim-status labels reused on import edges and the unclickable island. It adds the unmapped bucket losing its attention treatment. |
| codebase-posture-auditor | 3 (0) / 4 (0) | **near parity** | Sonnet carries the floating `ci.yml` tags and the correct 717-line `report.py`, but miscounts the tag uses as 4 (there are 6). It misses the private `_cell_tokens` import. It adds that the Python 3.9 floor is past EOL, and the `pyproject.toml` version drift that Opus noticed but didn't raise. |
| accessibility-auditor | 10 (7) / 7 (6) | **Sonnet loses** | Sonnet now carries the tooltip-only claim text. It still misses both focus-loss findings: the chip click (`FlowView.tsx:311`) and the view switch (`App.tsx:540`). |
| prompt-posture-auditor | 8 (2) / 5 (0) | **Sonnet loses** | Sonnet still misses both confirmed important findings (the signal-list gap and the observed-anchor conflict) and files nothing above `track`. Its "eleven lanes" vs 14 claim is probably not a defect: the charter says eleven lanes "whose standards read code". |
| interface-posture-reviewer | 17 (11) / 10 (6) | **Sonnet loses** | Sonnet still misses the critical zoom-receipt defect. It also misses the unmapped bucket shown 3 ways, the claim labels on edges, and approve-without-claims. It now carries the zod-500 and duplicated-guard findings. |

## Replication on a larger artifact
- **Artifact:** the 6 parity candidates reran on winnow `7bd9ba7..9120a04`: 62 commits, 128 files, +8,935/-995, touching CI, 3 manifests plus the lockfile, 13 tsx/css files and 9 docs. Codebase-posture judged winnow at `9120a04`, about 13k lines across 4 packages.
- **Arms:** infra, frontend and doc ran on Opus and on Sonnet `medium`, all as subagents. Dependency, ux and codebase-posture ran on Opus and on Sonnet `high`. Sonnet `high` ran twice, once headless and once as a subagent: this session loaded the temporary agents only after the headless batch had started. The subagent run shares Opus's harness.

| Lane | Opus | Sonnet (subagent) | Sonnet (headless) | Verdict | Evidence |
|---|---|---|---|---|---|
| infra-auditor (`medium`) | 2 (2) | 2 (0) | — | **parity** | The same 2 findings, missing `permissions` and a floating tag. Opus rates both `important`, Sonnet `track`. |
| frontend-reviewer (`medium`) | 7 (4) | 6 (2) | — | **Sonnet loses** | Both carry the swallowed `/diff` failure, the oversized App component and the stale keydown deps. Sonnet misses a confirmed `important` defect: `handleIngest` selects `concerns[0]` of an `ingesting` snapshot the daemon creates with `concerns: []` (`App.tsx:202`, `server.ts:189`), so nothing is selected and the concern list has no Tab stop. |
| doc-auditor (`medium`) | 5 (1) | 4 (2) | — | **Sonnet loses** | Sonnet misses the confirmed `important` spec drift: §3 of `winnow-poc-design.md` still lists `unmappedHunkRefs` and `filePath?`, which `cartographer-output.ts` now says are deliberately absent. It also misses 3 `track` gaps in the REST table, DESIGN.md and PRODUCT.md. It adds a confirmed README layout omission (`packages/eval`), and reports that its own grep failed. |
| dependency-auditor (`high`) | 2 (1) | 1 (0) | 3 (1) | **near parity** | Every run carries the deprecated `prebuild-install`. The subagent run drops the install-script allowlist and rates the main finding `track`. Opus ran osv.dev over all 40 added packages; Sonnet covered 17 and 22. |
| ux-reviewer (`high`) | 7 (3) | 14 (5) | 10 (3) | **Sonnet at parity or better** | Both Sonnet runs carry all 3 of Opus's `important` findings (the banner stack covering headings, the remand error behind the backdrop, the reused status colors). The subagent run adds 2 confirmed extras: approve and remand have no clickable control, and `HunkDiff.tsx` uses the light-only `defaultHighlightStyle` under a dark palette. |
| codebase-posture-auditor (`high`) | 6 (5) | 7 (3) | 5 (2) | **Sonnet loses** | Neither Sonnet run finds the UI diff parser that skips the C-quoted path decoding the daemon's parser does (`ui/src/diff.ts` uses `stripPrefix`, daemon uses `extractPath`), or the stale context docs. Neither runs `pnpm audit`, so both miss the 8 high advisories Opus reports through the locked `fastify@5.10.0`. The lock is confirmed; I didn't re-run the audit. |

Run-to-run spread is large. Sonnet `high` filed 1 vs 3 dependency findings and 14 vs 10 ux findings across its two runs on the same input.

## Conclusion
Across both artifacts, 2 lanes held parity every time:
- **infra-auditor** at Sonnet `medium`: the same findings on both artifacts, in about half the time. Sonnet under-tiers them against Opus.
- **ux-reviewer** at Sonnet `high`: parity on the small artifact, and parity or better on the large one in both harnesses.

The other 4 split:
- **dependency-auditor** at `high` loses nothing checkable, but covers roughly half the packages Opus does. A supply-chain lane is judged by its sweep, so it stays on Opus.
- **frontend-reviewer** and **doc-auditor** at `medium` reached near parity on the small artifact. On the large one each missed 1 confirmed `important` defect that needed a claim traced across files.
- **codebase-posture-auditor** at `high` reached near parity on gauntlet, but on winnow it missed a real parser defect and never ran the lockfile audit.

Effort explains part of the gap and scale the rest. Sonnet 5.5 holds on lanes that check a surface: CI config, visual and interaction patterns. It falls behind where a finding means following one value across two packages, or running a tool it wasn't told to run.

## Incidental findings on gauntlet itself
All confirmed at `4448859`:
- `dispatch.py:61`: prompt-auditor signals miss `prompt_templates/` and `*.prompt`, so the lane is silently dropped for those paths.
- `agents/frontend-reviewer.md:34,98` (and interface-posture): the critical anchor demands an observed result the posture forbids.
- `commands/review.md:119,132,148`: `--context` is hardcoded to all three files, against the prose rule that follows it.
- `.github/workflows/ci.yml`: 6 action refs float, against `release.yml:21`.
- `scripts/dispatch.py`: imports the private `_cell_tokens` at 3 sites.
