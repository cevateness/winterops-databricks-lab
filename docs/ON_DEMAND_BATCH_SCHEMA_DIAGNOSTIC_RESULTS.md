# Native schema diagnostic — observed type-alias mismatch

**2026-10-30: SUCCEEDED_METADATA_DIAGNOSTIC_ONLY.** From merged PR #11 / main `89fc2378a3d79ef8e129dc9cb355382c6bec56e2`, the exact approved query SHA-256 `a4648e831a1d3360cdc117e372ed52758f048874ad8df066e7296a780d13ed7c` matched both the Git blob and the LF-normalized working file (10,170 bytes). It was submitted **once** to the existing authenticated `winterops` warehouse. Three identity/warehouse/permission GETs passed; no other native requests followed the result. See [all sanitized metadata and counters](ON_DEMAND_BATCH_SCHEMA_DIAGNOSTIC_RESULTS.json).

The statement succeeded in **11.621 client seconds**; total active diagnostic time was **14.186 seconds**. It returned **59 complete rows**, with no truncation or extra chunk fetching, under the requested 200-row/65,536-byte limits. The API did not supply a total-byte metric; the evidence separately records the locally serialized result-array size. Bounds were 30-second wait/CANCEL and a hard 45-second SQL client deadline. These are client elapsed times, not CPU or billing measurements.

## Exact discrepancies

All eight discrepancies have expected type **`BIGINT`**, actual `DATA_TYPE` **`LONG`**, and actual `FULL_DATA_TYPE` **`bigint`**. Both expected and actual ordinals agree:

| Table suffix in `workspace.default` | Column | Expected = actual ordinal |
|---|---|---:|
| `winterops_v2_dev_bronze` | `source_record_number` | 10 |
| `winterops_v2_dev_bronze` | `source_line_end` | 11 |
| `winterops_v2_dev_silver` | `source_record_number` | 10 |
| `winterops_v2_dev_silver` | `source_line_end` | 11 |
| `winterops_v2_dev_silver` | `payload_occurrences` | 24 |
| `winterops_v2_dev_manifest` | `attempts` | 8 |
| `winterops_v2_dev_manifest` | `bronze_rows` | 9 |
| `winterops_v2_dev_manifest` | `silver_rows` | 10 |

The diagnostic reported **51 MATCH / 8 TYPE** rows. There were **no missing or extra columns, name/casing differences, or ordinal mismatches**. Bronze has 16 columns at positions 0–15; Silver has 30 at 0–29; manifest has 13 at 0–12. All actual schema names are `default`. All **59** `UPPER(FULL_DATA_TYPE)` values equal their expected SQL type declarations, including distinct `TIMESTAMP` and `TIMESTAMP_NTZ` fields.

The strict guard's counters were identical on every returned row:

| Counter | Observed |
|---|---:|
| Expected columns | 59 |
| Actual columns, case-insensitive discovery | 59 |
| Actual columns, exact guard filters | 59 |
| Exact guard joined rows | 59 |
| Exact guard matching rows | **51** |

## Interpretation and smallest recommended correction

The corrected zero-based guard fails because it compares the raw `DATA_TYPE` label `LONG` with the expected SQL declaration `BIGINT`. [Databricks documents BIGINT and LONG as names for the same 8-byte integer type](https://docs.databricks.com/aws/en/sql/language-manual/data-types/bigint-type); the observed `FULL_DATA_TYPE=bigint` confirms the declared type for all eight fields. This is a metadata representation mismatch. The original guard also expected one-based positions, independently inconsistent with the zero-based positions now observed for all 59 columns.

The smallest recommended change is **metadata comparison only**: for this primitive-type schema, compare `UPPER(FULL_DATA_TYPE)` with the expected SQL declaration. Keep the exact column-count/name/order checks and preserve the `TIMESTAMP_NTZ` versus `TIMESTAMP` distinction. The observed metadata would satisfy all 59 type comparisons using that rule. Add a future regression fixture containing actual `DATA_TYPE=LONG` / `FULL_DATA_TYPE=bigint` pairs. No table alteration, data cast, transformation change or type-check removal is indicated by these results.

**No correction was applied.** The guard, Job SQL files, diagnostic SQL, tests and pipeline code remain unchanged. No guard rerun, telemetry/source-record read, DML, DDL, upload, Job creation/execution, permission/configuration change or retry occurred. Only local diagnostic evidence/status files were written. Existing offline/CI results from PR #11 are historical and were not rerun for this metadata observation. Native Jobs and new-source processing remain unverified.

The diagnostic consumed the fourth of the cumulative 16-request trial ceiling; cumulative active execution time is **122.092 seconds**. Remaining slots do not authorize more execution. The task stops here. A guard correction or another native validation/deployment requires separate authorization.
