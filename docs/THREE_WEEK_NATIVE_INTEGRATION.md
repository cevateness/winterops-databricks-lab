# Three-week native integration — published and verified

**2026-10-30: PASS_NATIVE_PUBLISHED_GOLD_AND_PRESERVATION.** The separately approved 16-statement read-only continuation `9f5896dc8e963a3aa3c6a04adf4873b36315bac051d5128eb192046fd1d31888` completed successfully. Hourly (236 rows), daily (20) and weekly (3) views passed full multiset comparisons, published outputs matched candidates/offline predictions, and all final preservation/hash/metadata/grant/warehouse checks passed. The earlier stopped phases below remain recorded for audit.

**Earlier creation phase:** After explicit approval of corrected continuation `146088dfb1a50e2d05f0b9d901b9ced2fdc42fc1279d6086d75b4fd53639aef3` from merged main `2a3b75a`, the middle V2 backfill completed and the three create-only views passed ownership, definition and schema checks. The first published multiset comparison returned **CANCELED** under the 30-second wait/CANCEL bound, after 31.317 seconds. Execution stopped immediately; no retry, later SQL, cleanup or rollback followed. See [actual sanitized evidence](THREE_WEEK_NATIVE_RESULTS.json).

## What actually ran

Initial read-only readiness submitted seven original statements, all server-SUCCEEDED. Legacy source/payload/view/Gold checks and Delta versions (Bronze 2 / Silver 0) matched. The client stopped on the manifest timestamp comparison: raw TIMESTAMP values were serialized to milliseconds, whereas prior CAST-to-STRING evidence retained microseconds. Both selected manifests were COMPLETE with expected counts/attempts and matching metadata/policy hashes. One GET inspected the already-completed result; no SQL was retried.

The separately approved correction returned audit timestamps as STRING and combined the original middle CSV/new-scope guards, preserving all original checks within the 45-statement cap. Fresh permissions, workspace/warehouse, identity/schema, artifact hash and name-conflict checks passed. Both outer weeks passed full two-direction Bronze/Silver row-multiset checks; the precise manifest snapshot matched prior evidence, and the middle original CSV/absent-scope guard passed **before uploads**.

| Approved immutable upload | Bytes | Actual result / client seconds |
|---|---:|---|
| January 5–11 original CSV | 221,818 | HTTP 204 / 1.428 |
| January 12–18 JSONL gzip | 9,227,828 | HTTP 204 / 22.897 |
| January 19–25 original CSV | 9,302,196 | HTTP 204 / 23.343 |

Native binary-file guards matched the landed outer CSVs and middle transport fingerprints. The existing middle original CSV was reused and verified; it was not duplicated. No existing file was overwritten.

Only the middle source version/processing key was appended: **110,337 Bronze and Silver rows = 26 HEADER + 110,311 VALID + 0 other INVALID**. Full persisted row/multiplicity checks passed. Manifest updates reached COMPLETE; the three-selected-version COMPLETE guard passed. No existing V2 data scope was replaced.

## Native candidates versus predictions and published results

The candidate reconciliation passed natively in 19.758 seconds; all three weekly candidate rows matched the prior local aggregates in 10.391 seconds:

| Selected source week | Bronze = Silver | HEADER | VALID | Plow / spreader observations | Valid telemetry hours / dates | Geography warnings |
|---|---:|---:|---:|---:|---:|---:|
| January 5–11 | 2,810 | 19 | 2,791 | 2,790 / 164 | 42 / 7 | 677 |
| January 12–18 | 110,337 | 26 | 110,311 | 79,471 / 68,870 | 79 / 7 | 186 |
| January 19–25 | 118,159 | 34 | 118,125 | 92,747 / 50,405 | 115 / 6 | 0 |

For the selected scopes, native candidate totals are **231,306 Bronze/Silver rows, 79 HEADER, 231,227 VALID, 175,008 plow observations and 119,439 spreader observations**, with **236 valid telemetry hours / 20 dates / three weekly candidate rows** and **863 independent review-envelope warnings**. These initially returned as native candidates; the approved read-only continuation subsequently returned matching published results and full per-product row equality. No physical fleet-size or work-duration inference is made.

