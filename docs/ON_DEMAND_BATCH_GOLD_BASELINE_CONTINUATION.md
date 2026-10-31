# Gold baseline correction — one conditional continuation

**2026-10-31: LOCAL PASS; NOT APPROVED OR EXECUTED.** Work remains on `feat/native-jobs-trial`, based on merged PR #12 / main `a202e8264c623d779efb1ec02e70819e6862bc52`. This task performed no authentication, remote SQL/API requests, uploads, deployment or Job execution. The stopped execution evidence, original approved plan/matrix and eight-file private package are unchanged.

## Correction and complete column audit

The single reviewed query source is [batch_gold_baselines.sql](../src/winterops/sql/batch_gold_baselines.sql). Both matrix positions **2 and 14** now use `plow_active_observation_count` / `spreader_active_observation_count` inside the **legacy** CTE only. All V2 plural column names, result aliases, ordering and expected values remain unchanged. The other **12 SQL strings are byte-identical** to the stopped matrix. No legacy/V2 view definition, transformation, schema guard, source version, policy or Job SQL changed.

[The audit](ON_DEMAND_BATCH_MATRIX_COLUMN_AUDIT.json) covers **all 14 statements**: five SELECTs bound through SQLite's compiler/authorizer and nine Delta-history requests checked against the three exact V2 table contracts. The fixture instantiates the actual legacy views from `gold_hourly.sql`/the existing analytics renderer, all three V2 views from `UnifiedGold`, and Bronze/Silver/manifest columns from their existing type contracts. Information-schema columns use the existing batch fixture. It records every source column read, including expanded view dependencies. Both referenced Gold view column lists also match the fresh native metadata saved before the stopped trial. No record-bearing native data is loaded into this audit.

Four regression tests independently verify the different legacy/V2 naming contracts, execute the corrected cross-view baseline on synthetic observations with reconciled expected totals and no writes, and reject each naming convention in the wrong view. **170 offline tests passed**, zero failures/errors, **9.709 seconds**. Syntax, aggregate fixture, five SQL render modes and synthetic Job rendering passed; all six real Job SQL render hashes still equal the preserved 189,744-byte package. This is offline column binding/logic evidence, not new Spark or Jobs compatibility evidence. No new GitHub CI or PR cycle was triggered; exact-commit CI is required before a future approved execution.

## Frozen review artifacts

- [Continuation proposal](ON_DEMAND_BATCH_GOLD_BASELINE_CONTINUATION.json), UTF-8/LF SHA-256: **`cf4b4431c6fb26d7c8a0fb51e0af2b680f0286138016aeb6dd387aad1b14f9fe`**.
- New immutable private matrix SHA-256: **`a597db8cf73dc5f18dab944ebc3a933c23a14e1a310bbd12180bd9f18c27d975`**. Its content-addressed local path, all 14 statement hashes and package/code/audit hashes are in the proposal. The original matrix `4986733c…f9257d`, original proposal `8e328347…638710` and stopped execution evidence are preserved, never refreshed in place.
- Exactly the same source request `4222da72…f966d`, existing workspace/warehouse, COMPLETE January 5–11 version, `complete_only` policy, six code-file destinations, Job settings and task-output expectations are retained. The package's eight payload hashes and six SQL files / **189,744 bytes** are unchanged.

## Proposed execution, only after new explicit approval

1. Review/commit the final code/query/test/evidence hashes, obtain exact-commit CI success and explicit approval of this proposal/matrix and renewed bounds. Fresh metadata/file checks must confirm the same identity, warehouse/configuration/use permission, all 11 protected object contracts, Volume/parent access, source fingerprints, no active Jobs/warehouse sessions and absent deployment destinations. Stop on uncertainty, conflict or pagination.
2. Execute positions **1–5 sequentially**, with the corrected baseline at position 2. Require all assertions, exact COMPLETE manifest, expected Gold totals and all three Delta-history snapshots before **any** directory creation, upload, Job creation or run.
3. Create at most two necessary parent directories, upload the six immutable code files without overwrite and verify their hashes, then create the one unscheduled `WinterOps on-demand V1` Job on the existing warehouse. No record-bearing upload or table/view DDL.
4. Run `verify` / `recovery=deny` once; require all normal tasks successful, failure audit excluded, `SKIP_VERIFIED` / `COMPLETE_ELIGIBLE` and exact scalar outputs. Positions **6–9** must prove unchanged Delta versions and manifest before run two.
5. Run `process` / `recovery=deny` once under the unchanged `complete_only` policy. Require the same zero-write behavior; positions **10–14** must prove unchanged histories/manifest and three-week/legacy Gold baselines, including corrected position 14. Finish bounded metadata/source/settings preservation checks.

**Why a fresh position 1 is included:** its prior schema/content/manifest PASS is retained as valid historical evidence; this is not another diagnostic or investigation of the fixed schema guard. However, the run stopped before positions 3–5 captured any transactional Delta-version anchors. Object-schema equality and a COMPLETE manifest alone cannot prove that mutable table contents remain identical across the stopped run and a later continuation. One fresh reconciliation before deployment is therefore needed for safe readiness. There is no automatic repeat, optional fallback or additional first-guard request; failure stops this proposal. Skipping it safely would require a separately reviewed unchanged-version proof, which is not claimed here.

| Resource | Already consumed | Newly proposed maximum | Proposed cumulative ceiling |
|---|---:|---:|---:|
| Statement Execution SQL submissions | 6 | **14** | **20** (renewal from 18) |
| Execution metadata/file GET/HEADs | 87 | **50** | **137** (renewal from 109) |
| Job-state / task-output GETs | 0 / 0 | 90 / 10 | 90 / 10 |
| Active trial seconds | 179.785 | **720.215** | **900** |
| Directories / code uploads / Jobs / runs | 0 / 0 / 0 / 0 | 2 / 6 / 1 / 2 | Same |

The separate historical readiness inventory of 37 requests remains recorded, not hidden in these execution counters. Unused prior limits confer no authority after a stop. This proposal requires an explicit new SQL/metadata budget renewal; it is not a retry under the earlier approval.

Keep **30-second wait/CANCEL, 45-second SQL client deadline, 200 rows / 65,536 bytes**, 30-second metadata deadline / 1 MiB response cap, 90-second task / 600-second Job limits and at least five seconds between Job polls. Upload limits stay 256 KiB/file / 1 MiB total. At most 11 SQL-file task executions, two sequential runs, one active Job run, queue disabled, no schedule and zero retries. The remaining whole-trial deadline bounds all requests and reserves time for at most one cancellation of a known active run; Jobs limits bound scripts, not each inner SQL statement.

**Zero Bronze/Silver/manifest DML, zero table/view DDL, no Gold/source changes, new compute, grants/settings changes, scheduling, task repair or cleanup.** Stop on the first failed/incomplete gate, SQL/runtime error, timeout, cancellation, unexpected/truncated result or write; preserve any partial deployment. Neither the failed matrices, completed diagnostic nor compound-marker probe is replayed. Jobs-native compatibility, COMPLETE-only rerun preservation and genuinely new-source processing/recovery remain unverified until separately approved execution establishes them.
