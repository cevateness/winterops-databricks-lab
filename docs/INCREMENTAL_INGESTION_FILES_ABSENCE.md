# Incremental V1 — Files API absence correction and conditional continuation

**LOCAL FIX PASS; CONTINUATION NOT APPROVED OR EXECUTED.** Continue PR #15 from `b244f7f15cd4ec623818bd039fdc5811bd0c8f36`. No workspace authentication, inspection, SQL, upload, directory, Job or data request ran during this preparation. The [stopped execution evidence](INCREMENTAL_INGESTION_NATIVE_RESULTS.json) and [original plan](INCREMENTAL_INGESTION_NATIVE_PLAN.json) remain immutable. The user must review the exact correction commit/CI and [new conditional plan](INCREMENTAL_INGESTION_FILES_ABSENCE_PLAN.json) before any new native request.

## Narrow correction and evidence

`workspace_files.validate_absent_volume_file()` requires GET on exactly `/api/2.0/fs/files` plus the caller-pinned canonical `/Volumes/<catalog>/<schema>/<volume>/<file>` path, integer HTTP 404, a bounded JSON error object and `error_code=NOT_FOUND`. It never infers absence from status or message wording. The runner additionally limits the expected path to the two original approved CSV/gzip destinations. The existing `validate_absent_destination()` Workspace function is unchanged, including its `RESOURCE_DOES_NOT_EXIST` requirement; all other pre-existing module code is unchanged.

