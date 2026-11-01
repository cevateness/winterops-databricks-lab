# Workspace FILE AUTO export — conditional continuation

**2026-11-01: PREPARED LOCALLY; NOT APPROVED OR EXECUTED.** Continue PR #13 from `098585824bc292376e387b15d279b141c7961f32`. This correction changes content readback only. No Databricks authentication, workspace request, SQL, upload or Job ran during preparation. Original proposals, matrices, SQL packages and native evidence remain unchanged.

The official [Workspace Export reference](https://docs.databricks.com/api/workspace-files/v1/export) describes case-sensitive `format=AUTO` as selecting the representation from the object type. With `direct_download=false`, the response contains base64 `content` in JSON, with optional `file_type`. This supports an explicit AUTO test; native compatibility and byte equality remain unverified. The [last native evidence](ON_DEMAND_BATCH_WORKSPACE_RECOVERY_RESULTS.json) proves exact FILE metadata and unsupported RAW export, with no content verification or reuse.

The pure [validator](../src/winterops/workspace_files.py) now accepts explicitly selected AUTO or RAW JSON exports. The historical RAW-only entrypoint stays strict. This new plan selects **AUTO for every content readback**; imports remain RAW / `overwrite=false`. There is no HTTP client, format negotiation, fallback or retry in the module. Exact request path, FILE type and saved positive object identity must pass independently. Strict HTTP 200, JSON shape, canonical base64, decoded byte count and SHA-256 remain mandatory. Unknown fields, partial/paged responses, unsupported formats, malformed content or missing responses stop. Optional status size must match; decoded size is always required. No newline normalization or representation conversion is allowed.

## First gate: one bounded read-only AUTO test

New approval must bind the exact code commit, successful exact-commit CI and all three digests below. The [machine-readable proposal](ON_DEMAND_BATCH_AUTO_EXPORT_PLAN.json) pins paths, private operations and bounds. Its first phase consists of exactly three ordered GETs:

1. Confirm the same authenticated `winterops` identity/workspace using the existing approved profile/target contract. Charge authentication time to the active deadline; do not print identity, host or credentials.
2. Get-status `/Shared/winterops_on_demand_v1/4222da72f52c8699baf731fe01fbad7fbd8391615c1ae0f46b896380d38f966d/preflight.sql`. Require exact path, FILE, the original saved positive object ID pinned privately and matching size if supplied. The Job path adds `/Workspace`; the API path does not.
3. Submit **one** export GET for that exact path with **`format=AUTO&direct_download=false`**. Require **42,883 decoded bytes** and SHA-256 **`b4fb88bb236c8d137d843ec8e04c36a16cfb860540d5768c47ac7896c390d9b1`**. Use `verify_existing_file(...)` to produce REUSE / no import / no overwrite only after both response gates pass.

This phase has **zero SQL, uploads, directory writes, Jobs or runs**, at most 30 seconds/request, 1 MiB JSON/request and **90 active seconds including authentication**. It is included in the combined 81 GET / 624.150-second budget. Stop on the first failure, unsupported response or integrity mismatch. No RAW/SOURCE/direct-download/other-endpoint fallback or retry. If only this read-only test is approved, stop after recording it; that does not authorize deployment.

## Conditional continuation within newly approved combined scope

Only if the test passes and the combined scope is explicitly approved, proceed within the same attempt without reimporting `preflight.sql`. Preserve both existing directories; verify exact DIRECTORY paths and pin identities, with no mkdir/delete/replace. The remaining **26 readiness GETs** check warehouse configuration/use, zero active Jobs/sessions, 11 protected object contracts, unused Job name, other five destinations absent, exact source fingerprints, Volume ownership and parent/warehouse permissions. Absence requires HTTP 404 / `RESOURCE_DOES_NOT_EXIST`. Require no concurrent external writer; Job concurrency is not a global lock.

Execute four existing predeployment SQL checks sequentially: unchanged Delta histories **Bronze 3 / Silver 4 / manifest 13**, then corrected three-week/legacy Gold baselines. Reuse the earlier successful schema/source/quality/COMPLETE-manifest guard only if all fresh object identities, schemas, definitions, source fingerprints and Delta anchors still match its pinned evidence. Keep the exact full manifest row as comparison seed. Any mismatch stops; do not repeat the full guard, diagnostic, compound probe or stopped matrices. All **13 SQL statements are byte-identical** to the previous recovery matrix; only the active-time ledger changes.

Only after every gate passes:

1. RAW-import `bronze.sql`, `silver.sql`, `quality.sql`, `complete.sql`, `failure_audit.sql`, **five files / 146,861 bytes**, with `overwrite=false`. Validate each acknowledgement, then get-status and AUTO-export for exact FILE path/identity, decoded size and original SHA. Acknowledgement alone never proves content. Verify all six files before Job creation. Original six SQL files / 189,744 bytes, Job/request and eight payload fingerprints stay unchanged.
2. Create the one unscheduled **WinterOps on-demand V1** Job using frozen settings and existing warehouse; compare returned settings. Run `execution_mode=verify`, `recovery=deny` once. Require five normal tasks SUCCESS, failure audit EXCLUDED, `SKIP_VERIFIED` with 2,810 Bronze/Silver rows and `COMPLETE_ELIGIBLE`, with all expected output columns/values. Execute four after-run-1 history/full-manifest checks.
3. Recheck all six pinned FILE identities and AUTO-export hashes before run two. Run `execution_mode=process`, `recovery=deny` once under unchanged **complete_only**, permitting zero data/manifest writes. Execute five final history/manifest/Gold SQL checks and final protected objects, sources, warehouse/Job settings, all six files and both directories. Later scheduled preservation exports are separate planned gates, never retries of failed exports.

The stopped executable/journals remain historical. A future approved runner must explicitly select AUTO and use the new strict validators; do not rerun the old RAW executor. Native AUTO and Jobs SQL-file compatibility remain unverified. No genuinely new-source processing is proposed.

| Resource | Consumed | Additional maximum | Cumulative ceiling |
|---|---:|---:|---:|
| Statement API SQL | 11 | **13** | **24**, unchanged |
| Execution metadata/file GETs | 134 | **81** | **215**, renewal from 196 |
| Active seconds | 275.850 | **624.150** | **900**, unchanged |
| Code imports / decoded bytes | 1 / 42,883 | **5 / 146,861** | **6 / 189,744** |
| Directory creations | 2 | **0** | **2**, unchanged |
| Jobs / runs | 0 / 0 | **1 / 2** | Same |

GET allocation: **3 AUTO-test + 26 readiness + 10 new-file status/exports + 1 created-Job settings + 12 before-run-2 file checks + 29 final checks = 81**, including 18 explicit AUTO exports. After the test, at most 78 GETs and `624.150 - actual test active seconds` remain. Historical 37 initial-readiness GETs remain separate. Job-state GETs (90) and task-output GETs (10) are separate caps, not hidden content requests.

Retain SQL **30s wait/CANCEL, 45s client, 200 rows/65,536 bytes**; metadata 30s client / 1 MiB JSON. Source-hash streams retain exact approved size bounds. Upload caps stay 256 KiB/file / 1 MiB total. Job/task timeouts stay 600/90 seconds, concurrency 1, queue disabled, no schedule, zero retries, at most 11 SQL-file task executions, polling at least five seconds apart and at most one cancellation of a known active run. Every operation must fit the active deadline with cancellation time reserved. These hard ceilings do not guarantee that both runs will fit; insufficient time stops execution.

**Zero Bronze/Silver/manifest DML, table/view DDL, Gold changes, new-source processing, record-bearing uploads, new compute, grants/warehouse changes, mkdir, preflight reimport, overwrite, task repair or cleanup.** Stop on the first error, timeout, cancellation, unexpected write, ambiguity or mismatch and preserve partial state. Unused allowances are not continuation authority. New approval must renew metadata to 215 while retaining the original 900-second cumulative ceiling.

## Local evidence and review digests

**190 offline tests passed**, zero failures/errors, including four AUTO regressions covering valid base64/JSON, exact bytes, incorrect content, malformed/partial responses, unsupported formats and retained identity checks. Syntax, aggregate fixture and all SQL/Job render checks passed. Real package rerendering and matrix comparisons preserve original SQL/Job/request fingerprints. These are offline results; no native test, deployment or run occurred. Exact-head CI/commit links belong in PR #13 and the completion report without mutating frozen digests afterward.

- Proposal (UTF-8/LF): **`07db88a7ff053581c58eafd7135d1188c90c8b54e7141a65dd5f7a53c5550b94`**.
- Immutable private SQL matrix: **`920211e3d8a3edc3c512478736bf135f1958fb91a992a85b9a561aeedc6e8817`**.
- Immutable private metadata-operation plan: **`e35e1c1521c856ba6142e40746d4fe455bc1f77ac4a2d02b810cc62502ab8b1b`**.
