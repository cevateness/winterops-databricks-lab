# First native Job trial — stopped before deployment

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

## Local correction, not a native retry

The schema guard generated expected ordinal positions starting at **1**. Databricks documents `INFORMATION_SCHEMA.COLUMNS.ORDINAL_POSITION` as **zero-based**, including an example beginning at zero. The already-returned Unity Catalog API metadata also positions each table's first column at zero. This is a definite implementation contract error; [the official definition](https://docs.databricks.com/aws/en/sql/language-manual/information-schema/columns) supports the correction. No diagnostic SQL was run after the failure, so further native issues remain possible.

`batch_sql.py` now renders zero-based expected ordinals. The SQLite metadata fixture now models that documented contract; fixed first/interior/last schema anchors and a negative one-based fixture prevent the original assumption from being accepted. Name/type/count/order checks remain enforced. V2 transformations, source identities, row multiplicity, quality policy, `TIMESTAMP_NTZ`, manifest transitions and Gold definitions are unchanged.

**157 offline tests passed**, zero failures/errors, **7.540 seconds** (the previous 155 plus two ordinal-contract regressions). Syntax, fixture, renderer, package/hash and public-privacy checks passed; exact-commit CI is recorded in the final implementation PR. A separate synthetic execution of the proposed combined continuation returned all 29 guard/audit fields and rejected a conflicting manifest policy. These checks verify the correction offline, not the native corrected guard or Jobs execution.

The approved package, original 16-statement matrix and one-shot result remain immutable/private. The original public approval proposal is preserved byte-for-byte at SHA-256 `1b8e8e4ef87852409b3ac345dc48ad791e1713be0a7cd5ed8509e9606e1f9cff`; its original AWAITING status is historical proposal text, while this report records the subsequent user approval and outcome. Do not replay it against corrected code or overwrite its private package.

## Prepared continuation — separate approval required

The corrected private package contains the same six SQL code files, now **189,544 bytes**, with a new per-file hash set. Source request digest remains `4222da72f52c8699baf731fe01fbad7fbd8391615c1ae0f46b896380d38f966d`; code/file hashes must also match because this digest identifies source/policy inputs, not implementation bytes. New review files are under private `batch_v1/review_zero_based_20261030`, and the new statement matrix is under `batch_v1/trial_zero_based_20261030`.

[The exact corrected continuation](ON_DEMAND_BATCH_TRIAL_CONTINUATION.json) reuses the successful compound probe. It combines the corrected source/schema/quality guard and the exact manifest snapshot into one one-row SELECT, preserving all assertions, counts, hashes and full-precision timestamp fields. All subsequent Gold, history and after-run manifest checks are retained. This leaves **14 new Statement API requests**, keeping the **cumulative cap at 16 including the failed request**. The original 57.345 active seconds leave **842.655 seconds** within the same cumulative 900-second allowance; approval/engineering waiting is excluded.

Fresh identity/permissions/conflict/source checks are needed before continuation. The new proposed metadata allowance is **50 GET/HEADs**, or **78 cumulative** including the first trial's 28; this renewed allowance is explicit and not automatic retry authority. Upload/Job/run budgets are unused: at most six non-overwriting SQL-file uploads and two necessary directories, one create-only Job, and two sequential `complete_only` runs. Table/manifest DML, table/view DDL, record-bearing uploads, schedule, retries, repair, new compute, grant/warehouse changes, Gold changes and cleanup remain excluded. Request and task deadlines remain unchanged.

**Native new-source processing remains unverified and is not ready for approval from this evidence.** A successful future COMPLETE-skip trial would still not validate native append/recovery branches. The next milestone is to review/merge the ordinal fix and obtain explicit approval of the corrected continuation; stop again at the first unexpected result.
