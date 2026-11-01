# Optional AUTO metadata correction and conditional continuation

**2026-11-01: LOCAL FIX / PREPARED PROPOSAL / NOT APPROVED OR EXECUTED.** Based on canonical main `337d3357ad4a052f6025f45b9b6b3b65f040fc30`, on `fix/optional-auto-export-metadata`. No Databricks authentication, workspace/API/SQL requests, uploads or Job execution occurred during this correction. GitHub CI and local replay are separate from native execution. Original execution evidence, approved plans and six-file SQL/Job package remain unchanged.

## Exact correction and regression evidence

In [verify_file_export](../src/winterops/workspace_files.py), a present optional `file_type` must still be a string with length at most 64. Its lower bound changes from one to zero: **`file_type=""` means unspecified metadata**. Missing and nonempty string values continue to work. Non-string values and lengths above 64 still fail. Exact HTTP 200, response fields, requested format/path, FILE/saved identity, strict canonical base64, decoded size and SHA-256 checks are unchanged. No other runtime function, SQL, transformation, source/policy, manifest or Gold logic changes.

The original stopped AUTO response is retained privately and frozen as a regression fixture outside Git. The full **`verify_existing_file()`** contract now passes against that saved native get-status/export pair: exact path, FILE, original saved object ID, **42,883 decoded bytes** and SHA-256 **`b4fb88bb236c8d137d843ec8e04c36a16cfb860540d5768c47ac7896c390d9b1`**. It returns **REUSE / `import_required=False` / `overwrite=False`**. Fourteen altered private-fixture cases fail, covering incorrect types, excessive metadata length, unexpected/partial fields, malformed or truncated base64, different content, changed identity/type/path. No private response contents, object IDs or paths enter public tests or logs.

Three public synthetic tests cover optional metadata boundaries, the complete reuse decision and retained integrity/identity rejection paths, including duplicate JSON keys and unsuccessful HTTP. **193 offline tests passed, zero failures/errors, 7.775 seconds.** Syntax, aggregate fixture, all five SQL renders and synthetic Job rendering pass. The original eight SQL/Job/request payload hashes are unchanged and match offline rerendering. These results prove a local response-contract correction; they are not a newly executed native validation or deployment. Exact correction commit and CI links belong in the PR/completion report without changing frozen proposal digests afterward.

Private replay digests, bound in the proposal:

- Saved native fixture: `77f4c8e1fb037eed8cab454f9b03c3610d39aa131d318bbe5bc337b013667018`.
- Complete-contract regression result: `fa4e834a62c03a2b2c4cef53b3de2ddb70f4e89894b3cdae31f89cc71d8801b1`.

## One future conditional execution, only after fresh explicit approval

Approve the exact correction commit, its successful CI, [machine-readable proposal](ON_DEMAND_BATCH_OPTIONAL_METADATA_PLAN.json), private SQL matrix and metadata-operation hashes. The native state is still one accepted `preflight.sql`, two existing directories, **no Job and no runs**. Saved-response success does not establish that remote bytes are unchanged today. The first existing-file export below is a necessary freshness/integrity check, with no separate format-discovery probe. There are no repeated schema diagnostics, compound probes or full source guards.

1. Perform **29 ordered fresh readiness GETs**: same `winterops` identity/workspace; exact existing `preflight.sql` FILE/saved identity and one AUTO / `direct_download=false` export with the pinned size/SHA; warehouse/use/configuration and zero active sessions/runs; 11 protected objects; unused exact Job name; both existing DIRECTORY paths/identities; five other destinations absent; original/transport source fingerprints; Volume ownership and relevant parent/warehouse permissions. Every path/ID is pinned in the private plan. Require no external concurrent writer. Stop on a conflicting, unsupported, partial or ambiguous result; never adopt a different object or retry/fall back.
2. Execute the four unchanged predeployment SQL statements sequentially: Bronze/Silver/manifest latest Delta histories must equal **3 / 4 / 13**, then check three-week and legacy Gold baselines. With matching fresh source fingerprints, object identities/schemas/definitions and histories, reuse the prior successful full schema/source/quality/COMPLETE-manifest evidence and exact full manifest row. Any mismatch stops instead of repeating diagnostics or broadening scope.
3. Reuse existing `preflight.sql`; **no overwrite or repeat import**. Import only `bronze.sql`, `silver.sql`, `quality.sql`, `complete.sql`, `failure_audit.sql`: **five files / 146,861 bytes**, RAW / `overwrite=false`. Validate each acknowledgement, exact FILE path/identity and AUTO exported size/SHA. Verify all six code files before Job creation. Preserve both directories without mkdir/delete/replace. Keep the original six-SQL-file package (189,744 bytes), Job/request and all eight fingerprints unchanged.
4. Create the one unscheduled **WinterOps on-demand V1** Job on the existing approved warehouse and verify frozen settings. Execute `execution_mode=verify`, `recovery=deny` once. Require five normal tasks SUCCESS, failure audit EXCLUDED, `SKIP_VERIFIED` with 2,810 Bronze/Silver rows, `COMPLETE_ELIGIBLE` and all pinned output columns/values. Execute four unchanged after-run-1 history/full-manifest checks.
5. Recheck all six FILE identities/AUTO hashes, then execute `execution_mode=process`, `recovery=deny` once under **complete_only**. Run five unchanged final history/manifest/Gold SQL statements. Complete final protected-object, warehouse, source, Job settings, six-file and two-directory preservation checks. No published Gold redirection or broader source selection.

