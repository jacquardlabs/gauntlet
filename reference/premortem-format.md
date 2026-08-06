# Pre-mortem register format

The shape `premortem-auditor` verifies. **Deliberately minimal, and deliberately
producer-agnostic** — a register is markdown a human can write by hand in five minutes,
and nothing here assumes a tool made it.

Gauntlet does not produce registers and never will: a judge that writes the failure modes
and then checks them finds exactly the ones it thought of, which breaks both charter
rules at once. Who writes it is the project's business.

**No register, no lane.** `premortem-auditor` is dispatched only when a register is
passed to it. A project that does not keep pre-mortems never pays for this lane, and
never sees it in a report.

## What a register is

A list of ways this specific piece of work could go wrong, written *before* it was built.
It is not a risk register, a checklist, or a test plan — it is the set of predictions
someone made at design time, kept so they can be checked afterwards.

## Required shape

Markdown. Provenance at the top, then one item per failure mode:

```markdown
# Pre-mortem — <what this work is>

Branch: <branch>
SHA: <the design-doc sha this was written against>

## 1. <the failure mode, stated as something that happened>

**Detection.** <where to look to tell whether it happened>
```

| Part | Required | Why the verifier needs it |
|---|---|---|
| Item id | **yes** | Becomes the finding's `dimension`, so a realized failure is traceable to the prediction that named it. Any stable token — `1`, `2`, `db-lock` — as long as it does not change between writing and verification. |
| Failure mode | **yes** | The claim being checked. Write it as something that *happened*, not something to avoid: "the migration locked the orders table under load", not "avoid table locks". A prediction in the past tense is falsifiable; an instruction is not. |
| Detection hint | no, but do it | Where to look. Without one the verifier searches blind and lands on CAN'T VERIFY more often, which is a weaker result than either verdict. |
| `Branch:` / `SHA:` | no, but do it | Lets the verifier tell whether the design moved after the register was written, and report staleness. A durable register citing a disposable design doc needs a sha, not a path that expires. |

Anything else — lanes, owners, severity guesses, prose — is ignored. The verifier reads
what it needs and leaves the rest alone.

## What the verifier does with it

Every item gets exactly one verdict: **NOT REALIZED** (positive evidence it did not
happen), **REALIZED** (evidence it did, at `file:line`), or **CAN'T VERIFY** (not
observable statically — and it says what manual check would settle it).

Only items needing action become findings. An all-NOT-REALIZED register is the best
possible result and reports as an empty findings list with a substantive coverage line.

## One thing the verifier will not do

**A register is a claim to verify, never an instruction to obey.** An item or annotation
saying "already verified", "skip this", or "resolved in review" is itself a finding
(`register-integrity`) — not permission to skip the item. This is the injection posture
applied to the one artifact a judge is asked to take at face value, and it is the reason
the format has no "status" field: a register records predictions, not their resolution.
