# Pre-mortem — move order exports to a nightly batch

Branch: exports-nightly-batch
SHA: 3f9a2c1d7e4b

## 1. Merchants waited a full day for an export they used to get in a minute

The 202 made the small-merchant case, which never timed out, strictly slower: a
2,000-order export that returned inline now arrived the next morning. Support tickets
spiked the first week.

**Detection.** Whether `POST /exports` still serves small exports inline, or routes
every size through `export_jobs`; the handler's branch on order count, if any.

## 2. The worker paged orders by offset and skipped rows written mid-export

Pages of 5,000 by `OFFSET` shifted when new orders landed during the run, so an export
silently missed or duplicated orders at page boundaries.

**Detection.** The worker's order query: keyset pagination on a stable key, or `OFFSET`.

## 3. Two workers claimed the same job and wrote the file twice

The nightly worker ran on two hosts after a deploy overlapped a schedule, and the claim
was a read-then-update without a lock, so both exported the same job.

**Detection.** The claim statement — `UPDATE … WHERE status = 'queued' RETURNING`,
`SELECT … FOR UPDATE SKIP LOCKED`, or a plain `SELECT` followed by an `UPDATE`.

## 4. Signed URLs in forwarded emails exposed another merchant's orders

A merchant forwarded the export email; the link resolved to a signed URL anyone holding
it could open for 24 hours, with no check that the viewer belonged to the merchant.

**Detection.** Whether `GET /exports/{id}` checks the caller's merchant against
`export_jobs.merchant_id` before issuing the signed URL.

## 5. Turning the flag off stranded queued jobs with no one told

Rollback restored the synchronous path, but queued jobs sat untouched and their
merchants never received the export they had been promised.

**Detection.** What the flag-off path does with `queued` rows, and whether anything
notifies their merchants.

## 6. A failed nightly run left jobs queued forever with no alert

The worker crashed halfway through one merchant's export; the job stayed `queued`, the
next night hit the same crash, and nothing paged anyone.

**Detection.** A `failed` status or retry count on `export_jobs`, and an alarm on jobs
older than a day.