| Created view in `workspace.default` | Create-only DDL | Owner / definition / schema | Published multiset verification |
|---|---|---|---|
| `winterops_v2_gold_hourly_observations` | SUCCEEDED | PASS | PASS / 236 rows |
| `winterops_v2_gold_daily_activity` | SUCCEEDED | PASS | PASS / 20 rows |
| `winterops_v2_gold_weekly_quality` | SUCCEEDED | PASS | PASS / 3 rows |

Native types include `TIMESTAMP_NTZ` for the hour bucket, DATE source/day fields, STRING source/processing identities, integer count fields and DOUBLE maximum gap seconds. The weekly constant `bronze_rows` is INT; native COUNT metrics are BIGINT. Source-local/naive calendar/window/gap calculations matched candidate expectations. No notebook/PySpark entrypoint or negative-guard fault injection ran.

The combined published comparison canceled with HTTP 200 / statement CANCELED, without a returned assertion failure. This shows the request did not finish within the configured wait; no server execution profile or billing/CPU data was collected to establish a detailed root cause. The subsequent separately approved comparisons passed: hourly **30.388**, daily **14.830**, weekly **22.585 client seconds**. These checks retain all fields and duplicate multiplicity. Startup/transport are included, so client time is not identical to server execution time; the hourly request has narrow headroom against the configured wait.

## Budget, preservation limits and next scope

The complete run used **45 SQL submissions: 44 SUCCEEDED and one CANCELED**, with no automatic retries. The initial seven requests all succeeded at the server but one client audit comparison stopped on timestamp precision; its corrected snapshot subsequently matched full microseconds. The creation continuation submitted 22 requests and stopped at its first cancellation. The explicitly approved read-only continuation then submitted 16 requests, all complete/untruncated and validated.

Cumulative active elapsed time was **365.451 seconds** under 600, including the creation continuation's uploads and the final read-only metadata checks; approval waiting is excluded. Summed client SQL request time was **288.292 seconds**. The last read-only phase took **134.530 seconds**, of which requests summed to **118.024 seconds**. Billing, CPU and engine query profiles were not measured. No statement budget remains; do not replay either original or continuation plans.

The published hourly summary, 20 daily aggregate rows and three weekly aggregate rows matched the native candidates and prior offline values. Middle-week read-only rerun/full-content checks passed without DML. Both outer-week complete record multisets and full-precision manifest states/counts/timestamps/provenance hashes remained unchanged. Final legacy source/payload/view/Gold checks passed: **79 buckets / 110,311 observations / 79,471 plow / 68,870 spreader**, Delta versions Bronze **2**, Silver **0**. All three original CSV fingerprints matched again. Eleven object identity/owner/schema/definition checks, parent/table effective grants and the existing warehouse configuration matched saved snapshots before and after the read-only phase. No further files, data or views were written in that phase.

[THREE_WEEK_POSTFLIGHT_PLAN.json](THREE_WEEK_POSTFLIGHT_PLAN.json) records the approved and executed **16 READ-only statements**. The three independent full `EXCEPT ALL` comparisons replaced the canceled combined comparison. Middle/first-week checks and the final three CSV hash guards were combined without dropping assertions or counts. The private executable plan and provenance remain outside Git; the public summary contains only scope, hashes, status and timings.

Local regression tests cover timestamp precision, combined guards, separate product comparisons and same-rowcount corruption. The fresh-render template uses 43 requests; the two historical unsuccessful client/server attempts explain the cumulative total of 45. **Never replay the fresh template**: the middle scope and all three views already exist. Future writes, replacements or native execution need a new reviewed scope. No cleanup, rollback, grant/warehouse changes, jobs, schedules, notebook or PySpark execution occurred.

The final code/evidence update is on `feat/threeweek-native-integration` for one reviewed commit. Offline tests and GitHub CI are assessed at that exact commit. Raw telemetry, actual vehicle identifiers, coordinates, credentials and private workspace/object/statement IDs are excluded. Source-local/naive time, coordinate reference and identifier lifecycle limitations remain unresolved; this is observation/reporting analytics, not proof of working time, coverage or productivity.
