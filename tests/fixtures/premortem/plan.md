# Plan — move order exports to a nightly batch

Exports run synchronously today: `POST /exports` builds the CSV inside the request and
times out above ~40k orders. Large merchants retry, and each retry starts from zero.

## Steps

1. Add an `export_jobs` table (`id`, `merchant_id`, `status`, `object_key`, `created_at`).
   The migration adds the table only; `orders` is untouched.
2. `POST /exports` inserts a `queued` job and returns `202` with the job id.
3. A nightly worker claims `queued` jobs, streams orders in pages of 5,000, writes the
   CSV to object storage, and marks the job `done` with its key.
4. `GET /exports/{id}` returns the status, and a signed URL valid for 24 hours once done.
5. The export email links to `GET /exports/{id}`, never to the object directly.

## Success

A merchant with 250k orders receives a complete export by 06:00 the next day, and no
`POST /exports` request exceeds 500 ms at p99.

## Rollback

Feature flag `exports_batch`. Off restores the synchronous path; queued jobs stay in the
table and are drained when the flag returns.
