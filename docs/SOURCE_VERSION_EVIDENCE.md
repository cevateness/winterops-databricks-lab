# Exact source-version evidence (2026-10-28)

**Source audit: PASS. Lesson 6 candidate SQL validation: PASS. Lesson 7 published-view verification: PUBLISHED_VERIFIED_STABLE. Notebook/Spark entrypoint: NOT RUN.**

This is live aggregate evidence obtained through the authenticated local `winterops` profile and Statement Execution API. It supplements the original user-reported fixture; that fixture and Lessons 1–5 were not changed. No detailed vehicle records, identities, credentials or private workspace URLs are included.

## Selected source

- Dataset: `windsor_snowplow_activity`
- Filename: `snowplow-2026-01-12_2026-01-18.csv`
- Exact path: `/Volumes/workspace/default/winterops_raw/snowplow-2026-01-12_2026-01-18.csv`
- Current CSV byte SHA-256, also matching the stored Bronze/Silver source-file hash: `f5d7633c910e1ad6be23b4111445bf0bc14fe2071c6ea0f0d4cd456295ea9e94`
- Current CSV size: **8,671,212 bytes**; the exact-path binary-file query returned one file.
- Source-local/naive interval: `[2026-01-12 00:00:00, 2026-01-19 00:00:00)`; source timezone remains unverified.
- Existing tables: `workspace.default.winterops_bronze_windsor_activity` and `workspace.default.winterops_silver_windsor_week_sample`.

The inventory returned one Bronze version for the expected filename/path and one version across the entire Silver table. Dataset, filename, path and hash matched exactly in both. The selected Silver count also equals the whole Silver table count.

The exact Volume CSV was independently checksummed in the warehouse with `sha2(content, 256)` over `read_files(..., format => 'binaryFile')`. Only its hash and byte count were returned; no raw content was downloaded. The hash matched ingestion metadata in both tables. These queries are point-in-time observations, not pinned Delta versions or an atomic file/multi-table snapshot. Recheck the source before subsequent consumers run.

## Aggregate reconciliation

| Metric | Expected | Observed |
|---|---:|---:|
| Selected Bronze observations | 110,337 | 110,337 |
| Selected Silver observations | 110,337 | 110,337 |
| Whole Silver observations | 110,337 | 110,337 |
| HEADER | 26 | 26 |
| VALID | 110,311 | 110,311 |
| Other INVALID | 0 | 0 |
| Distinct valid truck identifiers | 251 | 251 |
| Valid plow-active observations | 79,471 | 79,471 |
| Valid spreader-active observations | 68,870 | 68,870 |
| Unknown/null quality classifications | 0 | 0 |
| Valid observations outside the naive window or missing event time | 0 | 0 |
| Missing/malformed record hashes | 0 | 0 |
| Invalid payload-frequency/repetition flags | 0 | 0 |
| Bronze/Silver payload multiplicity or occurrence-count mismatch groups | 0 | 0 |

All 17 required Silver column types matched the existing Python contract; metadata returned 18 columns in total. `event_time_unzoned` is `TIMESTAMP_NTZ`; status/repetition fields are Boolean and `payload_occurrences` is BIGINT. No timezone conversion or deduplication was performed. These observations do not establish service coverage, hours worked or productivity.

## Endpoints and execution bounds

- `GET /api/2.0/sql/warehouses`: allowed; one existing serverless PRO, 2X-Small warehouse, one-cluster minimum/maximum, configured auto-stop 10 minutes. It initially reported `STOPPED`.
- `POST /api/2.0/sql/statements`: allowed. Five statements succeeded: `SELECT 1`, Silver column metadata, source-version inventory, aggregate/multiplicity reconciliation, and the exact Volume CSV checksum. No result was truncated or required extra chunks. Reading the canonical Volume file was permitted; no separate file-download endpoint was used.
- Each request used `wait_timeout=30s`, `on_wait_timeout=CANCEL`, `JSON_ARRAY` / `INLINE`, `row_limit=25`, `byte_limit=65536`, and a 45-second local client deadline. Result limits bound returned data, not the amount of data scanned. No unbounded polling or manual retries were used.
- The authorized source audit used the existing warehouse; statement submission can resume stopped compute. A final metadata read confirmed the same single warehouse was `RUNNING`, with size, cluster bounds and auto-stop unchanged. No warehouse create/start/stop/edit endpoint, DDL, job submission or scheduling request was sent.

Observed source-audit compatibility includes `COUNT_IF`, `RLIKE`, `CAST(... AS TIMESTAMP_NTZ)`, named parameters, aggregate/full-outer-join payload reconciliation, `read_files` in binary-file mode and `sha2` over binary content. No runtime error occurred in these source-audit statements. The subsequent approved Lesson 6 SQL validation is recorded separately below.