All **13 SQL statements remain byte-identical** to the previous recovery matrix. The new matrix changes only consumed/remaining active-time fields. The 81 metadata endpoints/order are unchanged; the previous three-GET AUTO diagnostic phase is folded into the single 29-GET readiness phase, with no additional probe. Content readback selects AUTO explicitly; imports still select RAW. All six files must pass freshness/integrity gates before both runs and at final preservation. Successful diagnostics are reused only under the same strict unchanged-version gates, not assumed fresh from old evidence.

| Resource | Actually consumed | Proposed additional maximum | Proposed cumulative ceiling |
|---|---:|---:|---:|
| Statement API submissions | 11 | **13** | **24**, unchanged |
| Execution metadata/file GETs | 137 | **81** | **218**, renewal from 215 |
| Active execution seconds | 279.236 | **620.764** | **900**, unchanged |
| Code imports / decoded bytes | 1 / 42,883 | **5 / 146,861** | **6 / 189,744** |
| Directory creations | 2 | **0** | **2**, unchanged |
| Jobs / runs | 0 / 0 | **1 / 2** | Same |

The prior 215 ceiling leaves only 78 metadata GETs. This proposal explicitly requests **three more cumulative GETs** to retain fresh identity/status/content checks plus every original preservation check: **29 readiness + 10 new-file checks + 1 created-Job settings + 12 before-run-2 checks + 29 final checks = 81**. No hidden diagnostic is added. Historical 37 initial-readiness requests remain separate; 90 Job-state and 10 task-output GET caps remain separate. Unused earlier allowance is not permission to execute after a stop. The remaining active time includes fresh authentication and all approved operations, with no clock reset.

Retain **30-second SQL wait/CANCEL, 45-second SQL client deadline, 200 rows/65,536 bytes**; metadata deadline 30 seconds / 1 MiB JSON. Exact source-stream size bounds, 256 KiB/file / 1 MiB total SQL upload caps, 600/90-second Job/task timeouts, concurrency one, queue disabled, no schedule, zero retries, at most 11 SQL-file task executions, polling at least five seconds apart, and at most one cancellation of a known active run remain. Every call must fit the remaining deadline with cancellation reserve; insufficient time stops rather than enlarging the budget. Two successful runs are not guaranteed within this hard ceiling.

**Zero Bronze/Silver/manifest DML, table/view DDL, Gold changes, new-source processing, record-bearing uploads, new compute, grants/warehouse changes, directory creation, preflight reimport, overwrite, repair or cleanup.** Stop on the first error, mismatch, timeout, cancellation, unexpected write or response and preserve partial state. Native Jobs SQL-file/result compatibility and no-write reruns remain unverified; genuinely new-source processing is outside this proposal. Historical stopped executors/journals are immutable and must not be replayed.

## Exact review digests

- Proposal (UTF-8/LF): **`9e2b006be614ba50b86acf3c706207f27b56e73fe1e3848be51b93853b872511`**.
- Immutable private SQL matrix: **`17ee67ef456ab606845ff5394b880b2a813019f93f73ee717ae114ba95aede07`**.
- Immutable private metadata-operation plan: **`6f317e80b34650928f839fb378e1b45473df128fe9c829a82b8abd686d1f6374`**.
