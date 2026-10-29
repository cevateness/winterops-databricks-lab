# V2 — bounded integration scope and execution record

**Revised scope explicitly approved and completed: PASS.** The initial approved attempt stopped at the large-upload deadline before SQL. After separate explicit approval of PR #7's gzip scope, the replacement uploaded and all 38 integration statements passed; together with seven readiness statements, the count is 45. Both artifacts/input guards passed before DDL. The three development names now exist and are not fresh CREATE targets. See [actual native evidence](DATA_FOUNDATION_V2_NATIVE.md). The original and revised scopes below are retained for audit, not as authorization to rerun them. No compute, Volume, job or schedule creation occurred.

## Exact proposed write scope

Only these new managed Delta development tables:

1. `workspace.default.winterops_v2_dev_bronze`
2. `workspace.default.winterops_v2_dev_silver`
3. `workspace.default.winterops_v2_dev_manifest`

The initial DDL must be the fail-if-exists CREATE statements from `DevelopmentTargets.creation_sql()`. Inspect schema/target metadata and stop on any existing-name conflict, unexpected owner/type/schema or inability to confirm the workspace/warehouse. Do not use CREATE OR REPLACE or IF NOT EXISTS to adopt an unknown object. Record newly created object identities privately before writing data. An incomplete three-table creation is non-atomic and must be reported without automatic DROP/replacement.

Upload exactly the two prepared private NDJSON exports into **new immutable paths** under the existing Volume prefix `/Volumes/workspace/default/winterops_raw/foundation_v2_dev/`, with each source-version ID and artifact hash in its path. Expected files are listed below. No original CSV, old Volume path or unrelated artifact may be changed. If a target upload path already exists, compare exact bytes/hash and skip only if identical; never overwrite differing content.

| Source CSV | Source-file SHA-256 | NDJSON artifact SHA-256 | NDJSON bytes | Parsed rows |
|---|---|---|---:|---:|
| Jan 5–11 | `271c9339a42043f441b6c17e82dd309609db4b20e9953b9f368a95ec472d763d` | `375d6c5980ed66f61b2dcb0601f639f5e2a3a20ce546ac08d3e20fc60c17edd3` | 3,619,379 | 2,810 |
| Jan 19–25 | `b78d0fb82c8e3c5204ee79eea7a03417cd54bc935ead9b04577a30dc908c7c49` | `94b6464999a58757ea6977cdc3d8b6e402b19edac2b9843369e7c1a18738c172` | 152,492,496 | 118,159 |

The source bytes are independently hashed during local parsing/export. The runtime artifact guard verifies uploaded NDJSON bytes; it does not claim to rehash an original CSV in the workspace. NDJSON contains private record data and original local provenance paths; keep it inside the authenticated workspace. Never paste it into public logs or reports.

## One approved execution matrix, if approved later

Use the SQL-warehouse route rendered by `sql_version_plan`, with exactly the Silver SQL tested offline and `manifest_status_sql` for one processing key at a time. Read manifest plus complete persisted contents before deciding whether any write is necessary. Source version IDs, processing keys and default policy SHA-256 are pinned in [the source report](DATA_FOUNDATION_V2_SOURCE_REPORT.json).

1. **Preflight:** revalidate named profile, expected workspace/warehouse configuration, protected original objects and absence of development-name conflicts. Record sanitized original one-week aggregate baselines with the existing source/published-view guards. Create the three dev tables only after metadata/ownership conflict checks.
2. **First week / interrupted-stage recovery:** verify artifact bytes/schema/source scope and record ordinals, write manifest PROCESSING and only January 5–11 Bronze, then record BRONZE_WRITTEN. Deliberately end that processing stage before Silver; this is a planned checkpoint, not an error/retry. Inspect committed content and resume the same approved matrix with a new manifest attempt. Verify Bronze equality and skip its rewrite, derive/write scoped Silver, reconcile complete row multisets, and mark COMPLETE.
3. **Unchanged first-week rerun:** verify full Bronze/Silver equality and COMPLETE metadata; require SKIP with no data or manifest DML. Record the row multiset and sanitized summary for preservation checks.
4. **Append January 19–25:** artifact/input guards, new processing key, scoped Bronze write, scoped Silver write, per-stage manifest updates and full-content postflight. Require 118,159 rows = 34 HEADER + 118,125 VALID + 0 other INVALID. The first week must retain 2,810 rows = 19 HEADER + 2,791 VALID + 0 other INVALID and identical complete contents.
5. **Final read-only checks:** verify unchanged-second-week skip, complete manifests, separate per-version reconciliation and safe quality summaries; rerun original protected source/published-view guards and compare the original one-week aggregates. Do not point existing Gold/views at development data.

