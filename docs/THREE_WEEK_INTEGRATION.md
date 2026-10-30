# Original three-week integration plan — retained for audit

**Do not replay this original plan.** Integration completed through explicitly approved corrected and read-only continuations. The middle scope is COMPLETE, all three new views exist, and per-product published equality plus all final preservation checks passed. See [actual evidence](THREE_WEEK_NATIVE_INTEGRATION.md). The original preparation below is retained for audit, not authorization for another run.

The implementation and aggregate evidence were local when this plan was prepared. This document requests no implicit execution. A subsequent explicit approval must bind the reviewed revision and the exact private plan digest in [THREE_WEEK_NATIVE_PLAN.json](THREE_WEEK_NATIVE_PLAN.json). The plan preparer only renders local SQL and verifies local staged bytes; it never connects to Databricks.

## Exact files and objects

Use the authenticated `winterops` profile, the previously verified workspace/existing SQL warehouse, and existing Volume `workspace.default.winterops_raw`. Fresh metadata must match workspace/warehouse, schema contracts, identities, permissions, grants and protected configurations. The new view names must all be absent. Stop on a name/type/owner conflict; do not adopt or replace an existing object.

There are **three proposed immutable uploads, 18,751,842 bytes total**, with `overwrite=false`:

| Kind | Bytes | Destination |
|---|---:|---|
| January 5–11 original CSV | 221,818 | `original_csv/<filename>/271c9339a42043f441b6c17e82dd309609db4b20e9953b9f368a95ec472d763d/<filename>` under the existing Volume |
| January 19–25 original CSV | 9,302,196 | `original_csv/<filename>/b78d0fb82c8e3c5204ee79eea7a03417cd54bc935ead9b04577a30dc908c7c49/<filename>` under the existing Volume |
| January 12–18 V2 JSONL gzip | 9,227,828 | `foundation_v2_dev/73e9338d8a7e78ba01827806b2172a715a50b90c819959ba1ade17632f2d4433/2e67e1457d5a581804e66a33d8b1ddac4c21914dd0aaeef3653cb8b886f34d39/bronze.jsonl.gz` under the existing Volume |

Full filenames, paths, source/transport fingerprints, expected sizes and all selected processing keys are in the machine-readable plan and [selection](THREE_WEEK_SELECTION.json). Reuse the existing middle CSV at `/Volumes/workspace/default/winterops_raw/snowplow-2026-01-12_2026-01-18.csv`, hash `f5d7633c910e1ad6be23b4111445bf0bc14fe2071c6ea0f0d4cd456295ea9e94`; no middle CSV duplication is allowed. Existing first/third JSONL transports remain untouched. Only missing parent directories for these exact targets may be created. If a destination exists, bounded HEAD/GET fingerprint inspection must establish identical bytes before skipping it; otherwise stop without overwrite, deletion or adoption.

Append **only** middle source version `73e9338d8a7e78ba01827806b2172a715a50b90c819959ba1ade17632f2d4433` / processing key `5e478fdced5a0ac67865413d68b9359a97fffd980a2a6dee976d6ab984c599be` to:

- `workspace.default.winterops_v2_dev_bronze`
- `workspace.default.winterops_v2_dev_silver`
- `workspace.default.winterops_v2_dev_manifest`

The data operations are explicit column-listed INSERTs after an absence guard. There is no data-table replacement/overwrite. Four manifest updates use `REPLACE WHERE` for only that new middle processing key. Existing V2 scopes must retain complete row multisets and byte-identical manifest metadata/states/timestamps. No development-table DDL is included.

Create **only** these new views, sequentially with `CREATE VIEW`, never OR REPLACE:

- `workspace.default.winterops_v2_gold_hourly_observations`
- `workspace.default.winterops_v2_gold_daily_activity`
- `workspace.default.winterops_v2_gold_weekly_quality`

The three operations are not atomic. The existing `workspace.default.winterops_gold_windsor_hourly_observations` and all other legacy objects remain separate and unchanged.

## Reviewed matrix and bounds

