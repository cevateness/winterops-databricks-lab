# Exact source-version evidence (2026-10-28)

**Source audit: PASS. Lesson 6 candidate validation: PREPARED / NOT RUN.**

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

Observed SQL compatibility includes `COUNT_IF`, `RLIKE`, `CAST(... AS TIMESTAMP_NTZ)`, named parameters, aggregate/full-outer-join payload reconciliation, `read_files` in binary-file mode and `sha2` over binary content. No runtime error occurred in these source-audit statements. This does not validate the unexecuted Gold query or notebook entrypoint.

API contract reviewed: [Statement Execution API](https://docs.databricks.com/api/statement-execution/v1/execute-statement), [SQL warehouse API](https://docs.databricks.com/api/warehouses/v1/list-warehouses), [`read_files`](https://docs.databricks.com/aws/en/sql/language-manual/functions/read_files).

## Prepared Lesson 6 scope and remaining approval

The existing `build_plan(config)` was rendered offline for the exact hash above with the unchanged expected aggregate fixture. The read-only plan contains two source preflight statements and one candidate Silver/Gold CTE reconciliation query, with no view publication DDL or dependency on prospective consumer views.

Ignored local artifacts are `.venv/winterops-lesson6-validation.sql` and `.venv/winterops-lesson6-validation-scope.json`. The scope records the selected existing warehouse identifier locally; it contains no credentials or workspace URL.

Reproduce the SQL locally with:

```powershell
python scripts/render_analytics_sql.py --source-file-sha256 f5d7633c910e1ad6be23b4111445bf0bc14fe2071c6ea0f0d4cd456295ea9e94 --expected-summary data/fixtures/windsor_week_2026_01_12_18_summary.json --validation-only
```

**Stopped at the user's separate approval gate.** The source audit authorization was not extended to Lesson 6 validation. Proposed next scope: the same `winterops` workspace and existing warehouse, one schema metadata recheck followed sequentially by the three shared validation statements, with the same per-request limits and immediate stop on failure. No candidate validation SQL, view DDL or notebook `mode=apply` was executed.

Executing these shared statements through the SQL API would validate their warehouse runtime behavior. It would not execute the Python notebook or its Spark entrypoint; a direct notebook `mode=validate` run needs its own approved runtime context. Gold's nested CTEs, hour construction and assertion behavior remain unverified until validation actually runs.
