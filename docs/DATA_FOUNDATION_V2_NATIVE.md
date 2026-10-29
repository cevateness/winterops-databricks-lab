# V2 native integration — PASS (2026-10-29)

**The approved revised SQL-warehouse integration passed.** Both immutable source versions coexist in three isolated development tables; recovery, read-only rerun decisions, full-record reconciliation and preservation of the published one-week pipeline passed. This verifies shared SQL through the Statement Execution API, not the optional PySpark adapter or a notebook. See [per-statement sanitized evidence](DATA_FOUNDATION_V2_NATIVE_RESULTS.json) and [executed scope](DATA_FOUNDATION_V2_INTEGRATION.md).

## Revision, approval and readiness

Work began from merged PR #6 / main `fceb46a` on `feat/v2-native-integration`. The executed gzip plan was pinned at `c1d8de3c3e8835694e64709742d213f34b0cd933` in PR #7, with SHA-256 `97c0018f94f62555de1680eb243381db41d50e8118ba7bfbc4be249335d25879`. The user separately approved that exact revised scope after the initial upload stop. Original uncommitted `.gitignore`, `.vscode/settings.json` and `databricks.yml` bytes were preserved.

Phase A confirmed the named `winterops` profile, expected existing workspace/warehouse, catalog/schema/Volume privileges, protected schemas/ownership, absent development names and absent original upload destinations. Both local artifacts matched their hashes and every parsed CSV record. Seven read-only statements passed, including protected source/payload/view reconciliations, Gold aggregates, Delta histories and synthetic V2/manifest compatibility. Their elapsed client request time totaled **30.942 seconds**. Local submission-wrapper guards were corrected before SQL submission; no SQL was retried.

Before the revised integration, source CSV hashes, encoded/decoded artifacts, user-file preservation, workspace/warehouse configuration, privileges, protected metadata and development-name conflicts were freshly checked. Both artifact fingerprints and both input scope/schema/record-ordinal guards passed **before all DDL**. The initial first-week upload was reused without reupload.

## Earlier approved attempt — stopped, retained for audit

| Original upload | Bytes | Actual outcome |
|---|---:|---|
| January 5–11 NDJSON | 3,619,379 | HTTP 204 in 9.551 seconds; post-stop HEAD 200 with expected length |
| January 19–25 NDJSON | 152,492,496 | Hard client deadline at 180.010 seconds; no success response; post-stop HEAD 404 |

That attempt stopped with **zero integration SQL**, no development-table creation and no automatic retry, cleanup or rollback. Protected metadata, parent grants and warehouse configuration matched afterward; final protected-data SQL postflight was not reached. The 404 is a point-in-time observation, not a guarantee about eventual transfer outcome. The old attempted destination was not adopted, overwritten, deleted or retried in the revised run.

## Revised upload and actual native results

Optional `export_bronze(..., compression='gzip')` and `--artifact-compression gzip` preserve the plain default and decoded NDJSON bytes. Gzip headers omit filename/time; encoded and decoded hashes are distinct. The January 19–25 gzip upload was **9,920,290 bytes**, HTTP **204** in **23.959 seconds**, with no overwrite and subsequent metadata visibility. Its SHA-256 is `5516fe43d00a609c858f71323b7c4fa7c856ca7c3b8c69137e6e67ac5b99034c`; it decodes to the original 152,492,496-byte artifact SHA-256 `94b6464999a58757ea6977cdc3d8b6e402b19edac2b9843369e7c1a18738c172`. The original CSV fingerprints, source version IDs, processing keys, row order, repeats and audit fields remain unchanged. Exact source fingerprints/versions are in the [source report](DATA_FOUNDATION_V2_SOURCE_REPORT.json).

All three names were absent before their fail-if-exists CREATE operations. Creation metadata confirmed exact schemas, managed Delta type and expected authenticated ownership:

| Created object | Final rows |
|---|---:|
| `workspace.default.winterops_v2_dev_bronze` | 120,969 |
| `workspace.default.winterops_v2_dev_silver` | 120,969 |
| `workspace.default.winterops_v2_dev_manifest` | 2 |

| Native per-source result | January 5–11 | January 19–25 |
|---|---:|---:|
| Bronze = Silver observations | 2,810 | 118,159 |
| HEADER | 19 | 34 |
| VALID | 2,791 | 118,125 |
| Other INVALID | 0 | 0 |
| Observed identifier strings | 27 | 316 |
| Plow-active observations | 2,790 | 92,747 |
| Spreader-active observations | 164 | 50,405 |
| Repeated valid-payload members retained | 10 | 1,527 |
| Outside configured review envelope | 677 | 0 |
| Final manifest status / stage | COMPLETE / COMPLETE | COMPLETE / COMPLETE |
| Manifest attempts / errors | 2 / 0 | 1 / 0 |

