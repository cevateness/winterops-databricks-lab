# Native Job trials — schema passed; legacy Gold preflight blocked

## Approved type-fix trial — stopped before deployment (2026-10-31)

From merged PR #12 / main `a202e8264c623d779efb1ec02e70819e6862bc52`, the user explicitly approved proposal `8e328347…638710` / private matrix `4986733c…f9257d`, renewing the SQL ceiling to 18 cumulative submissions. The exact code/request/package/matrix hashes matched; all six immutable SQL files remain unchanged at 189,744 bytes. All **28 fresh metadata/file readiness GETs passed**, including identity/admin membership, the existing warehouse configuration/use permission, zero active sessions/Jobs, all 11 object identities/owners/schemas/definitions, source CSV/artifact fingerprints, required ownership/parent permissions and absent destinations. Readiness is a snapshot, not a global writer lock.

| Approved preflight | Actual result | Client seconds | Complete result |
|---|---|---:|---|
| 1: corrected schema/source/quality/state guard and exact manifest | **SUCCEEDED / PASS** | 24.931 | One row / 29 columns; no truncation |
| 2: published three-week/legacy Gold baselines | **FAILED**, `UNRESOLVED_COLUMN.WITH_SUGGESTION`, SQLSTATE `42703` | 3.724 | No successful baseline result |

**The native schema guard passed:** all 59 expected columns satisfy UPPER(FULL_DATA_TYPE), strict names/counts/schema/table and zero-based positions. The same successful query reconciled **2,810 Bronze = Silver = 19 HEADER + 2,791 VALID + 0 INVALID**, returned `SKIP_VERIFIED` and matched the exact existing COMPLETE manifest, attempt 2, full timestamp and metadata/policy fingerprints. These are actual native SQL results, independent of prior offline metadata tests.

The failing baseline query's **legacy CTE** requests `plow_active_observations` and `spreader_active_observations`. Its first unresolved reference is `plow_active_observations`; fresh object metadata saved during readiness confirms that both names are absent and the actual legacy fields are **`plow_active_observation_count` / `spreader_active_observation_count`**. The V2 weekly view retains its plural names. This is a query-column mismatch, not another schema-guard failure or a reason to change published objects. No query/package/matrix correction was made during execution.

Execution stopped immediately after position 2: **two SQL submissions (one success / one failure), 28 metadata GETs, 28.655 SQL client seconds / 57.693 active seconds**. Positions 3–14, Delta-history snapshots, deployments and both Jobs runs were not reached. **Zero directories, uploads, Job creations/runs, DML, DDL, Gold changes, retries, repair, cleanup or after-failure Databricks requests occurred.** This attempt made no writes; Jobs-native zero-write reruns/postflight preservation were not exercised. No partial deployment exists to clean up.

See [sanitized statuses, outputs and evidence](ON_DEMAND_BATCH_JOB_TRIAL_RESULTS.json). Cumulative trial totals now stand at **six SQL submissions (three successes / three failures), 87 execution metadata GETs and 179.785 active seconds**; the separate initial readiness inventory remains 37 requests. Of the approved ceilings, 12 SQL slots / 22 metadata slots / 720.215 seconds are unused. They do **not** authorize continuation after this stop. A future corrected proposal must explicitly account for these consumed budgets; neither stopped matrix may be replayed.

