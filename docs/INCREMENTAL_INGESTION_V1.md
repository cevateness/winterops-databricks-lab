# Incremental ingestion V1 — January 26 acceptance

**NATIVE TRIAL STOPPED AT READINESS CHECK 18; NO REMOTE WRITES OR RUNS.** The user approved the exact PR #15 commit `25faab5c0ca6b1d22267e53c491cb9e67b5990bb` and frozen plan. The source/package/code/plan hashes and successful exact-commit CI matched. See [actual native results](INCREMENTAL_INGESTION_NATIVE_RESULTS.json). The preparation below is based on main `d658511`, branch `feat/incremental-ingestion-v1`; its predicted counts and run results are not native outcomes.

## Actual native execution — stopped without retry (2026-11-01)

Seventeen readiness gates passed: authenticated identity, existing warehouse configuration/zero active sessions, no active Job runs, three V2 table and four Gold view metadata contracts, protected original Job settings, unused acceptance Job name, Shared parent/permissions, new Workspace-root absence, Volume identity/ownership and warehouse permissions. The eighteenth GET, for the original CSV's exact immutable Files API destination, returned **HTTP 404 / `NOT_FOUND`**, with `FILES_API_FILE_NOT_FOUND` in its structured error details. The client called `workspace_files.validate_absent_destination()`, which requires the Workspace-specific `RESOURCE_DOES_NOT_EXIST`, and stopped with **`NOT_FOUND_ERROR_CONTRACT_MISMATCH`**. This is an observed endpoint-response compatibility defect in the readiness gate, not a permission denial or ingestion SQL failure. The synthetic rehearsal did not cover this Files API response variant.

**Actual usage: 18 metadata GETs / zero SQL / 18.517 active seconds.** No source/artifact/code uploads, directory creation, Job creation/runs, Bronze/Silver/manifest DML, DDL, Gold/configuration changes, retries, repairs or cleanup occurred. All three planned runs are **NOT SUBMITTED**, with no task states. The gzip destination check and all five predeployment SQL checks were not reached. The last previously verified Delta versions remain **3 / 4 / 13 as historical evidence**; neither fresh versions, selected-scope absence, manifest contents nor Gold aggregate preservation was queried in this attempt. Expected process versions **4 / 5 / 17** and 66,850 persisted rows were not observed. Protected metadata matched, and this execution made no writes; that does not establish current row-level preservation by other writers.

The original approved plan, private matrix/metadata/upload list, source files, six-file SQL/Job package and unrelated local files are preserved. **No validator correction or continuation ran.** Smallest next step: review an endpoint-specific Files API absence validator and regression cases using the saved response, retaining the strict Workspace contract and exact path/404 checks, then review a bounded continuation before further native requests. Unused capacity (23 SQL, 68 metadata GETs, 1,181.483 seconds) does not authorize resumption after this stop. No new-source native write, rerun-idempotency or performance claim is made.

Evidence update: **197 offline tests passed / zero failures or errors / 8.877 seconds**, plus syntax for 33 Python files, aggregate fixture, all SQL/Job renders and unchanged package/plan/source/user-file hashes. The initial sandbox test attempt encountered temporary-directory permission errors; the unchanged suite passed with required filesystem access. Synthetic Job rendering passed in private staging outside Git. No Databricks request occurred during documentation or offline checks. Evidence-commit CI is recorded in PR #15 and the completion report.

## Actual source and local reconciliation