The exact plan contains **45 SQL statements: 36 READ, 6 scoped WRITE, 3 CREATE VIEW**. No extra probing or retries fit this budget; metadata/Files API calls are separately bounded and cannot create compute.

1. Check metadata/permissions/conflicts and the three exact upload/reuse decisions. Upload only missing approved artifacts; do not overwrite or retry. Fresh SQL then captures legacy source/payload/published aggregates/Delta versions and outer-week manifest snapshots. Verify all three original CSV fingerprints and existing outer-week complete contents.
2. Verify middle transport hash, input schema/scope/ordinals/hash and absence of any middle Bronze/Silver/manifest scope. Record PROCESSING, append 110,337 Bronze rows, mark BRONZE_WRITTEN, append the shared-SQL 110,337 Silver rows, mark SILVER_WRITTEN, perform full two-direction record/multiplicity reconciliation, then mark COMPLETE.
3. Run the three-week COMPLETE guard, candidate reconciliation and safe weekly aggregates. Confirm native NTZ/date/microsecond/window/error-propagation behavior and expected schema/grain/results before DDL. Only then create the three new views and verify each type/owner/definition/columns using metadata.
4. Reconcile full expected versus published aggregate row multisets. Return only three per-week hourly summaries, 20 daily rows and three weekly rows (no raw 236-row hourly export). Verify the middle unchanged rerun decision with read-only content checks and **no additional DML**. Recheck outer-week contents/manifests, legacy reconciliations/Gold/Delta versions, all original CSV hashes and protected metadata/grants/configuration.

Bounds: at most **45 SQL submissions**, **600 seconds SQL-phase wall time**, sequential requests, `wait_timeout=30s`, `on_wait_timeout=CANCEL`, hard **45-second client deadline**, INLINE JSON at most **200 rows / 65,536 bytes**, no polling/chunk fetching/retries. Check enough remaining time before each submission. Each upload is capped at **16 MiB / 180 seconds**, all uploads at **32 MiB**; metadata requests use 15 seconds and optional file-verification GETs a hard 45 seconds with the same byte cap. Credentials remain in memory. Use no warehouse create/edit/start/stop endpoint, jobs, schedules, grants, source edits or notebook/Spark submissions. Existing stopped compute may resume through the approved SQL requests; configuration remains unchanged.

Expected complete V2 result: **231,306 Bronze = Silver = 79 HEADER + 231,227 VALID + 0 other INVALID**, three COMPLETE manifests, **236 hourly buckets / 20 daily rows / 3 weekly rows**, **175,008 plow / 119,439 spreader observations**, and **863 review-envelope warnings** (677 / 186 / 0). Header/quarantine splits, duplicate multiplicities, engine diagnostics, distinct participation, categories and source-local/naive gap metrics must match the local aggregate evidence separately for every selected processing key. Preserve original legacy Delta versions Bronze **2**, Silver **0**, and Gold **79 buckets / 110,311 observations / 79,471 plow / 68,870 spreader**. Elapsed times are measured at runtime; local SQLite timings are not native performance predictions.

## Stop and recovery behavior

Stop at the first error, unexpected result, source/schema/owner mismatch, cancellation, timeout, truncation, insufficient budget or changed protected baseline. Save sanitized statement status/query hash/timing and the last confirmed committed stage. An unexpected response is not permission to continue. No automatic FAILED-marker write, retry, cleanup, rollback, DROP, table/view replacement or compensation is included.

Immutable uploaded originals/transports remain in place. A later separately reviewed recovery must inspect exact hashes, complete row multisets and manifest states before deciding which committed data stages to skip; never replay append into an existing middle scope. If publication is partial, report the exact created names and leave them intact. Completion of missing views or correction of any created definition requires a new explicit reviewed scope. This plan does not claim atomic three-table or three-view behavior, forced-crash recovery or concurrent exactly-once operation.

Publish only sanitized aggregates and statuses, never tokens, private workspace/warehouse/object/statement IDs, local provenance paths (including their reversible hex encoding), coordinates, vehicle identifiers or payloads. The full private plan stays outside Git. After execution, update evidence/status once in the same coherent PR or its clearly identified merged successor; do not create milestone-only PR cycles.
