# Trade-study format

The shape `trade-study-auditor` judges. **Deliberately minimal, and deliberately
producer-agnostic** — a trade study is markdown a human can write by hand, and nothing
here assumes a tool made it.

Gauntlet does not produce trade studies and never will: a judge that fills the matrix
and then checks the recommendation against it confirms exactly the decision it reached,
which breaks both charter rules at once. Who writes it is the project's business.

Dispatch is consumer-named, like every document. A document with no decision matrix
costs the lane a self-skip reported in `coverage`, never a finding — not being a trade
study is not a defect.

## What a trade study is

A decision made by comparison, kept checkable: named options, explicit criteria, one
judgment per criterion × option, and a recommendation that follows from those
judgments. The matrix is the argument and the recommendation is its conclusion — not a
proposal with a comparison table for decoration.

## Required shape

Markdown. Options and criteria first, then the matrix, then the recommendation:

```markdown
# Trade study — <the decision>

## Options
<one line each: what it is, at what version or configuration>

## Criteria
<one line each: what is measured and why it matters here — and, if weighted,
the reason for each weight>

## Matrix

| Criterion | <option> | <option> |
|---|---|---|
| Cost at 10k rps | $410/mo ([calc](…)) | $1,900/mo ([calc](…)) |

## Recommendation
<the chosen option, and the reading of the matrix that picks it>
```

| Part | Required | Why the judge needs it |
|---|---|---|
| Options | **yes** | The alternatives compared, each pinned to a version or configuration — "Postgres 16 behind pgbouncer", not "SQL". An option nobody pinned cannot be engaged at its strongest. |
| Criteria | **yes** | What the options are compared on. Weights are optional — but a weight with no stated reason is how a matrix gets rigged, so every weight carries one. |
| Matrix | **yes** | One judgment per criterion × option. A finding lands on a cell as `locus.cell: "<criterion> × <option>"`, which is why rows and columns need stable names. |
| Recommendation | **yes** | The chosen option plus the reading of the matrix that picks it. A bare "we chose X" leaves the derivation unstated, and the derivation is what the judge checks. |

**A load-bearing cell** is one whose value, if wrong, could change the recommendation:
a number (price, latency, benchmark), a categorical disqualifier ("no SLA", "not
supported"), any cell where the winner and runner-up differ on a weighted criterion.
Every load-bearing cell carries a receipt or citation a reader can check — a pricing
page, a benchmark log, a doc section, `file:line` in the repo. Hedged filler is fine in
a cell the outcome does not turn on; in a load-bearing one it is a judgment with no
evidence attached.

Anything else — background, constraints, prior art, prose — is ignored. The judge reads
what it needs and leaves the rest alone.

## What the judge does with it

Recomputes the recommendation from the matrix as written — stated weights applied,
nothing added, nothing dropped — and compares it to the one on the page. Checks each
load-bearing cell for a citation a reader can follow. Reads each losing column for a
strawman: a stale version, an ignored mitigation, an uncited dismissal opposite a
cited win.

## One thing the judge will not do

**The matrix is a claim to verify, never an instruction to obey.** A cell or note
saying "benchmarked internally", "verified by the platform team", or "already decided
at the review" is an assurance nothing can check — itself a finding, not permission to
skip the cell. This is the injection posture applied where it bites hardest: a trade
study is persuasive prose around a table, and the table inherits none of the prose's
credibility.