API contract reviewed: [Statement Execution API](https://docs.databricks.com/api/statement-execution/v1/execute-statement), [SQL warehouse API](https://docs.databricks.com/api/warehouses/v1/list-warehouses), [`read_files`](https://docs.databricks.com/aws/en/sql/language-manual/functions/read_files).

## Approved Lesson 6 SQL API validation

The user approved one bounded read-only run from commit `11dba68`, against the same authenticated workspace and previously verified warehouse. The exact hash above and unchanged expected fixture were supplied to `build_plan(config)`. Its two existing `preflight` statements and single `validation` statement were submitted unchanged, sequentially, after a Silver schema recheck. No publication statements were submitted.

| Step | API execution state | Returned rows | Outcome |
|---|---|---:|---|
| Silver column metadata | SUCCEEDED | 18 | All 17 required types matched, including `TIMESTAMP_NTZ` |
| Source preflight | SUCCEEDED | 1 | `bronze_check`, `preservation_check`, `version_check`, `quality_check`, `domain_check`, `evidence_check`: PASS |
| Payload preflight | SUCCEEDED | 1 | `payload_check`: PASS |
| Candidate Silver/Gold CTE reconciliation | SUCCEEDED | 1 | `consumer_check`, `hourly_check`: PASS |

Each assertion output was SQL `NULL`, the successful result of `assert_true`; the runner required the expected column names, exactly one result row and all-null assertion values before continuing. All responses were HTTP 200 / `SUCCEEDED`, complete and untruncated. No runtime error, source-version mismatch, cancellation, unexpected response or retry occurred.

The source preflight re-established the selected Bronze/Silver counts and whole-Silver version guard, approved quality/activity evidence, valid-row domain/window checks and header/invalid classification consistency. Payload preflight confirmed occurrence multiplicities. Candidate reconciliation confirmed 110,311 valid observations plus 26 quarantined observations reconcile to 110,337, and hourly observation/status/repetition totals reconcile to the candidate valid consumer. Hourly bucket-count and per-bucket truck/repetition invariants passed; no detailed buckets or truck identifiers were returned.

The same existing warehouse and its unchanged configuration were verified before submission; it initially reported `STOPPED` and served the approved statements. Requests used `wait_timeout=30s`, `on_wait_timeout=CANCEL`, 25-row/65,536-byte inline result limits and a hard 45-second client deadline. SQL API requests were sent once with redirects and automatic retries disabled. Credentials remained in memory and were not written into any report.

Ignored local artifacts include `.venv/winterops-lesson6-validation.sql`, `.venv/winterops-lesson6-validation-scope.json` and the sanitized `.venv/winterops-lesson6-once-11dba68.json` run report. Warehouse/statement identifiers remain local. The completed run was not repeated.

Reproduce the SQL locally with:

```powershell
python scripts/render_analytics_sql.py --source-file-sha256 f5d7633c910e1ad6be23b4111445bf0bc14fe2071c6ea0f0d4cd456295ea9e94 --expected-summary data/fixtures/windsor_week_2026_01_12_18_summary.json --validation-only
```

## Publication readiness and remaining limits

The Lesson 6 run verified nested candidate CTEs, native `TIMESTAMP_NTZ` predicates, source-local/naive hour construction and assertion/reconciliation behavior. No SQL runtime incompatibility was observed. The separately approved Lesson 7 publication and actual published-view verification subsequently passed, as recorded below.

Lesson 6 was shared SQL execution, **not execution of the Databricks notebook or its Spark entrypoint**. It did not itself verify DDL or published objects. Lesson 7 now separately verifies create-only privileges, created-view metadata, published postflight and stable repeated reads. Replacement, notebook import/path compatibility and repeated DDL remain untested. Sources remain point-in-time and should be rechecked before future use.

No DDL, `mode=apply`, publication, source modification, job/schedule creation or warehouse configuration change was performed during Lesson 6 validation. The subsequent Lesson 7 run used separate explicit approval for the three create-only view operations; no replacement, source modification, grant/owner transfer, job/schedule or warehouse configuration change was performed.

## Lesson 7 follow-up

After fresh source/schema/privilege checks and separate explicit approval from `f240d60`, all three create-only view operations succeeded. Type, authenticated-creator ownership and definitions matched. All 11 bounded SQL statements passed without errors, cancellations, truncation, retries or rollback. Published postflight assertions and safe aggregate results matched across two read-only verification passes. Gold has 79 hourly buckets, 110,311 observations, 79,471 plow-active, 68,870 spreader-active and 2,210 repeated-payload observations. Hourly distinct truck identifiers range from 1 to 20. Parent grants and warehouse configuration were unchanged. See [publication evidence](LESSON_7_PUBLICATION.md) and [all safe hourly counts](LESSON_7_GOLD_RESULTS.json); no notebook/Spark entrypoint was run and no DDL rerun was attempted.
