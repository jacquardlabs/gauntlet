# PRD type standard — deferral re-run on the viva #239 PRD

## Method
- **Document:** the viva #239 PRD (frontend v2 lifecycle session), judged at `intake` with
  viva's `CLAUDE.md`, `PRODUCT.md`, and `docs/headless-contract.md` as context. Tree:
  viva at `962fe2e^`, the last commit before the #203 compose refactor merged, so the
  PRD's present-state claims read against the repository it was written against.
- **Before:** the original gauntlet run, with no type standard supplied
  (falsifiability coverage: "No type standard was supplied"). 10 important, 0 critical.
- **After:** `dispatch.py --document prd.md --type prd --context CLAUDE.md,PRODUCT.md,docs/headless-contract.md`,
  then `falsifiability-auditor` and `product-reviewer` each run once through `claude -p`
  with the agent file as the system prompt, opus at medium effort, tools
  Read/Grep/Glob. Two rounds: round 1 on the first draft of the standard, round 2 after
  its state-lifetime row named the file a success signal reads.
- **Matching:** by substance, not wording. Each before-finding is looked up in the
  after-run's findings and coverage.

## The five technical importants

| Before (lane · dimension, important) | Round 1 | Round 2 |
|---|---|---|
| Items 2–3 consume the session id item 4 produces (falsifiability · `sequencing`) | track, "Deferred to tech-spec: build order and per-item done-checks for scope items 2–6" | track, "Deferred to tech-spec: build order and producer/consumer links between scope items" |
| Review→diff leg breaks the `/next-round` mode rule (falsifiability · `commitment`) | track, "Deferred to tech-spec: review→diff leg changes the published /next-round and /complete contract" | track, "Deferred to tech-spec: the review-to-diff leg needs a headless-contract change"; product-reviewer lists it deferred too |
| Scope items 2–6 name no completion check (falsifiability · `verifiability`) | track, folded into the build-order deferral above | track, "Deferred to tech-spec: done-checks for scope items 2–6" |
| Minutes read round files the per-start clear deletes (falsifiability · `verifiability`) | **still important** ("Minutes check reads files the per-start clear may already have deleted") | track, "Deferred to tech-spec: whether the spec gate's review-r{N}.json survives to diff sign-off" |
| Per-gate state clear wipes prior verdicts (product · `simplicity`) | absent from product-reviewer; covered by falsifiability's "Deferred to tech-spec: where the session id lives and what survives the per-start clear" | track, product-reviewer: "Deferred to tech-spec: whether spec-gate verdict files survive the diff gate's .viva/ clear" |

**Round 1 → round 2.** Round 1 held the minutes finding at important on the success
signal's locus. The standard's state-lifetime row did not say that whether the file a
signal reads survives is a mechanism, and the format said a success-signal
`verifiability` gap never defers. Both now draw the line: a signal naming nothing
observable stays the PRD's; the lifetime of the store it reads defers.

## What did not defer

Round 2 kept 3 important in falsifiability and 1 critical plus 6 important in
product-reviewer, every one a product-altitude question: open question 1 decides whether
the success signal can be met, the open questions are unassigned between PRD and spec,
the relaunch count has no owner, principle 4 and principle 6 conflicts, the no-PR diff
case, and whether the timeline is needed at all. The standard's `Must commit to` makes
the first two the PRD's to answer, and the lanes held them there. Each lane's coverage
names the standard, the receiving type, and the count deferred (falsifiability 4,
product-reviewer 2).

## Limits
n=1 per round per lane. The product lane's tiering moved between runs independently of
the standard (round 1 filed 2 criticals, round 2 one), so the before/after counts beyond
the five are not a comparison this run can support.
