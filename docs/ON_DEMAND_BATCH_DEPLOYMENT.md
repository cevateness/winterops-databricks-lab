# On-demand V1 — native deployment review plan

**PREPARED LOCALLY; NO APPROVAL, DEPLOYMENT OR EXECUTION YET.** This is a proposed future scope, not modification authority. [Machine-readable limits and exact file hashes](ON_DEMAND_BATCH_NATIVE_PLAN.json) pin request `4222da72f52c8699baf731fe01fbad7fbd8391615c1ae0f46b896380d38f966d`. Review the final code commit as well as that package; a change to either requires a new review. Real Jobs settings/request/SQL are private under the local WinterOps `batch_v1/review_20261030_final` directory. Public evidence omits the warehouse ID, local provenance paths, identity and private workspace URL.

## Selected source and expected results

The smallest already COMPLETE version is selected to test native orchestration without risking a new ingestion:

- Source: `snowplow-2026-01-05_2026-01-11.csv`, CSV SHA-256 `271c9339a42043f441b6c17e82dd309609db4b20e9953b9f368a95ec472d763d`, **221,818 bytes**.
- Existing plain JSONL artifact SHA-256 `375d6c5980ed66f61b2dcb0601f639f5e2a3a20ce546ac08d3e20fc60c17edd3`, **3,619,379 bytes**. Its exact immutable Volume path is derived from the selected source-version/hash in the request. No artifact upload is proposed.
- Both local files were rehashed and matched; the private local manifest is COMPLETE with **2,810 Bronze = Silver = 19 HEADER + 2,791 VALID + 0 INVALID**. These are fresh local checks, not new native checks. Native auth/object state was not rechecked in this task.
- Targets remain `workspace.default.winterops_v2_dev_bronze`, `workspace.default.winterops_v2_dev_silver`, `workspace.default.winterops_v2_dev_manifest`. The prepared `complete_only` policy cannot append absent scopes or update a failed/interrupted manifest even if `execution_mode=process` is supplied.
- Expected native outcome: preflight `SKIP_VERIFIED`, final `COMPLETE_ELIGIBLE`, all normal tasks succeed, failure audit excluded, **no data/manifest DML**. The existing source manifest attempt count/timestamp and all Delta versions must remain unchanged.

## Read-only readiness before seeking the one exact approval

Use the existing named `winterops` profile and warehouse identity pinned privately from PR #9. Recheck the account/workspace origin, authenticated identity, exact warehouse ID/type/settings, Jobs availability/quota and current USE/SELECT/MODIFY/READ VOLUME access without publishing sensitive values. Confirm no other writer is active; one Job's concurrency setting is not a global lock.

Inspect all three existing table identities/types/owners/schemas and the original CSV/transport paths. Verify the exact selected COMPLETE manifest metadata, policy, counts, attempt and full timestamp; compare full source-scoped row multisets. Reconfirm the prior three-week and legacy Gold baselines. Capture all three V2 Delta versions and selected manifest content for unchanged-after comparisons. Read-only native readiness must fail rather than guess if a target, permission or lineage is uncertain.

Confirm the proposed Job name `WinterOps on-demand V1` is absent and the six SQL destinations `/Workspace/Shared/winterops_on_demand_v1/<request-sha256>/<task>.sql` are absent. Do not adopt or overwrite an unknown Job/file. Confirm Jobs create/run permission and Workspace-file parent access. If required files/folders cannot be created in this exact path, revise the plan before approval; do not change permissions.

A bounded SELECT-only compound script can probe SQL scripting/named markers using Statement Execution before deployment. Jobs SQL-file marker binding, DAG result handling and timeout behavior remain part of the approved trial, not proven by that probe.

**Stop here and request one explicit approval** of this exact Job creation, six code-file uploads, two `complete_only` runs, existing warehouse and limits. Earlier ingestion/publication approvals do not cover Jobs deployment. No execution or permission change is authorized by this document.

## Exact deployment/run matrix, if separately approved

