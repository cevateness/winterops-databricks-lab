# Workspace import recovery — conditional continuation

**2026-11-01: PREPARED LOCALLY; NOT APPROVED OR EXECUTED.** Continue PR #13 from `a6e0a4d00130f158b3cf9cd2b96382d1191b5f7d`. No new Databricks workspace/API requests, authentication, uploads or Jobs ran during this preparation. Public documentation retrieval and GitHub CI are separate from workspace execution. The original package, matrices and execution evidence are unchanged.

## API review and response correction

The official [import reference](https://docs.databricks.com/api/workspace-files/v1/import) lists RAW and explains that `overwrite=false` rejects an existing destination; its retrieved text does not prescribe an empty success body. [Get-status](https://docs.databricks.com/api/workspace-files/v1/get-status) returns absolute path, object type and unique object ID, with optional file size; an absent path produces `RESOURCE_DOES_NOT_EXIST`. [Export](https://docs.databricks.com/api/workspace-files/v1/export) supports RAW and returns base64 content when `direct_download=false`, with optional `file_type` metadata.

The saved native HTTP-200 response contains exactly one positive integer `object_id`. That is observed evidence, not a claim that the reference guarantees this import-body variant in every environment. The new pure local [validator module](../src/winterops/workspace_files.py) accepts HTTP 200 plus an empty wire body/JSON object or exactly a positive signed-int64 `object_id`. Other HTTP statuses, missing/ambiguous responses, duplicate JSON keys, malformed JSON, nonpositive/bool/string/float IDs and unknown/error fields stop. HTTP 201/202/204 are deliberately outside this narrow reviewed contract. The future transport must preserve raw response JSON or decode it strictly; it must not discard duplicate-key evidence.

Import acknowledgement always has `content_verified=False`. It never permits adoption by itself. `verify_existing_file(...)` produces an immutable **REUSE / no import / no overwrite** decision only after both exact get-status identity and RAW export length/hash pass. Errors use fixed codes; IDs and response contents stay out of public reports. No SDK or new dependency was introduced.

**186 offline tests passed**, zero failures/errors, **7.546 seconds** (170 existing + 16 new response/reuse regressions). Coverage includes both acknowledgement variants, unsuccessful/ambiguous outcomes, file/path/type/ID/size mismatches, invalid/truncated/corrupt exports, directory preservation, incomplete Job listings and combined reuse-only decisions. Syntax, aggregate fixture and all SQL/Job render checks passed locally. Exact-commit GitHub CI must pass before approval/execution; its final run link is recorded in the same PR and completion report, without changing frozen review artifacts afterward.

## Existing file and directories — future read-only recovery gate

The existing Job path is `/Workspace/Shared/winterops_on_demand_v1/4222da72f52c8699baf731fe01fbad7fbd8391615c1ae0f46b896380d38f966d/preflight.sql`. The exact Workspace **API** path omits the `/Workspace` prefix. There is no fuzzy/suffix/case-insensitive path match.

1. Get-status both existing parent/request directories; require their exact API paths and `DIRECTORY` type and pin their current IDs. Do not call mkdirs, delete or replace, even idempotently. Verify their pinned identities again at final preservation.
2. Get-status the exact `preflight.sql` API path; require `FILE` and the same positive object ID returned by the saved import. The real ID is bound in the private operation plan and omitted here. If status supplies `size`, it must also agree.
3. RAW-export that same exact path with `direct_download=false`. Require strict/canonical base64, **42,883 decoded bytes** and SHA-256 **`b4fb88bb236c8d137d843ec8e04c36a16cfb860540d5768c47ac7896c390d9b1`**. No newline normalization or content conversion is allowed. Only then reuse the file; **zero repeat imports and zero overwrites** of this path.
4. Require the remaining five exact destinations to return 404 / `RESOURCE_DOES_NOT_EXIST`, not a permission/error/unknown response. Require a complete, unpaginated, empty listing for the exact Job name `WinterOps on-demand V1`. A conflict stops; do not adopt an unexpected object, existing Job or additional uploaded file.

**Remote verification has not been attempted.** The previous import acknowledgement is not promoted into a successful content-verification result by these local tests.

## One future continuation, only after explicit approval

Approve the exact reviewed code commit plus the proposal, SQL matrix and metadata-operation digests. The [machine-readable proposal](ON_DEMAND_BATCH_WORKSPACE_RECOVERY_PLAN.json) pins all file/code hashes, paths, response gates, SQL lineage and resource bounds.

1. Perform 29 fresh metadata/file checks: identity, warehouse/configuration/use, zero active Jobs/sessions, all 11 protected object contracts, source fingerprints and ownership/parent permissions, plus the recovery/absence gates above. Preserve the existing directories and file.
2. Execute four read-only SQL checks: Bronze/Silver/manifest latest histories must still equal **3 / 4 / 13**, then verify the unchanged three-week/legacy Gold baselines. All identities/schemas/definitions and source fingerprints must match. With those anchors unchanged, reuse the previous successful full source/schema/quality/COMPLETE-manifest evidence and exact manifest row as the comparison seed. Do not repeat the completed 31-KB source guard, diagnostic or compound probe. Any version/lineage mismatch stops rather than expanding to a new source or silently revalidating a different snapshot.
3. Upload only `bronze.sql`, `silver.sql`, `quality.sql`, `complete.sql`, `failure_audit.sql`: **five files / 146,861 bytes**, all with RAW / `overwrite=false`. Validate each acknowledgement, then get-status and RAW-export it, requiring its exact path, `FILE` type, positive/pinned ID, decoded size and original SHA. All six files must be verified before Job creation. Preserve the immutable original package (six SQL files / 189,744 bytes; unchanged Job/request settings and eight payload hashes).
4. Create the one unscheduled Job, verify exact settings and run `verify` / `recovery=deny` once. Require normal tasks SUCCESS, failure audit EXCLUDED, `SKIP_VERIFIED` / `COMPLETE_ELIGIBLE` and complete expected outputs. Run the original after-run-1 history/manifest checks. Require unchanged versions and exact full manifest.
5. Before run two, get-status/RAW-export all six files again and require pinned identities and original bytes/hashes. Run `process` / `recovery=deny` once under the unchanged `complete_only` policy, then run the original final history/manifest/Gold checks. Finish fresh protected-object/source/warehouse/Job settings, all six file identities/hashes and both directory identity checks. No publication or broadened Gold selection is permitted.

All **13 SQL strings are unchanged** from the previously reviewed matrix; positions map to old matrix positions `[3,4,5,2,6,7,8,9,10,11,12,13,14]`. New positions 1–4 are the predeployment SQL gates; 5–8 follow run one and 9–13 follow run two. All statements remain read-only. The original passed source guard is reused only under the strict unchanged-version/identity gates above; Jobs preflight also rechecks the selected COMPLETE scope as before.

| Resource | Already consumed | Proposed new maximum | Proposed cumulative ceiling |
|---|---:|---:|---:|
| SQL submissions | 11 | **13** | **24**, renewal from 20 |
| Execution metadata/file GETs | 115 | **81** | **196**, renewal from 137 |
| Active execution seconds | 257.371 | **642.629** | **900**, unchanged |
| Code imports / bytes | 1 / 42,883 | **5 / 146,861** | **6 / 189,744** |
| Directory creations | 2 | **0** | **2**, unchanged |
| Jobs / runs | 0 / 0 | **1 / 2** | Same |

The 81 metadata/file GETs are enumerated and hash-pinned: **29 readiness + 10 new-file status/exports + 1 created-Job settings + 12 checks before run two + 29 final preservation checks**. They include file-content verification before both runs and after completion; they are not hidden in Job polling. Separate caps remain 90 Job-state GETs (at least five seconds apart) and 10 task-output GETs. The historical 37 initial-readiness requests remain recorded separately. Unused old budgets confer no authority to continue after a stop; this requires renewed SQL and metadata approval, without increasing the 900-second cumulative active limit.

Keep 30-second wait/CANCEL, 45-second SQL client deadline, 200 rows/65,536 bytes; metadata deadline 30 seconds / 1 MiB JSON response bound. Approved source-byte hash streams retain their exact original size bounds. Upload caps remain 256 KiB/file / 1 MiB total. Job/task limits remain 600/90 seconds, max concurrent runs 1, queue disabled, zero retries and at most 11 SQL-file task executions. All requests must fit the remaining whole-trial deadline, reserving time for at most one cancellation of a known active run. A readiness snapshot and Job concurrency setting are not a global writer lock; require no concurrent external writers.

**No Bronze/Silver/manifest DML, table/view DDL, Gold changes, new compute, scheduling, grants/configuration changes, task repair or cleanup.** Stop at the first failure, ambiguity, conflict, truncation, timeout or unexpected write. Preserve partial state; never overwrite, recreate directories, re-import `preflight.sql`, retry or repair automatically. The original stopped executable/journal is historical and must not be rerun; the future approved wrapper must use the new validators and this exact partial-state-aware request plan. Native Jobs compatibility and genuinely new-source processing remain unverified.

## Review digests (UTF-8/LF for the public proposal)

- Proposal: **`4da8acafbb6283ad12a52116198cc658db90edb4316a0101c97a6b0dbe586a88`**.
- Immutable private SQL matrix: **`ecf753ee6146875099bb630858fe20fa5bf3c53dba3829d5cbd14d3401fd6e61`**.
- Immutable private metadata-operation plan: **`22d0f622f744c1d2ef4b802d73b8c1ba8ab150ed6037a24fa7fd0a5cdd62758a`**.