The official [Files API](https://docs.databricks.com/api/files/v2/file) separates file and directory endpoints and uses absolute Volume paths. The [error contract](https://docs.databricks.com/api/workspace/errors) makes `details` optional, allows an empty array and permits ignoring unknown typed details; it distinguishes resource `NOT_FOUND` from `ENDPOINT_NOT_FOUND` and treats messages as informational. Accordingly, the validator accepts absent/empty details and well-formed unrelated typed details. Every supplied `google.rpc.ErrorInfo` must contain **`reason=FILES_API_FILE_NOT_FOUND` / `domain=filesystem.databricks.com`**; conflicting or incomplete ErrorInfo fails. Optional ErrorInfo metadata must be a string map. This reason/domain pair is supported by the saved native response; it is not inferred from HTTP 404. [Official error classes](https://docs.databricks.com/aws/en/error-messages/error-classes) also identify the Files API missing-file condition.

Wrong request paths/methods/endpoints, unexpected status/codes, endpoint/permission errors, duplicate JSON keys, non-finite JSON values, malformed/ambiguous structures, invalid details and conflicting ErrorInfo fail closed. Message text is not parsed. No fallback, retry, overwrite, import or state mutation exists in this pure validator.

The saved response is a **private** regression fixture, SHA-256 **`b83ecdc053afa08c45af385da7564d3e7fec30718df6ae246cc2675961598f13`**. Offline verification accepts it for the exact pinned Files requests and confirms the old Workspace validator still rejects it. This proves response compatibility locally, not current remote destination absence. Twelve synthetic regression tests cover both file roles, optional/unknown details, error variants and negative cases. The isolated offline executor rehearsal routes **both** CSV/gzip checks to the new validator and only the Workspace-root check to the original one; no HTTP/auth transport is enabled.

**209 offline tests passed, zero failures/errors, 9.600 seconds.** Syntax for 33 Python files, aggregate fixture, all five SQL renders, synthetic Job rendering, saved-fixture checks and all immutable source/gzip/decoded JSONL/request/SQL/Job/matrix/upload-list hashes pass. The original default Job/package, transformations, policies, manifest logic, Gold selection and unrelated `.gitignore`, `.vscode/settings.json` and `databricks.yml` hashes are preserved. The stopped executor/journals and old metadata plan are preserved. Exact correction-commit CI is recorded in PR #15 and the completion report.

## Revised bounded execution request

Previous actual consumption is **18 metadata GETs / zero SQL / 18.517 active seconds**, with zero remote mutations or runs. This proposal repeats all 19 readiness checks because destination/source absence, writer state, permissions and preservation anchors must be fresh before mutation. It does not repeat a standalone diagnostic or any previously executed SQL: no SQL was reached.

| Resource | Already consumed | Additional requested | Cumulative ceiling |
|---|---:|---:|---:|
| Metadata/file GETs | 18 | **86** | **104** |
| Read-only Statement API submissions | 0 | **23** | **23** |
| Active execution seconds, including auth/uploads/checks | 18.517 | **1,181.483** | **1,200** |
| Job-state / task-output GETs | 0 / 0 | **180 / 15** | **180 / 15** |
| Original CSV + gzip uploads / bytes | 0 / 0 | **2 / 10,888,721** | **2 / 10,888,721** |
| SQL code imports / bytes | 0 / 0 | **6 / 190,473** | **6 / 190,473** |
| Volume parent PUTs / maximum new directories | 0 / 0 | **2 / 4** | **2 / 4** |
| Workspace mkdirs / Job creates / sequential runs | 0 / 0 / 0 | **2 / 1 / 3** | **2 / 1 / 3** |

**Explicit renewal required:** 18 consumed + 86 fresh GETs = **104 cumulative**, 18 above the original 86-GET ceiling. Remaining unused allowances do not authorize continuation. The active ceiling is not increased: 18.517 + 1,181.483 = 1,200 seconds. State/output GETs remain separate and have not been consumed. All other bounds and protections are inherited unchanged from the original frozen plan.

After separate explicit approval, execute the same conditional sequence:

1. Verify exact reviewed commit/green CI, original and new plans, corrected code, private executor/metadata plan, unchanged SQL matrix/upload list/package and original/gzip/decoded artifact fingerprints. Perform all **19 fresh readiness GETs**: authenticated target/warehouse/permissions, no competing sessions/runs, protected schemas/views and original Job settings, distinct Job name/Workspace root unused, Volume identity and **both exact file destinations absent**. Only gates **18/19** change validator. Run the same **five read-only predeployment SQL statements** sequentially: Delta **3/4/13**, all prior COMPLETE records, zero new filename/version/processing-key rows and unchanged published Gold aggregates. Stop before mutations if any gate fails or is ambiguous. Concurrency checks are point-in-time checks, not a writer lock.
2. Only then land the two original immutable CSV/gzip files with `overwrite=false`, verify exact returned bytes/hashes, create only approved parent directories, import the six unchanged SQL files without overwrite and verify FILE identities/AUTO-export bytes/hashes. Create only **WinterOps incremental 2026-01-26 acceptance V1**, unscheduled, on the same warehouse. Preserve **WinterOps on-demand V1** and all old files/objects.
3. **Verify/deny:** require normal tasks SUCCESS, failure audit EXCLUDED, `NEW_OR_REUSE_BRONZE`, zero selected records and `VERIFIED_NOT_PROCESSED`; four external checks require unchanged **3/4/13** and Gold. Recheck the six code files before processing.
4. **Process/deny, append_missing:** require **66,850 Bronze/Silver = 26 HEADER + 66,824 VALID + 0 INVALID**, the four expected manifest transitions and COMPLETE attempt 1. Nine external checks require **4/5/17**, full new-source multisets/quality/lineage, all previous records equal their historical versions and unchanged Gold. Job SUCCESS or DML acknowledgements alone are not data validation. Recheck the code before rerun.
5. **Process/deny again:** require `SKIP_VERIFIED` / `COMPLETE_ELIGIBLE`, exact manifest and **no additional commits**, followed by the same five external SQL and final focused metadata/content checks. Gold remains three-week only. Record actual task outputs, timings, writes, preservation and any failure; do not claim predicted outcomes as observed.

Retain **30-second wait/CANCEL, 45-second SQL client deadline, 200 rows / 65,536 bytes**, metadata 30 seconds / 1 MiB, upload bounds 120 seconds/file and 180 seconds combined, original byte caps, Job/task 600/90 seconds, polling at least five seconds, concurrency one, queue disabled, zero retries and the reserved 20 seconds for at most one known-active-run cancellation. Stop on first failure, timeout, unexpected response/write or integrity mismatch; preserve partial state without repair, cleanup or recovery. Normal writes remain only the new source's **one Bronze / one Silver / four manifest commits**; a natural failure may invoke the already reviewed single own-attempt FAILED audit, never downgrading COMPLETE. No failure injection, original Job update, old-scope writes, Gold publication, DDL, new compute, schedules, grants or configuration changes.

## Exact review fingerprints

- New conditional proposal JSON, UTF-8/LF: **`380b00887523a9baf1df21f256082b85123185bd9b3a83bf47006c92149733b1`**.
- New private metadata operation plan: **`b25d44df7c35e99bdf0ac5d6cac15bf70eef471e4bb7704d52087adf47e52eda`**. Exactly two gate values change; endpoints, order and all other operations are identical.
- Private continuation executor: **`a93d885cdaadc26c17b904a788352d46bbeaa1a28971faceba67bc3bfcadd451`**. Prepared only; never run. Approval requires the exact reviewed commit and plan hash before authentication; the one-shot journal is separate from the preserved stopped attempt.
- Unchanged SQL matrix: **`3eb5830b2232daf8a7b7ebf5794b17683695baa67944ae9f0a6a51ca0c81b404`**.
- Unchanged upload list: **`25d9278e168ae8e82286e37095d49cbf3fb810f746fcf2475f6ee819452356f6`**.
- Original proposal: **`7489c5a8e971a79723070d7f0b9b2c353c2191bc76d1b9b1a427d5aa51c78d4a`**. Source identities, all eight SQL/Job/request payload hashes and the new code hashes are pinned by the new plan plus this preserved base plan.

**Native status remains:** no incremental Job created, all three runs unsubmitted, current data/manifest/Gold baselines unqueried since the stopped attempt. Native append_missing execution, first-attempt completion, rerun stability, runtime performance and failure auditing remain unverified. Source-local/naive timestamps and observation-count interpretations are unchanged.