1. Recheck the approved request/file hashes, existing target metadata and absence of conflicting Job/files. Preserve all original datasets and unrelated user files.
2. Upload exactly six generated SQL **code** files, without overwrite, under the pinned Workspace directory (create only its necessary parent folders). Current total **189,559 bytes**; maximum 256 KiB/file and 1 MiB total. Verify uploaded content hashes. Keep `request.json`, `review.json` and real warehouse configuration private; submit `job.json` only as the Jobs create-settings payload, not as record data.
3. Create exactly one Job from the reviewed settings: existing warehouse, no new compute, `max_concurrent_runs=1`, queue disabled, no schedule/trigger, zero retries, 90 seconds/task and 600 seconds/job. Verify the returned settings and exact file paths before running. Do not reset, replace or duplicate an existing Job.
4. Run once with the pinned source/key/digest, `execution_mode=verify`, `recovery=deny`. Require complete expected scalar/aggregate outputs and task states. Validate manifest/data/Delta snapshots unchanged. If anything differs or the Job fails, stop; do not proceed to run two.
5. Reconfirm the same selected manifest remains COMPLETE. Run once with `execution_mode=process`, `recovery=deny`; the compiled `complete_only` policy must again skip every write branch. Require `SKIP_VERIFIED`/`COMPLETE_ELIGIBLE`, failure audit excluded and unchanged snapshots.
6. Final read-only checks: same original/transport bytes, manifest identity/counts/status/attempt/full timestamp, exact schemas, all three V2 Delta versions, all pre-existing object identities/definitions/grants and warehouse settings. Gold remains **236 hourly / 20 daily / 3 weekly rows**, **231,227 valid / 175,008 plow / 119,439 spreader observations**; legacy Gold remains **79 buckets / 110,311 valid / 79,471 plow / 68,870 spreader**. No published selection may change.
7. Record sanitized file hashes, request/commit, task/Job statuses, elapsed times, output completeness, logical skip decisions and unchanged-after evidence. Keep actual Job/run/statement/warehouse IDs and raw error payloads private. Report whether Jobs-native compatibility actually passed; source/native SQL evidence alone is insufficient.

## Resource bounds and stop/recovery behavior

| Resource | Hard proposed cap |
|---|---:|
| Job creation / SQL-file uploads / record-bearing uploads | 1 / 6 / 0 |
| Run-now submissions | 2, sequential; no retries or task repair |
| Job SQL-file task executions | At most 11 including a possible terminal failure audit; stop before the next run on failure |
| Read-only Statement API requests for readiness/postflight/probe | 16; 30-second wait, CANCEL, 45-second hard client deadline, 200 rows / 65,536 bytes |
| Job/task runtime | 600 / 90 seconds, separately enforced by Jobs |
| Entire active trial client deadline | 900 seconds, including uploads, Jobs and verification; approval waiting excluded |
| Job-state GETs | At most 90, no more often than every 5 seconds; bounded requests |
| Table data/audit DML or table/view DDL | **0** |

Statement API bounds do not automatically apply to inner statements in a Jobs SQL script. The task/job deadlines bound those scripts. Stop on the first failure, cancellation, timeout, unknown response, truncated/unexpected output, hash/lineage/version mismatch or unexpected write. Do not retry a timed-out create/run/upload; inspect only through a separately reviewed read-only continuation. If the whole-trial deadline is reached with a known active run, request cancellation of that exact run once; record the outcome and stop. Never expand quotas or change warehouse settings.

Files, Job creation and task commits are not atomic. Failure can leave verified SQL code files and/or the new Job deployed. Preserve them, report exact partial state, and obtain a concrete follow-up scope; no automatic delete, reset, cleanup or overwrite. Table writes are prohibited in this trial and the pinned policy guards them. Native processing of a new version, forced-crash recovery, task repair, concurrent-writer tests, failure injection and any future update of the deployed Job to `append_missing` require separate exact approval. Offline tests cover those processing decisions but do not replace native evidence.
