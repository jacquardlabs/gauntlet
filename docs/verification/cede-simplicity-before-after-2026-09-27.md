# Cede simplicity to exorcist — before/after on PR #94

## Method
- **Changeset:** jacquardlabs/gauntlet PR #94 (issue #88), base `b958b78`, head `c9e7f06`, 2 commits, +839/-14 across 16 files. Worktree: detached at `c9e7f06`.
- **Before:** three gauntlet judges ran on the acceptance mount with the pre-#95 prompts: code-auditor, architecture-auditor 0.15.2 and product-reviewer 0.15.2. Each ran once.
- **After:** exorcist v0.8.0 `exorcise` ran once, audit only, with its intent taken from the PR body (11 claims). All four lanes reported (trace, abstraction, threshold, deletion). It traced all 34 hunks to a claim, all 6 checks passed, and it applied no edits.
- **Matching:** I read the code and diff at head and issue #88 for every selected finding. I didn't match on wording.

## Selection
The judges filed 13 findings. 2 fall under removed checks. The other 11 are in kept dimensions:
- code-auditor: `logic` ×3, `complexity` ×1. None is `maintainability`.
- architecture-auditor: `coupling`, `pattern-fit`.
- product-reviewer: `delivers`, `missing`, `error-states`, `journeys`, `language`.

## Results

| Finding | Removed check | Verdict | Evidence |
|---|---|---|---|
| arch `simplicity` (track/low): the 5-to-8 item bound is stated in both `schema.GENERATED_ITEMS` and the lenses merge prompt | arch `simplicity` (the dimension). The finding fits none of Reuse, Altitude or Scaffold | **LOST** | Both copies exist at head: `scripts/schema.py:386` `GENERATED_ITEMS = (5, 8)` and `reference/premortem-lenses.md:72` "between five and eight items". The defect is real but minor: two copies that can drift apart, and the fix is a consistency test, not less code. The exorcise report has no counterpart. Its abstraction §3 looks for parallel helpers in code, not a constant repeated in prose, so exorcist isn't built to catch this. |
| product `spec-fidelity` (important/high): the PR rewrites PRODUCT.md's authoring non-goal to admit the producer it ships | product `spec-fidelity`: code nothing asked for | **LOST** | Issue #88's Goal and Done means never mention PRODUCT.md. The diff edits the non-goal at `PRODUCT.md:19-20` in commit c9e7f06. exorcise took its intent from the PR body, whose claim 5 names this edit, so trace counted the hunk as covered ("every hunk traced to a claim") and flagged nothing. This is a structural gap: intent-tracer can't flag scope that the PR body itself declares. |

**Net-new from exorcise (no BEFORE counterpart):**

| exorcise finding | Lane | Note |
|---|---|---|
| `_verdict_line` helper has 1 caller, so inline it (`scripts/report.py:388` into `:488`) | abstraction §1 | Confirmed at head: the one-line f-string join is called only from `render_markdown`. Low value. |

**Counts:** 2 selected: 0 carried, 2 lost, 0 not-a-defect. 1 net-new from exorcise. 11 out of scope.

## Conclusion
On PR #94, #89's done-means ("no lost finding that exorcise's report doesn't carry") is **not met**. Exorcise ran cleanly and carries neither removed-check finding.

The two losses don't weigh the same.
- **The architecture finding** was mis-shelved under `simplicity`. It is about knowledge duplicated across artifacts, and none of the removed shapes covers it. It could go under `coupling` or be dropped as `track`, so losing it costs little.
- **The product finding** is the real gap. It is `important`, and it names a scope change the issue never asked for. The PR body introduced that change and also claimed it. exorcise's intent-tracer reads intent from the PR, so it certifies whatever the PR says it does. Nothing downstream checks the PR's claims against the issue.

Before #95 ceded "code nothing asked for", that half needed one of two changes, since as run it has no owner:
- keep an issue-versus-PR scope check in product-reviewer (for example, fold it into `missing`'s sibling or make it a kept `spec-fidelity` half), or
- run exorcise with the issue as its intent source.

This is n=1: one changeset, one run per side.
## Second run: issue #88 as intent

**Result: #89's done-means is not met.** Both findings the removed checks used to catch are still lost when exorcise takes issue #88 as its intent.

**Method:** I read `exorcise-94-issue.json` (intent = issue #88's 7 claims, scope `b958b78..c9e7f06`, 34 hunks, report-only). I checked each lost finding against the diff in `m94` and against the first run's `exorcise-94.json` (intent = PR #94 body).

| Finding (removed check) | Where it lives | Run 1 (PR #94 body) | Run 2 (issue #88) | Why |
|---|---|---|---|---|
| arch `simplicity` (track): the 5-to-8 bound is stated twice | `scripts/schema.py:386` `GENERATED_ITEMS = (5, 8)`; `reference/premortem-lenses.md:72` "between five and eight items" | LOST | **LOST** | No applied or held entry names either location. A value repeated across code and prose isn't a pattern any of the four lanes (trace, abstraction, threshold, deletion) looks for, so a different intent can't bring it back. |
| product `spec-fidelity` (important): the PRODUCT.md non-goal was rewritten without being asked for | `PRODUCT.md:19-20` (+2/-1 in the diff) | LOST | **LOST** | PRODUCT.md is in the diff. No claim covers it, yet `out_of_intent_files` lists only `commands/review.md`, and trace raised no revert or hold on it. Even with the issue as intent, trace let the edit through. |

Findings that are new compared with run 1 (run 1's only finding was the abstraction inline of `_verdict_line`, which run 2 also has):

| Lane | Action | Location | Finding |
|---|---|---|---|
| trace | revert | `commands/review.md:165-168` | A pre-dispatch register lint that no claim asks for. `commands/review.md` is flagged out of intent. |
| trace | hold (unmet claim) | claim 1 | `--premortem` on an issue body has no route: §0 reads a bare number as a PR, and §1/§6 take only a committed file path. |

**Counts:** 2 lost findings checked: 0 carried, 2 lost. 2 new findings (1 revert, 1 held unmet claim). 1 finding shared with run 1 (inline `_verdict_line`).

Running exorcise on the issue does make the trace lane sharper than running it on the PR body. It caught an out-of-intent hunk in `commands/review.md` and an unmet claim, and run 1 found neither. But #89's second done-means item says a before/after run must show "no lost finding that exorcise's report doesn't carry", and two findings are still lost:

- **The simplicity finding:** This is outside exorcist's lanes by construction, so no choice of intent will recover it. Either `architecture-auditor` keeps a narrow "one value, one source" check, or exorcist gets a lane for it (for example under jacquardlabs/exorcist#11).
- **The spec-fidelity finding:** trace passed over an unrequested edit to PRODUCT.md even with the issue as intent. That is a gap in how trace decides what is out of intent, and it needs fixing in exorcist before product-reviewer's spec-fidelity half can go.

Until one of those happens, #95 should not claim #89's done-means is met.

The run itself completed. Report JSON kept out of tree.