There are **120,916 VALID observations and 53 retained HEADER observations**, with no other INVALID rows. Geographic review-envelope flags remain diagnostics; they do not turn otherwise valid coordinates into parsing/domain failures. The reference source report's other gap/participation distributions remain local evidence and were not all recomputed natively.

The matrix first committed January 5–11 Bronze and recorded `BRONZE_WRITTEN`. An explicit checkpoint confirmed the complete 2,810-row Bronze scope with no Silver rows. The controlled second attempt verified Bronze and skipped its rewrite, then wrote Silver, reconciled and completed the manifest. This is the approved deliberate application-stage interruption; it did not kill a process or inject an unexpected runtime failure.

The first unchanged rerun was a read-only full-content/manifest check with no DML. After appending January 19–25, its unchanged rerun also used no DML. A final first-week check matched complete Bronze/Silver multisets and unchanged COMPLETE manifest content, attempt count and timestamp. All persisted comparisons use both directions of `EXCEPT ALL`, retaining duplicate multiplicities, provenance, classification and values rather than relying on row totals alone. These verify decisions in the reviewed SQL matrix; the optional PySpark adapter was not invoked.

## Runtime compatibility and bounded resource use

All **38** statements were `SUCCEEDED`: **22 READ, 3 CREATE, 13 scoped WRITE**. Responses were complete and untruncated; expected aggregate/command shapes and counts passed. There were no SQL errors, cancellations, timeouts or automatic retries in the revised run. Each read returned one aggregate row, each DML returned one command-metrics row, and CREATE returned an empty success; none exposed detailed telemetry.

Observed native compatibility passed for plain/gzip JSON `read_files`, binary-file encoded fingerprints, explicit JSON DATE/TIMESTAMP parsing, `TIMESTAMP_NTZ`, shared Silver classification, managed Delta CREATE, `INSERT INTO ... REPLACE WHERE`, UTF-8 manifest metadata round-trip and full multiset `EXCEPT ALL` reconciliation. No corrective SQL/transformation change was needed after approval.

- Revised SQL phase wall time: **130.391 seconds** within its 564-second reservation.
- Revised per-request client times sum to **125.133 seconds**; slowest was fresh protected-source validation at **9.444 seconds**.
- With Phase A: **45 SQL statements**, 156.075 seconds of request time / **161.333 seconds** of conservatively combined active SQL elapsed time, below 600 seconds.
- Bounds remained 30-second wait / CANCEL, hard 45-second client deadline, 200 rows / 65,536 bytes, 256 MiB / 180 seconds per upload, sequential execution and no retries/chunk fetching.
- Existing warehouse state changed from STOPPED to RUNNING through approved SQL use. Configuration and existing auto-stop settings matched; no explicit configuration change, compute/job creation or schedule was submitted.

These are client elapsed times, including transport/startup and metadata overhead, not billing, CPU or execution-engine scan measurements. Gzip reduces transport bytes, not decoded scan volume; these results do not establish larger-scale performance. No further compute was run after the approved matrix.

## Protected pipeline and engineering review

Fresh and final checks matched the original one-week Bronze/Silver counts (**110,337**, including **26 HEADER / 110,311 VALID**), stored source version/path/hash metadata and payload multiplicities. Published Gold still reconciled to **79 buckets / 110,311 observations / 79,471 plow-active / 68,870 spreader-active / 2,210 repeated-payload members**, with per-hour distinct identifier counts unchanged (range 1–20). Original Delta versions remained Bronze **2**, Silver **0**. All five protected object metadata snapshots, parent grants and warehouse configuration matched after completion. No protected table/view/source file was a write target.

Native guards verify the immutable serialized artifacts and their source scope. The original CSVs were hashed locally; this run does not claim a fresh native checksum of an independently uploaded original CSV. Existing Gold retains its original exact one-week selection and was not pointed at V2.

All **110 offline tests pass**, including gzip decoded-byte equality, repeat preservation, repeatable headers, unchanged local manifest state, retained plain exports and protected path rendering. Syntax, aggregate fixture and offline render checks pass. GitHub CI must be assessed at the exact PR head. Updated artifacts are aggregate-only evidence/status documentation; telemetry, tokens, private URLs and object/statement/warehouse IDs remain outside Git.

The three table writes are **not atomic together**, and creation now cannot be replayed as a fresh run. Unexpected partial failure, source revisions, concurrent writers, forced-crash recovery, distributed exactly-once processing and the optional PySpark/notebook entrypoints remain outside this native evidence. No cleanup/deletion, rollback, grant change, warehouse configuration change, job or schedule occurred.

Review PR #7 and confirm source identifier lifecycle, CRS and timezone semantics before widening operational interpretation or promoting V2 into consumers. Preserve source-local/naive timestamps. Observed identifier strings are not a fleet roster; observation counts and gaps do not establish working time, inactivity, availability, road coverage or productivity. Any later write, promotion or native run requires a new concrete reviewed scope. Weather, forecasting, optimization, streaming and dashboards remain subsequent work.
