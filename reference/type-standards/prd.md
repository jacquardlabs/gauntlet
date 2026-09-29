# Type standard — prd

A product requirements document: the product half of a feature, written before its
technical design. Its sections are the ones `product-reviewer` quotes. The shape is
`reference/type-standard-format.md`.

## Must commit to

- **A named persona and the job it is hired for** — Problem & persona.
- **The journey that changes**, step by step as the persona walks it — User journey.
- **A success signal**: an observable tied to the persona's job, and where it will be
  read — Success signal. "No measurable surface, because X" satisfies this; silence does
  not.
- **What is in scope and what is explicitly out** — Scope and out of scope.
- **The alternatives rejected, each with its reason** — Alternatives considered.
- **Which open questions change product behavior**, and which are left to the spec —
  Open questions. An open question that decides whether the success signal can be met
  is the PRD's to answer.

## Defers to `tech-spec`

| Claim | Would otherwise file under |
|---|---|
| The order scope items are built in, and which item produces what a later one consumes | `sequencing` |
| How each scope item is shown to be done — its test, endpoint response, or rendered state | `verifiability` |
| Changes to a published interface or contract the scope needs — an API, a protocol, a file format — and the version bump that carries them | `commitment` |
| Where state lives and how long it survives — storage, caches, what a restart or a new run clears | `verifiability`, `simplicity` |