The [official catalogue](https://opendata.citywindsor.ca/details/224) links the exact [January 26–February 1 CSV](https://opendata.citywindsor.ca/Uploads/snowplow-2026-01-26_2026-02-01.csv), dated February 2 on the catalogue. `windsor_history.py discover` confirmed the link; `stage` downloaded that exact HTTPS URL, HTTP 200, no redirect/substitution, `application/octet-stream`. Strict CSV parsing confirms ASCII-compatible UTF-8, no BOM, comma delimiter and the seven existing columns in order: Latitude, Longitude, Date time, Plow status, Spreader status, Engine status, Truck. All 66,850 parsed records after the outer header have seven fields.

| Local result | Observed |
|---|---:|
| Original CSV bytes | 5,272,022 |
| Bronze / Silver rows | 66,850 / 66,850 |
| HEADER / VALID / INVALID | 26 / 66,824 / 0 |
| Geographic review warnings / malformed widths / missing non-header values | 0 / 0 / 0 |
| Repeated valid-payload observations retained | 234 |
| Observed identifier strings, not fleet availability | 223 |
| Gzip transport / decoded JSONL bytes | 5,616,699 / 86,262,730 |

The nominal source period is `[2026-01-26, 2026-02-02)`. Actual valid timestamps span **January 26 00:00:00 through January 30 13:12:52**; no January 31/February 1 observations are present. Missing dates do not establish inactivity or complete recording. Keep source-local/naive `TIMESTAMP_NTZ`; timezone semantics remain unconfirmed. This activity-triggered feed's nominal 15-second cadence does not turn observation counts into work duration, coverage or productivity. The old catalogue warns of migration; the replacement route-geometry layer was not substituted.

`windsor_history.py process --export-bronze --artifact-compression gzip` reused the existing default quality policy / `windsor-foundation-v2.1`, preserved all repeated observations and headers, reconciled record identities and completed the local manifest. Full ordered hashes of every pre-existing local version/run/attempt and all **231,306 prior Bronze/Silver rows** remain unchanged. Source/staging bounds passed: 64 MiB CSV, configured 60-second acquisition bounds, 500,000 parsed records, 256 MiB decoded/transport artifact. Raw CSV, local SQLite records, full request and artifacts live outside Git. [Aggregate evidence](INCREMENTAL_INGESTION_SOURCE_EVIDENCE.json) contains the measured policy, period, diagnostics and fingerprints.

- CSV SHA-256: `cebcbd758e2a0cf5d0624ecf9cd6993244e7becdd1846a4057b4f63be22ed6c6`.
- Source version: `ad5c201ccee0b96b2f4907f10ee3a064a7562d17429146d2205b1eaca46fdc00`.
- Processing key: `9c8e1b6f640e75c21f1c9f429ec670c389bf178269afd2f1543b2ae759c3eeae`.
- Gzip SHA-256: `4aa85d0024845ab8662201127938a4ba9ec8fd23e05c282b352130952d414191`.
- Decoded JSONL SHA-256: `92b8ba14fd997620fc5ac396369b0272dada7e177ebd951cf11d6ed7f102206a`.

Attribution: Contains information licensed under the [Open Government Licence – The Corporation of the City of Windsor](https://opendata.citywindsor.ca/Documents/OpenDataTermsofUse.pdf). Public artifacts contain aggregates and synthetic fixtures, not operational identifiers, coordinates or trajectories.

## Minimal implementation and write-path review

`job_definition()` and `prepare_job()` accept an optional bounded `job_name`; the existing renderer exposes `--job-name`. The default remains **WinterOps on-demand V1**, with byte-identical old SQL/Job/request output. A name change cannot overwrite an immutable package. No task, transformation, policy, manifest or Gold logic was modified.

The private new package has **six SQL files / 190,473 bytes**, Job/request/review JSON, and request digest **`876c8aa2aa64352454d9b4ef4984e443b96257426c0ada61648d4a3c26434508`**. It pins `append_missing`, `prior_attempts=0`, actual counts and immutable CSV/gzip paths. New Job: **WinterOps incremental 2026-01-26 acceptance V1**. New Workspace root: `/Workspace/Shared/winterops_incremental_2026_01_26_v1`; generated files sit under its request-digest child. The old Job is only read for preservation, never updated or repointed.

**No `append_missing` logic defect was found in offline review.** A new synthetic fourth-source test executes verify → process → process, preserves three COMPLETE weeks, repeated payloads and HEADER/INVALID rows, observes `PROCESSING → BRONZE_WRITTEN → SILVER_WRITTEN → COMPLETE`, and confirms zero DML on verify/rerun. Existing conflict, lineage, multiplicity, failure and recovery tests remain. Named-Job tests prove unchanged default settings and immutable isolated output. The existing failure-audit comparison uses the documented lowercase [task result-state reference](https://docs.databricks.com/aws/en/jobs/dynamic-value-references). Its native failure branch remains untested; no failure is intentionally injected here.

**197 offline tests passed, zero failures/errors, 8.852 seconds.** Syntax, fixture, SQL/Job render and original-package hash checks must pass before review; exact-commit CI is recorded in the PR/report. SQLite tests adapt dialect/files/Delta and do not establish native write-path compatibility. The local manifest's attempt 1 is separate from the proposed native prior-attempt count 0. Native absence is **unverified** and mandatory before landing/deployment.

## One conditional native acceptance proposal

Review the exact commit/CI plus [machine-readable plan](INCREMENTAL_INGESTION_NATIVE_PLAN.json), immutable private package, 23-statement matrix, 86-operation metadata plan and upload-list hashes. This is a **new trial budget**, not reuse of the exhausted earlier SQL/metadata allowances. Use the existing private `winterops` workspace/warehouse bindings. No new compute, grants, configuration, schedules, table/view DDL or Gold selection changes are authorized by this preparation.

1. **Prerequisites, before any landing:** 19 focused metadata GETs check identity, warehouse/use/zero active writers, three target schemas/owners, four published Gold definitions, original Job settings, unused distinct Job name, Shared parent permissions, new Workspace root absence, Volume identity/ownership and both destination-file absences. Five read-only SQL statements require Delta **3 / 4 / 13**, three COMPLETE prior manifests / 231,306 prior rows and **zero rows for this filename/version/key in all three tables**, then capture all four Gold aggregate baselines. Any existing selected scope stops; do not adopt it as a new-source experiment.
2. **Immutable landing/deployment:** create only the two pinned Volume parent trees (two recursive directory PUTs, at most four new directories) and two Workspace directories. PUT the CSV and gzip with **explicit `overwrite=false`**, then verify exact bytes/SHA by bounded streaming GET. Files [directory](https://docs.databricks.com/api/files/v2/create-directory) and [upload](https://docs.databricks.com/api/files/v2/upload-file) acknowledgements require HTTP 204 / no content; overwrite must be explicit because the upload API otherwise permits replacement. Import six new code files, RAW/no overwrite, and get-status/AUTO-export each for exact FILE identity/size/SHA using the existing validators. Create only the new unscheduled Job, verify its settings and require its ID differ from the protected old Job.
3. **Run 1, verify/deny:** five normal tasks SUCCESS, audit EXCLUDED. Expect `NEW_OR_REUSE_BRONZE`, Bronze/Silver zero, `VERIFIED_NOT_PROCESSED`. Three history queries must remain **3 / 4 / 13**, proving no table commits; repeat all four Gold aggregate checks. Job SUCCESS alone is insufficient. Recheck six code files before run 2.
4. **Run 2, process/deny:** allow only the selected new-version Bronze insert, selected processing-key Silver insert and four selected-key manifest transitions. Although the shared SQL uses `INSERT … REPLACE WHERE`, data writes are reachable only for an empty selected scope; old scopes cannot be replaced. Expect all normal tasks SUCCESS, audit EXCLUDED and COMPLETE/attempt 1. Nine read-only postchecks require versions **4 / 5 / 17**, exact incoming/persisted Bronze/Silver **full multisets**, 66,850 rows = 26 HEADER + 66,824 VALID + 0 INVALID, correct lineage/manifest/Gold eligibility, **all prior rows in each table equal their before versions via EXCEPT ALL**, and unchanged four-view Gold baselines. Recheck code before run 3.
5. **Run 3, process/deny:** expect `SKIP_VERIFIED`, 66,850/66,850 and `COMPLETE_ELIGIBLE`. Five read-only checks require **no additional Delta commits**, exact manifest including timestamp and unchanged Gold. Final focused metadata/content checks confirm original Job settings, protected schemas/view definitions, warehouse, new Job/code/directories and both source hashes. Published V2 hourly/daily/weekly remain **236 / 20 / 3 rows and 231,227 observations**, with zero new-source rows; legacy Gold remains 79 / 110,311. New-source eligibility is SELECT-only and does not broaden publication.

| Hard limit | Proposed maximum |
|---|---:|
| Entire active trial, including auth/uploads/validation | **1,200 seconds** |
| Read-only Statement API submissions | **23** |
| Focused metadata/file GETs; separate state/output GETs | **86; 180 / 15** |
| Source/artifact uploads | **2 / 10,888,721 exact bytes** |
| SQL code uploads | **6 / 190,473 exact bytes** |
| Volume parent PUTs / Workspace mkdirs / Job creates / sequential runs | **2 / 2 / 1 / 3** |
| Normal source-scoped commits: Bronze / Silver / manifest | **1 / 1 / 4** |
| SQL-file task executions, including a possible natural-failure audit | **16** |

Keep 30-second SQL wait/CANCEL, 45-second SQL client, 200 rows/65,536 bytes; metadata 30 seconds / 1 MiB; source uploads 120 seconds each / 180 seconds combined, at most 16 MiB/file / 32 MiB total and exact listed bytes; code caps 256 KiB/file / 1 MiB total. Job/task limits remain 600/90 seconds, concurrency one, queue disabled, polling at least five seconds apart, zero retries. Reserve 20 seconds for at most one known-active-run cancellation. Every call fits the remaining whole-trial deadline; stop rather than extend bounds. The larger decoded artifact and full-multiset checks may hit native task/wait limits: actual performance remains unverified.

**Stop on the first error, timeout/cancellation, integrity/response/count/version mismatch or unapproved write.** Preserve partial files, Job and selected data/manifest state without cleanup, retry, repair or recovery. On a natural failure after attempt 1 began, the existing failure-audit task may perform **at most one additional selected-key FAILED update**, with matching metadata/policy/attempt and never downgrading COMPLETE; a preflight failure cannot write that audit. This conditional audit is part of the requested write approval. A failed Job/postcheck does not permit later phases. Serialization across all writers is an execution premise; this experiment adds no lock service.

## Review fingerprints and status

- Proposal UTF-8/LF: **`7489c5a8e971a79723070d7f0b9b2c353c2191bc76d1b9b1a427d5aa51c78d4a`**.
- Private SQL matrix: **`3eb5830b2232daf8a7b7ebf5794b17683695baa67944ae9f0a6a51ca0c81b404`**.
- Private metadata operations: **`2c7e3ebfb66fbc5d9bef1c5868b506a5358e62118ab53e0e34ea8d88349b2c38`**.
- Private record-upload list: **`25d9278e168ae8e82286e37095d49cbf3fb810f746fcf2475f6ee819452356f6`**.

Local source preparation, package rendering and synthetic acceptance are implemented. **The approved native attempt stopped before SQL or writes; uploads, the new Job and write/rerun acceptance remain unexecuted.** Existing three-week publication and the original successful COMPLETE-only Job remain the latest completed native evidence. A reviewed response-contract correction and continuation are required before another native request. No scheduling, automatic acquisition, failure exercise or new dashboard is included.