Source revision and changed-policy behavior, malformed records and failure recovery have synthetic offline tests. The first native scope above validates the two real exact versions, reruns, append and planned partial-stage recovery. It does not inject corrupt telemetry, mutate official bytes or claim native revision/corruption fault-injection coverage. Such cases can be included only in an explicitly revised concrete approval scope.

## Hard bounds and stop rules

- **At most 45 SQL statements total**, including three CREATE operations, exact-scope DML/manifest updates and all read-only checks; at most **10 minutes** for the SQL phase. Precheck the planned statement budget before any submission.
- Sequential requests only; `wait_timeout=30s`, `on_wait_timeout=CANCEL`, hard **45-second client deadline**, inline JSON responses capped at **200 aggregate rows / 65,536 bytes**. No automatic retries, result-chunk retrieval or polling loops. Metadata requests use a 15-second client bound. Upload at most the two listed files, approximately 149 MiB total; cap each upload at 256 MiB / 180 seconds.
- Stop the matrix on any error, timeout, cancellation, source/artifact mismatch, truncation, permission issue, unexpected count/type/owner/result, or mutation of a protected baseline. Record the last committed stage and sanitized status. Do not continue data writes to compensate for a failure. Any permitted failure audit update must target only its exact development-manifest key; if that fails, retain the private client report and stop.
- Planned checkpoint recovery in step 2 is already part of this proposed matrix. An **unexpected** partial failure does not authorize an automatic resume or destructive rollback. Read-only inspection can establish what committed; renewed approval is required for further writes outside the completed matrix.
- No DROP, TRUNCATE, VACUUM, RESTORE, replacement of existing objects, source deletion, permission/owner change, warehouse setting change, job, schedule or Spark/notebook submission is included. Only native shared SQL/Delta behavior is exercised; the optional PySpark adapter itself remains unexecuted.

Record statement hashes/statuses/timings, row/quality totals and whether reruns wrote nothing. Keep statement/object/warehouse IDs, local paths, credentials, raw identifiers, coordinates and record payloads private. Final evidence must separate this native dev-table result from the local SQLite/Python run and from the existing validated one-week Gold pipeline.

## Revised upload recovery — APPROVED AND EXECUTED

Reuse the January 5–11 artifact at its original exact path after a fresh HEAD check and native fingerprint/input guards; do not upload it again. Upload **one** January 19–25 replacement, without overwrite, to:

```text
/Volumes/workspace/default/winterops_raw/foundation_v2_dev/d2a89e9a8582aefdca97264a482d51a6116b827a71f0241a0e1f0149ed14f97a/5516fe43d00a609c858f71323b7c4fa7c856ca7c3b8c69137e6e67ac5b99034c/bronze.jsonl.gz
```

Compressed size: **9,920,290 bytes**; SHA-256 `5516fe43d00a609c858f71323b7c4fa7c856ca7c3b8c69137e6e67ac5b99034c`. Decoded SHA-256 remains `94b6464999a58757ea6977cdc3d8b6e402b19edac2b9843369e7c1a18738c172` (152,492,496 bytes / 118,159 records). Source CSV SHA-256 remains `b78d0fb82c8e3c5204ee79eea7a03417cd54bc935ead9b04577a30dc908c7c49`. Only the new parent directories may be created; the old failed destination is not a cleanup/overwrite target.

Keep the same three fail-if-exists table targets, source versions, quality policy and planned checkpoint/recovery/rerun matrix. Move **both artifact guards and both input guards before all DDL**, so gzip/real-file compatibility is checked before table creation. The executed plan was pinned at SHA-256 `97c0018f94f62555de1680eb243381db41d50e8118ba7bfbc4be249335d25879` from commit `c1d8de3`.

The revised integration contains 38 SQL statements; together with seven successful readiness statements and zero SQL from the stopped attempt, the combined count remains 45. Reserve 564 seconds for integration SQL within the cumulative 600-second active SQL budget. Preserve 30-second wait/CANCEL, hard 45-second requests, 200-row/65,536-byte results, 256 MiB/180-second uploads and no automatic retries. Approval wait is outside active execution time.

The user explicitly approved this revised scope before execution. It completed once: one gzip upload in 23.959 seconds, 38 SQL statements in 130.391 seconds, and final protected-object/data/grant/configuration checks passed. This record does not authorize a rerun. All three development tables now exist; do not replay fail-if-exists DDL or overwrite artifacts. Any later write/recovery/promotion needs a new concrete scope. No cleanup, rollback, replacement or warehouse/grant/job change occurred.
