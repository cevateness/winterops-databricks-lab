# Unified three-week V2 Gold foundation

**Current native state: PUBLISHED_AND_VERIFIED after separate approval of the read-only postflight.** See [actual execution](THREE_WEEK_NATIVE_INTEGRATION.md). The following local preparation evidence is historical: Baseline is merged main `7662ece` (PR #7). That prior integration verified two isolated V2 weeks; the original January 12–18 Silver/Gold views retain their separate exact one-week scope. This task performed bounded read-only file/metadata GET requests, local processing, SQLite-adapted SQL validation and offline rendering. No SQL was submitted to Databricks and no remote upload, data/object/grant/configuration change, job or schedule ran.

A [GET-only metadata pass](THREE_WEEK_METADATA_READINESS.json) matched the three V2 schema/identity contracts and five protected object definitions, confirmed all three proposed Gold names absent (404), and matched the existing warehouse configuration. It did not run SQL or revalidate live data counts/privileges; those remain part of the bounded approval matrix.

## Original source versus transport

The original byte-preserving CSV landing contract is in `landing.py`. First/third-week targets use `/Volumes/workspace/default/winterops_raw/original_csv/<filename>/<CSV-SHA-256>/<filename>`. The middle week reuses `/Volumes/workspace/default/winterops_raw/snowplow-2026-01-12_2026-01-18.csv`. No duplicate middle-week CSV upload is proposed. Every reference binds filename, covered dates, original CSV hash and byte count. An existing path must verify identical; a conflict stops execution without overwrite or deletion.

JSONL/gzip exports under `foundation_v2_dev/<source-version>/<transport-hash>/bronze.jsonl[.gz]` are parsed-observation transport, not original CSVs. The original CSV hash, decoded JSONL hash and encoded transport hash have different meanings. Gzip preserves decoded records, ordinals, repeats and audit fields; it is not a new source version.

The previous V2 `source_file_path` remains its original private local acquisition provenance; existing rows/manifests are not rewritten to pretend they were read from new Volume locations. The explicit [selection](THREE_WEEK_SELECTION.json) maps each exact source version/processing key to `original_csv_volume_path`, which is retained in every Gold grain and verified by native CSV fingerprint guards before publication. Source URLs remain the official archive identities; the middle file was retrieved from the existing Volume and adopted as `LOCAL_IMPORT`, not downloaded again from the city. Private staging/SQLite/export files stay outside Git.

## Middle-week backfill and observed differences

The HEAD/GET request returned the documented **8,671,212 bytes** and SHA-256 `f5d7633c910e1ad6be23b4111445bf0bc14fe2071c6ea0f0d4cd456295ea9e94`. It used no compute/SQL, redirects or retries, and a 90-second hard client deadline. The existing V2 parser, policy, source-version construction, manifest and gzip exporter processed only the new local scope. Full ordered row digests and complete run metadata for both earlier local weeks matched before/after.

| Middle-week metric | Prior legacy native evidence | New local V2 |
|---|---:|---:|
| Bronze / Silver | 110,337 | 110,337 |
| HEADER / VALID / other INVALID | 26 / 110,311 / 0 | 26 / 110,311 / 0 |
| Observed identifier strings | 251 | 251 |
| Plow / spreader observations | 79,471 / 68,870 | 79,471 / 68,870 |
| Hourly buckets | 79 | 79 |
| Repeated valid-payload members / excess copies | 2,210 / 1,113 | 2,210 / 1,113 |
| Outside configured geographic review envelope | Not measured under V2 policy | 186 warnings |

The additional 186 warnings are legitimate new diagnostics under the documented broad review box, not 186 invalid coordinates or proof of a wrong location. Raw identifier whitespace, stricter parsing rules and payload serialization remain V2 contracts; aggregate agreement does not claim byte-for-byte equivalence with legacy typed rows or their payload hashes. These are local classifications compared with prior native aggregates, not fresh native backfill results. See [source/backfill evidence](THREE_WEEK_SOURCE_EVIDENCE.json).

## Analytical contracts

`unified_gold.py` builds candidate SELECTs, validation SQL and three create-only view statements. It has no authentication or execution capability. Every source must have an explicit CSV fingerprint, source-version ID, processing key, pipeline revision, quality policy and expected source count. There is no implicit latest/active revision. One processing selection is allowed per logical source week; duplicate revisions/policies for that week fail. Different policies across different weeks require explicit opt-in and remain distinct grains, never blended. The reviewed three-week selection uses the same default policy throughout.

At query time the common gate requires exactly one selected COMPLETE manifest with COMPLETE last stage, matching source/policy metadata and counts. It checks Bronze/Silver scope, unique ordinals, complete audit lineage, quality/domain contracts and payload frequencies. Unselected revisions/policies are excluded before aggregation. A missing or inconsistent selected week raises an error rather than returning a partial multi-week result. Standalone preflight also checks the empty/invalid selection case. Native optimizer/error-propagation behavior remains a required integration check.

All products retain dataset, filename, original CSV hash/path, source-version ID, processing key, pipeline revision, quality-policy hash and source-week bounds:

| Product / proposed view suffix | Grain | Meaning |
|---|---|---|
| `winterops_v2_gold_hourly_observations` | Selected processing version + source-local/naive hour | VALID observation counts, overlapping plow/spreader flags, four exclusive equipment categories, engine diagnostics, direct distinct identifier count and repeated-valid-payload members |
| `winterops_v2_gold_daily_activity` | Selected processing version + source-local/naive date | Same activity/composition metrics; distinct identifiers calculated from that day's valid rows, hours with VALID telemetry and maximum within-hour participation |
| `winterops_v2_gold_weekly_quality` | Selected processing version/source week | Bronze/Silver/class/quarantine counts, invalid-coordinate issues, independent geography warnings, valid activity/participation, repeated payload members/groups/excess and ordered source-clock gap diagnostics |

`quarantine_rows = HEADER + INVALID`. Only VALID rows enter activity metrics; invalid-only hours are not counted as hours with telemetry. All-header/invalid-only weeks remain present in weekly quality with zero activity, and have no hourly/daily activity rows. No synthetic zero buckets imply inactivity.

Plow-only + spreader-only + both + neither equals observations. Plow flag count equals plow-only + both, and spreader equals spreader-only + both. Engine-off-with-equipment is an overlapping diagnostic. Repeats remain observations; valid payload frequencies are recomputed within the selected valid scope, not inferred from potentially mixed valid/invalid payload occurrences. Reporting gaps use per-processing-key/raw-identifier ordering by naive event time then source record number, with the existing calendar-field microsecond index; gaps never bridge source versions. Thresholds come from the selected policy.

Distinct identifiers are computed separately from valid rows at each grain. Do not sum hourly/daily counts into a week or add weekly counts into a physical fleet total. Source-local/naive times are preserved as `TIMESTAMP_NTZ`; no timezone, instant or UTC conversion is introduced. Counts/gaps do not establish workforce, operating duration, inactivity, availability, road coverage or productivity.

## Validation and engineering review

The local real-data [SQLite results](THREE_WEEK_LOCAL_SQL_RESULTS.json) pass the selection gate and per-week/hour/day/week reconciliations: **231,306 Bronze/Silver = 79 HEADER + 231,227 VALID + 0 other INVALID**, **236 hourly buckets**, **20 daily rows**, **3 weekly rows**, **175,008 plow** and **119,439 spreader observations**. Geographic warnings total **863** (677 / 186 / 0). There is no three-week fleet-size inference.

Sixteen synthetic tests compare all product fields with an independent Python row-based oracle and exercise source revisions, mixed-policy opt-in, unselected policies, missing/failed/duplicate manifests, same-count lineage corruption, equal NULL audit values on both layers, repeats, fractional ties, all-header weeks, separate geography/invalid-coordinate diagnostics, partial-completion rejection and published metric corruption that preserves weekly totals. Candidate reconciliation checks valid/quarantine/class totals, equipment identities, nonnegative counts and hourly/day/week totals per selected version. Published verification additionally compares complete expected/published aggregate rows with both directions of `EXCEPT ALL`, not totals alone.

SQLite explicitly adapts native date/NTZ/decimal functions and error handling. It is not evidence of native parsing, optimizer behavior, DDL, privileges or performance. Native `raise_error` is documented by [Databricks](https://docs.databricks.com/aws/en/sql/language-manual/functions/raise_error); the Files API's binary download contract is documented [here](https://docs.databricks.com/api/files/v2/file). No new library dependency is introduced.

The design reuses existing V2 tables, parsing, policy, manifest, shared Silver SQL and clock arithmetic. Inline selection avoids an extra registry table and prevents accidental source promotion. The tradeoff is deliberate full selected-source guard scans on view queries; native cost and optimizer behavior must be measured within the approval budget. Three-table state transitions and three view publications are not one transaction. Serialized execution is required; concurrent exactly-once ingestion, automatic retries, distributed leases and scheduling are not claimed. The legacy pipeline is preserved rather than redefined.

The full offline suite passes **126 tests** (110 existing plus 16 new); syntax, original aggregate fixture and offline render checks pass. GitHub CI is assessed on the exact PR head.

## Dashboard-ready use and next gate

[`sql/v2_gold_dashboard.sql`](../sql/v2_gold_dashboard.sql) provides four charts: (1) grouped weekly activity comparison, (2) hourly observation/flag trends for one selected week per bounded fetch, (3) stacked daily **four-category** composition, and (4) separate weekly classification, warning/repetition and gap diagnostic panels. Do not stack overlapping flag counts or warnings with mutually exclusive classifications. Display sparse telemetry as observations, not continuous activity.

```powershell
python scripts/render_unified_gold.py --selection docs/THREE_WEEK_SELECTION.json --output $env:TEMP\winterops-threeweek-candidates.sql
python scripts/render_unified_gold.py --selection docs/THREE_WEEK_SELECTION.json --publication --output $env:TEMP\winterops-threeweek-publication.sql
python scripts/prepare_threeweek_plan.py --output "$env:LOCALAPPDATA\WinterOps\foundation_v2\reviewed-threeweek-plan.json"
python -m unittest discover -s tests -v
```

The native approval bundle can contain hex-encoded private acquisition provenance in manifest SQL; the preparer rejects output under any Git tree. Public evidence contains only aggregate metrics, source identities, statement hashes and Volume targets. Source coordinates, raw vehicle identifiers, record payloads, credentials and private workspace/object IDs are absent.

Review the single PR and [bounded integration plan](THREE_WEEK_INTEGRATION.md) before native execution. The existing native state remains the two V2 outer weeks and the separate one-week legacy Silver/Gold pipeline. The middle-week V2 append, two original-CSV landings and all three new Gold publications remain pending. Weather, H3, forecasting, optimization, jobs, streaming, schedules and a new dashboard application are outside this task.