The smallest recommended follow-up is to correct only the two legacy CTE column references in a separately reviewed, rehashed plan; keep the V2 names, pipeline and published objects unchanged. No automatic correction, retry or new proposal approval is implied. Native Jobs SQL-file scripting/parameter binding, task/result handling, both COMPLETE-only runs, timeout behavior and genuinely new-source processing/recovery remain unverified. The existing **166 offline tests passed** after the stopped attempt (zero failures/errors, 8.038 seconds); [merged-main CI](https://github.com/cevateness/winterops-databricks-lab/actions/runs/41180576063) passed before execution. Evidence/status changes are local on `feat/native-jobs-trial`; no extra PR cycle was opened, and unrelated local files are unchanged.

## Prior stopped attempts (historical)

**State before the later diagnostic and type-fix trial:** the separately approved corrected continuation also stopped at the schema assertion. Three Statement API requests had then been submitted in total (one succeeded, two failed), with **zero uploads, Jobs, runs or table writes**. The ordinal correction was not sufficient. Actual `INFORMATION_SCHEMA` rows had not yet been observed; the metadata-only diagnostic was the next proposed step. Later observed LONG/BIGINT evidence and the current successful declared-type guard supersede that uncertainty.

**2026-10-30: STOPPED_BEFORE_DEPLOYMENT_SCHEMA_GUARD_FAILED.** The user explicitly approved [the exact proposal](ON_DEMAND_BATCH_TRIAL_APPROVAL.json) from merged PR #10 / main `eaf17ffa1872dac06de1c54f06af89d5fd09195a`. The one-shot controller stopped at its second SQL statement. **No Workspace directories/files, Job or runs were created; no data/manifest DML, table/view DDL, grant/configuration change, retry or cleanup occurred.** See [sanitized execution evidence](ON_DEMAND_BATCH_NATIVE_RESULTS.json).

## Actual native execution

Fresh checks matched the pinned code/request/package, authenticated workspace/administrator identity, existing serverless PRO / 2X-Small warehouse configuration and use permission, 11 object identities/owners/schemas/view definitions, target-name/path absence, Shared parent permission and Volume ownership. Remote original CSV and JSONL fingerprints/sizes matched. The separately approved corrected active-run request (`limit=20`) succeeded with no active runs and no pagination. These **28 metadata/file GET operations** passed; no failed request was automatically repeated.

| Approved Statement API request | Actual result | Client seconds | Returned rows |
|---|---|---:|---:|
| Compound BEGIN/END + bound named-marker probe | SUCCEEDED / assertion passed | 8.203 | 1 |
| Combined source/schema/content/quality/COMPLETE guards | FAILED / schema assertion | 19.956 | No successful result |

The error was `BAD_REQUEST`, with sanitized runtime message: `[USER_RAISED_EXCEPTION] V2 target schema contract mismatch SQLSTATE: P0001`. Both requests returned HTTP 200; the second failed at the SQL statement layer. There were no SQL cancellations or transport failures. Summed SQL client time was **28.159 seconds**; active trial elapsed time was **57.345 seconds** of the approved 900. Startup/transport and local controller work are included; no billing/CPU profile was collected.

The engine/API probe establishes compound-script and named-marker support through Statement Execution. **It does not establish SQL-file Jobs task execution.** The live COMPLETE snapshot, successful source reconciliation, Gold reads, Delta-history baselines, uploads, Job creation, both runs and all postflight preservation checks were not reached. The combined failed statement provides no successful reconciliation outputs; do not infer that its other assertions passed.

No workspace modifications were submitted. Source/file and protected-object metadata checks passed **before** SQL; final row/Delta/Gold preservation verification did not run because the stop rule took precedence. Existing Gold publication evidence remains the earlier three-week result. The existing warehouse could auto-resume for the approved SQL; no explicit start or setting change was requested and no final warehouse-state observation was made.

## Local ordinal correction

The schema guard generated expected ordinal positions starting at **1**. Databricks documents `INFORMATION_SCHEMA.COLUMNS.ORDINAL_POSITION` as **zero-based**, including an example beginning at zero. The already-returned Unity Catalog API metadata also positions each table's first column at zero. [The official definition](https://docs.databricks.com/aws/en/sql/language-manual/information-schema/columns) justified correcting the documented expectation, but that did not establish the actual cause of the native mismatch. No diagnostic inventory has run, and the corrected continuation still failed.

`batch_sql.py` now renders zero-based expected ordinals. The SQLite metadata fixture now models that documented contract; fixed first/interior/last schema anchors and a negative one-based fixture prevent the original assumption from being accepted. Name/type/count/order checks remain enforced. V2 transformations, source identities, row multiplicity, quality policy, `TIMESTAMP_NTZ`, manifest transitions and Gold definitions are unchanged.

At that correction milestone, **157 offline tests passed**, zero failures/errors, **7.540 seconds** (the previous 155 plus two ordinal-contract regressions). Syntax, fixture, renderer, package/hash and public-privacy checks passed. A separate synthetic execution of the proposed combined continuation returned all 29 guard/audit fields and rejected a conflicting manifest policy. These offline checks did not establish a native pass; the subsequent approved attempt below failed the same assertion.

The approved package, original 16-statement matrix and one-shot result remain immutable/private. The original public approval proposal is preserved byte-for-byte at SHA-256 `1b8e8e4ef87852409b3ac345dc48ad791e1713be0a7cd5ed8509e9606e1f9cff`; its original AWAITING status is historical proposal text, while this report records the subsequent user approval and outcome. Do not replay it against corrected code or overwrite its private package.

## Corrected continuation — approved, then stopped

The corrected private package contains the same six SQL code files, now **189,544 bytes**, with a new per-file hash set. Source request digest remains `4222da72f52c8699baf731fe01fbad7fbd8391615c1ae0f46b896380d38f966d`; code/file hashes must also match because this digest identifies source/policy inputs, not implementation bytes. New review files are under private `batch_v1/review_zero_based_20261030`, and the new statement matrix is under `batch_v1/trial_zero_based_20261030`.

[The exact corrected continuation](ON_DEMAND_BATCH_TRIAL_CONTINUATION.json) was separately approved at fix commit `85f8024c500c029b02f94c0db06941537cf584ec`; its reviewed proposal is preserved at SHA-256 `87915d4910cbfe45826d689fe48cec483b0bdbe3c5cf3547b574529630d292ee`. It reused the successful probe and combined the corrected source/schema/quality guard with the exact manifest snapshot, preserving all assertions. The proposed maximum was 14 new / 16 cumulative SQL requests, with 842.655 active seconds remaining from the first attempt.

All **28 fresh GET checks passed again**, including source hashes, object metadata, permissions and zero active runs. The first corrected SQL request then **FAILED** in **21.216 client seconds**, returning the same `V2 target schema contract mismatch` / SQLSTATE P0001, without result rows. The continuation stopped in **50.561 active seconds**. No additional statements, uploads, directories, Jobs, runs or recovery actions followed.

Execution-phase totals are **3 SQL requests (1 passed / 2 failed), 56 metadata GETs, 49.375 SQL client seconds and 107.906 active seconds**. The earlier 37 readiness GET/HEADs are a separate pre-approval phase. Thirteen slots remain under the cumulative 16-request ceiling and 792.094 active seconds remain under 900, but unused slots do not authorize another query after the stop rule. Neither approved attempt observed the live column inventory or successful source/manifest/Gold reconciliation; no Jobs entrypoint or final preservation checks ran.

## One observational diagnostic — not executed

The available error identifies a failed assertion, not the actual differing fields. The zero-based expectation matches current documentation and the UC API positions, but the actual `INFORMATION_SCHEMA` names, types, ordinals and counts are still unknown. No additional type alias, index normalization or visibility assumption has been applied to make the guard pass.

`BatchSql.schema_diagnostic()` renders [one metadata-only SELECT](../sql/batch_schema_metadata_diagnostic.sql) against the three development names in `workspace.information_schema.columns`. It returns expected versus raw actual `DATA_TYPE`, `FULL_DATA_TYPE`, ordinal and name values, missing/extra/type/position flags, and the exact guard counts. Case-insensitive lookup exposes casing differences while a separate exact-filter relation reconstructs the unchanged guard predicates. The strict guard and all six Job SQL file bytes remain identical to the approved zero-based package; only the observational method was added.

**161 offline tests pass**, zero failures/errors, **8.157 seconds**, including complete metadata results, missing/extra columns, type/position/casing evidence, zero-write behavior and generated-file consistency. The alias/casing examples in tests are synthetic and are **not native findings**. CI is assessed at the final PR head. No diagnostic SQL has run.

The [new proposal](ON_DEMAND_BATCH_SCHEMA_DIAGNOSTIC_APPROVAL.json) permits **one** Statement API request, at most three identity/warehouse permission GETs, a 120-second diagnostic deadline, 30-second wait/CANCEL, 45-second SQL client deadline and 200 rows/65,536 bytes. It returns metadata only, makes no uploads/Jobs/writes and stops after recording the result; it does not resume the guard or deployment. Its successful submission would be the fourth of the cumulative 16 SQL requests. Inspect the actual differences before deciding on another code correction or native scope.

**Native new-source processing remains unverified and is not ready for approval from this evidence.** Even a successful future COMPLETE-skip trial would not validate native append/recovery branches. The next milestone is the single observational schema diagnostic, after explicit approval. The existing PR carries both stopped outcomes, instrumentation and tests; no separate documentation-only PR is needed.
