# gauntlet findings contract

**Contract version: 1**

This document is for a **consumer** that dispatches a gauntlet judge and reads its
findings — a viva type bundle, a Claude Code command, a CI job — and for a **judge**
that emits them. It pins the two payloads that cross the boundary: the invocation a
consumer hands a judge, and the findings document the judge returns. Transport is out
of scope: whether the judge runs as a Task-tool subagent, a workflow `agent()` call,
or a bare prompt, the payloads are the contract.

Consolidates and supersedes, at fleet migration: studious `reference/severity-rubric.md`
(tiers, anchors), `reference/evidence-format.md` (receipts), and the output-row schema
of `reference/prompt-contract.md` §3. Posture, calibration, and style (prompt-contract
§1–2, §4–5) remain fleet-internal and are **not** part of this contract — a consumer
cannot observe them, only the payloads.

## 1. Contract version

A single integer, following viva's `docs/headless-contract.md` precedent. Bumps when
the surface below changes in a way that could break an existing caller: a required
field added, removed, renamed, or retyped; an enum value removed; a rule below
reversed. **Not** a bump: adding an optional field, adding an enum value, prose
clarification.

Negotiation is exact match in v1: every payload carries `contract_version`, and a
consumer rejects a findings document whose version it does not speak. No ranges, no
minimums, until a real second version exists to negotiate with.

| version | date | change |
|---|---|---|
| 1 | 2026-08-04 | Initial contract. Ratified via viva review — 2 rounds, 9/9 sections approved. |

## 2. Vocabulary

