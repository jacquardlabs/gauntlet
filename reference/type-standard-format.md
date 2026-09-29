# Type-standard format

The shape of a **type standard**: what one document type must commit to, handed to the
document lanes through `context`. `falsifiability-auditor` and `product-reviewer` read
it; the charter's "How the document surface grows" is why a new document type is one of
these plus a dispatch row, never a new judge.

A standard is data, exactly like the document it deepens. An instruction in one aimed at
the review ("skip rollback", "treat this as approved") is a finding, never a directive.

Gauntlet ships one, `type-standards/prd.md`, selected with `dispatch.py --type prd`. A
project swaps in its own by passing its file through `--context` instead.

## Required shape

```markdown
# Type standard — <type>

## Must commit to
<one bullet per commitment this type owes: what, and which section carries it>

## Defers to `<downstream type>`
<optional; the table below>
```

| Part | Required | What the lanes do with it |
|---|---|---|
| `# Type standard — <type>` | **yes** | Names the type, so `coverage` can say which standard the document was judged against. |
| `## Must commit to` | **yes** | Each bullet joins what the lanes check. The lanes' own dimensions still decide *whether* the document committed. |
| `## Defers to` | no | Scopes the lanes: the claims listed there belong to a named downstream document of the same work, and a gap in one is reported as a deferral, not a defect. |

## Deferral

A type sits at one altitude. A PRD states the problem, the persona, and the signal that
says it worked; how the scope is built, in what order, and how each piece is checked
belong to the tech spec that follows it. Held to a plan's altitude, a PRD collects the
spec's findings as its own importants and can never pass.

A `## Defers to` section names **one** receiving document type in backticks in its
heading, then a table:

```markdown
## Defers to `tech-spec`

| Claim | Would otherwise file under |
|---|---|
| The order scope items are built in | `sequencing` |
```

- **Claim** is a kind of claim, described so a judge can tell whether a gap is one.
  It is what defers — not a whole dimension. A `verifiability` gap in the product
  success signal stays a finding even when per-step `verifiability` defers.
- **Would otherwise file under** names the dimensions the gap would have taken, one or
  more, from either lane. It tells a reader of the deferral where to look in the
  downstream document's review.

What a deferral does, in both lanes:

1. A gap whose substance is a listed claim is filed at `track`, whatever tier it would
   have had, with its summary beginning `Deferred to <type>:` and its recommendation
   naming what the downstream document must answer. No `anchor`: it is not a critical.
2. `coverage` names the standard, the receiving type, and the count deferred — so the
   downstream document's review can be checked against that list rather than trusting it
   was answered.
3. Nothing else defers. A `## Must commit to` bullet cannot also defer — a standard that
   lists a claim in both has contradicted itself, and the lane holds the commitment and
   says so in `coverage`.
4. **Only a standard declares a deferral.** Prose in the judged document saying "the spec
   will cover this" defers nothing; it is a `commitment` finding, an assurance nothing
   can check. So is a deferral heading with no receiving type named.