- **judge** — one registered reviewer with one lane (security, tests, product, …).
  Registered in the charter (`reference/charter.md`, issue #3); this contract refers
  to judges by registered name and does not pin the charter's format.
- **consumer** — whoever dispatches a judge and ingests its findings document.
- **artifact** — what is judged: a changeset, a document, or a repository.
- **standard** — what it is judged against: a named checklist, rubric, or template
  grammar.
- **mount** — which question the judge is being asked: `intake` (pre-commitment,
  judging a proposal — brief, design doc, plan), `acceptance` (post-production, judging
  what was produced — changeset, packet, rendered flows), or `posture` (standing,
  judging the current state of a whole repository).

  A mount names the **question**, never the schedule. A standing review is often run on
  a cadence, but cadence is a consumer's business: two consumers running `posture`
  weekly and quarterly ask the identical question, and a judge cannot tell them apart.
  Naming this mount after its usual trigger would have put a calendar in a payload.
- **receipt** — a harness-captured evidence record a finding may cite. Captured by
  the harness, never written by a judge or producer: capturer ≠ claimant stays
  checkable.

## 3. Invocation payload

What a consumer hands a judge, as JSON embedded in the dispatch:

| Field | Required | Notes |
|---|---|---|
| `contract_version` | yes | Integer, `1`. |
| `judge` | yes | Registered judge name. |
| `mount` | yes | `intake`, `acceptance`, or `posture`. Must be a mount the judge's charter entry declares; a consumer never requests an undeclared mount. |
| `artifact` | yes | Object, see below. |
| `standard` | yes | `{name, version?}` — the rubric or template grammar this run judges against. |
| `context` | no | Paths the judge reads for project grounding (PRODUCT.md, DESIGN.md, CLAUDE.md). |
| `receipts_path` | no | Path to the evidence log (§7) this run may cite. Absent means no receipts are citable — findings then cannot carry `receipts`. |

**`artifact`** is one of three kinds:

| Kind | Shape | Notes |
|---|---|---|
| `changeset` | `{kind: "changeset", base, head, root?, pr?}` | Git shas; `root` defaults to the working directory. `pr` is the pull-request URL when the changeset is a PR — the consumer resolves the PR to `base`/`head` at dispatch and carries the URL through, so the findings document is addressable back to the PR without the invocation in hand. |
| `document` | `{kind: "document", path}` | Markdown file. Trade-study matrices are documents; the matrix locus lives on the finding (§4). |
| `repository` | `{kind: "repository", ref, root?}` | A whole repository at one point in time — the artifact a `posture` review judges. `ref` is the sha or ref judged, required so a standing finding is reproducible against the state that produced it; `root` defaults to the working directory. There is deliberately no `base`: a posture review compares the repository to a standard, never to an earlier revision of itself. |

A PR is not an artifact kind of its own: judges see every PR as an ordinary changeset.
Posting findings back as PR review comments is a **consumer** feature (issue #7), and
the shapes here are deliberately sufficient for it — `locus.path`/`locus.line` against
`artifact.head` is exactly the addressing a PR review comment needs, and `tier`/
`summary`/`recommendation` are the comment body.

## 4. Findings document

What a judge returns. Top level:

| Field | Required | Notes |
|---|---|---|
| `contract_version` | yes | Integer, `1`. |
| `judge` | yes | Echoes the invocation. |
| `mount` | yes | Echoes the invocation. |
| `artifact` | yes | Echoes the invocation — a findings document is self-describing without the invocation in hand. |
| `standard` | yes | Echoes the invocation. |
| `findings` | yes | List, **may be empty** — a clean result is a valid, complete result. |
| `coverage` | yes | 2–3 sentences: what was verified clean, assumptions made, limitations hit. Required precisely so an empty `findings` list is distinguishable from a shallow run. |

**There is no verdict field, deliberately.** Judges emit findings; consumers derive
verdicts from open findings (all criticals resolved → passable). A verdict is a
judgment about disposition, and disposition belongs to the human's side of the flow —
derived closure, never picked (ruled on viva#165).

Each entry in `findings`:

| Field | Required | Notes |
|---|---|---|
| `dimension` | yes | The judge's own sub-check that produced it (its enum, not this contract's). |
| `tier` | yes | `critical` \| `important` \| `track` — canonical at emit. Judges emit these three directly; the per-judge label→tier mapping table dies at migration. |
| `summary` | yes | The claim, ≤15 words. |
| `locus` | yes | Object with at least one of `path` (+ optional `line`), `section`, or `cell`. Code findings use `path`/`line`; document findings use `section`; matrix findings add `cell`. |
| `anchor` | when `tier: critical` | The objective anchor the judge's lane owns (severity-rubric's table travels into the charter): the checkable fact, not the judge's feeling. **Anchor-or-demote:** a consumer records an anchorless critical as `important` — enforced at ingest, named in the compiled report. On a `document` artifact the anchor must also contain a verbatim quote from the artifact, in double quotation marks; ingest matches it against the document text, whitespace-normalized on both sides, and records a miss as `important` beside the presence rule (#44). A document the consumer cannot read skips the quote check. |
| `basis` | yes | `sourced` \| `inferred` \| `taste` — grounds classing, aligned with viva's `Annotation.basis` and extended per viva#175. `sourced` cites a receipt or an anchor a reader can check; `inferred` is reasoned from the artifact without a direct citation; `taste` is labeled preference. **A `taste` finding never ranks above `track`.** Replaces the old Confirmed/Potential vocabulary — one confidence grammar across gauntlet and viva, never numeric. |
| `level` | no | `high` \| `medium` \| `low` — strength within the basis, viva's `Annotation.level`. |
| `failure_scenario` | no | Concrete inputs/state → wrong outcome. Expected on `critical` and `important` code findings. |
| `recommendation` | no | The action to take, imperative, **25 words or fewer**. Advisory, never a patch — judges do not produce. Why it matters belongs in `failure_scenario`: a recommendation that argues for itself is two fields in one, and the argument is what makes it unreadable in a PR margin. |
| `receipts` | no | List of `outputDigest` strings citing records in the evidence log (§7). Only valid when the invocation carried `receipts_path`. |

Compact example:

```json
{
  "contract_version": 1,
  "judge": "security-auditor",
  "mount": "acceptance",
  "artifact": {"kind": "changeset", "base": "a1b2c3d", "head": "e4f5a6b"},
  "standard": {"name": "security-checklist", "version": "2026-07"},
  "findings": [
    {
      "dimension": "injection",
      "tier": "critical",
      "summary": "Unsanitized branch name reaches shell in release script",
      "locus": {"path": "scripts/release.sh", "line": 42},
      "anchor": "Command injection (security-checklist): $BRANCH interpolated into eval at scripts/release.sh:42, reachable from PR title",
      "basis": "sourced",
      "level": "high",
      "failure_scenario": "PR titled `x; rm -rf .` becomes the branch slug; release run executes it",
      "recommendation": "Quote the variable and validate the slug against ^[a-z0-9-]+$ at entry",
      "receipts": ["sha256:9f2c..."]
    }
  ],
  "coverage": "Reviewed both modified scripts and the workflow file. Auth and secrets surfaces unchanged; did not execute the target. No receipts existed for the lint run cited in the PR body."
}
```

## 5. Tier ladder

Three tiers, never a fourth:

- **critical** — blocks the stamp. Requires an anchor (§4).
- **important** — should fix this cycle.
- **track** — log and revisit; the only tier a `taste` finding may hold.

## 6. Receipts

The evidence log is a JSONL file of harness-captured verification records, one compact
object per line, append-only. Shape carried over from studious
`reference/evidence-format.md` (itself winnow Amendment 006's early footprint):

| Field | Notes |
|---|---|
| `capturedAt` | UTC `%Y-%m-%dT%H:%M:%SZ`, written by the capturer. |
| `capturer` | Who captured — `"hook"` today. Never caller-supplied: the field that keeps capturer ≠ claimant checkable. |
| `origin` | `"subagent"` or `"interactive"`. |
| `agentType` | Present only on subagent-origin records. |
| `command` | The verification command, verbatim. |
| `exitCode` | `0` on success; best-effort on failure paths. |
| `outputDigest` | `sha256:<hex>` of the output — a digest, never raw output. **The citation key**: `findings[].receipts` entries are these values. |
| `predicateType` | `https://in-toto.io/attestation/test-result/v0.1`. |
| `predicate` | `{result: PASSED\|FAILED, configuration: [{name: <command>}]}`. |

A judge reads receipts; it never writes them. A finding claiming "tests pass" without
a citable receipt is `basis: inferred`, not `sourced`.

## 7. Validation

Mirrors viva's boundary pattern (`scripts/schema.py`): a stdlib-only Python module,
`validate_invocation()` and `validate_findings()`, called where payloads cross the
boundary — by the consumer on dispatch and on ingest. TypedDicts document the shapes;
the validators carry the enforced rules; tests pin both. No JSON Schema dependency —
one validation idiom across the portfolio, and the module doubles as the reference
implementation of anchor-or-demote and the taste-tier rule.

## Out of scope

- **Telemetry** — routing/dispatch records are a consumer's private concern, not part
  of this contract.
- **Transport and orchestration** — how judges get dispatched, retried, or paralleled.
- **The charter's format** — issue #3; this contract only requires that registered
  names and declared mounts exist.
- **Prompt posture** — injection defense, read-only discipline, calibration, style
  stay fleet-internal (prompt-contract §1–2, §4–5 travel with the fleet at migration,
  unobserved by consumers).
