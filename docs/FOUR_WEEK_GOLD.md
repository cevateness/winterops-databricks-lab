# Four-week Gold candidate — January 5–February 1, 2026

**LOCAL CANDIDATE VERIFIED; NOT VALIDATED OR PUBLISHED IN DATABRICKS.** Prepared on `feat/four-week-gold-candidate` from canonical main `3b7fdb175d353c02cd695f728c4ced9ca8c7d86f`. No authentication, workspace inspection, SQL, upload, Job run or remote mutation occurred. Prior [native ingestion evidence](INCREMENTAL_INGESTION_FILES_ABSENCE_RESULTS.json) establishes the fourth source's COMPLETE state; current remote readiness must be checked only under a new explicit approval.

## Selection and minimal implementation

[FOUR_WEEK_SELECTION.json](FOUR_WEEK_SELECTION.json) retains the first three entries of [THREE_WEEK_SELECTION.json](THREE_WEEK_SELECTION.json) exactly and appends:

- Source: `snowplow-2026-01-26_2026-02-01.csv`, nominal `[2026-01-26, 2026-02-02)`.
- CSV SHA-256: `cebcbd758e2a0cf5d0624ecf9cd6993244e7becdd1846a4057b4f63be22ed6c6`.
- Source version: `ad5c201ccee0b96b2f4907f10ee3a064a7562d17429146d2205b1eaca46fdc00`.
- Processing key: `9c8e1b6f640e75c21f1c9f429ec670c389bf178269afd2f1543b2ae759c3eeae`.
- Pipeline `windsor-foundation-v2.1`, default quality policy `03829a2ce3b308a45e0205ca12a5288e5cb08b97189cf20b69c0e37d4c546e08`, 66,850 expected Bronze/Silver rows. The complete policy and exact immutable original-CSV Volume path are explicit in the selection; the compressed transport is not substituted for the original CSV.

The existing `UnifiedGold` selection/eligibility/transformation/reconciliation logic is reused. The only runtime addition is a validated unqualified `view_prefix` (1–80 lowercase identifier characters), loaded by the existing renderer. Its default is unchanged. The four-week prefix is `winterops_v2_gold_20260105_20260201_v1`; every candidate retains source week, exact version/key/policy and original CSV reference. No latest-version inference, new policy, ingestion or orchestration logic is introduced. The non-three-week dashboard query label is now `source_week_comparison`; existing three-week selection and all its SQL/dashboard renders remain byte-identical.

## Actual offline analytical evidence

The original private local store was opened read-only; its SHA-256 was unchanged afterward. A separate private typed SQLite copy holds the existing four scopes. All original CSV fingerprints were checked locally. The existing generated selection guard, hierarchy reconciliation and hourly/daily/weekly queries executed successfully. Every aggregate row then matched an independent Python row-based oracle using full `Counter` multisets, including duplicates, participation, microsecond clock ties/gaps and quality diagnostics. SQLite dialect adaptations do not prove native type/optimizer behavior. [Aggregate evidence](FOUR_WEEK_LOCAL_EVIDENCE.json) records exact results, timings and canonical product hashes; record-bearing files remain outside Git.

| Measure | Existing three weeks | Fourth week added | Four-week candidate |
|---|---:|---:|---:|
| Bronze / Silver observations | 231,306 | 66,850 | **298,156** |
| HEADER / other INVALID | 79 / 0 | 26 / 0 | **105 / 0** |
| VALID / Gold observations | 231,227 | 66,824 | **298,051** |
| Hourly / daily / weekly aggregate rows | 236 / 20 / 3 | 89 / 5 / 1 | **325 / 25 / 4** |
| Plow-active observations | 175,008 | 64,336 | **239,344** |
| Spreader-active observations | 119,439 | 7,793 | **127,232** |

The three-week subset's **full daily/weekly rows and hourly summaries match recorded native published evidence**. All hourly rows also match the independent local oracle. These comparisons use historical native results, not fresh reads of currently published views. The fourth week's counts, policy, participation and equipment flags match its existing source-validation evidence.

| Source week begins | Valid observations | Plow / spreader | Hours / days containing telemetry | Observed identifier strings |
|---|---:|---:|---:|---:|
| January 5 | 2,791 | 2,790 / 164 | 42 / 7 | 27 |
| January 12 | 110,311 | 79,471 / 68,870 | 79 / 7 | 251 |
| January 19 | 118,125 | 92,747 / 50,405 | 115 / 6 | 316 |
| January 26 | 66,824 | 64,336 / 7,793 | 89 / 5 | 223 |

Hourly grain is one selected processing version/source-local hour; daily grain is that version/date; weekly grain is one explicitly selected processing version. Hourly → daily → weekly additive metrics reconcile with valid Silver separately for all four scopes. Equipment categories total **170,819 plow-only + 58,707 spreader-only + 68,525 both-active + 0 neither = 298,051**. Plow/spreader counts overlap through both-active observations. The 3,981 valid observations belonging to repeated-payload groups are retained, not deduplicated. Engine-off and engine-off-with-equipment diagnostics are zero for these selected records. Geographic review warnings remain **863** (677 / 186 / 0 / 0), separate from zero invalid-coordinate classifications.

Observed days are not a complete calendar: January 19's source has six days with telemetry and January 26's source has five, ending January 30 13:12:52. Missing January 31/February 1 rows do not establish inactivity. `event_time_unzoned` stays `TIMESTAMP_NTZ`, source-local/naive; gap values are clock differences within a source/policy/identifier scope. Observation counts and hours containing telemetry are not working time, coverage or productivity. Distinct identifier counts are recomputed at each grain, never summed into a four-week fleet size or interpreted as availability. No detailed identifier, coordinate or trajectory is exported.

**217 offline tests passed / zero failures or errors / 7.018 seconds**, including eight new differential/isolation tests. They verify four-source metrics, missing-COMPLETE failure, multiplicity corruption, create-only naming, unchanged three-week products, published same-count corruption detection, checked-in source identity and CLI rendering. CI additionally renders both four-week candidate/publication SQL. An offline audit compiles all 18 adaptable read contracts in the native matrix against local legacy/V2 aggregate schemas and separately checks history/fingerprint/DDL contracts; it never executes Databricks SQL. Exact-commit CI and all render/hash/privacy checks are recorded in the PR/report.

Render locally with the existing entrypoint:

```powershell
python scripts/render_unified_gold.py --selection docs/FOUR_WEEK_SELECTION.json --output .venv/four-week-candidate.sql
python scripts/render_unified_gold.py --selection docs/FOUR_WEEK_SELECTION.json --publication --output .venv/four-week-publication.sql
```

## Smallest publication step — one conditional approval, three new views

After reviewing the exact code/CI and [frozen native plan](FOUR_WEEK_NATIVE_PLAN.json), approve a fresh bounded scope using the existing `winterops` workspace and SQL warehouse. The old ingestion SQL/metadata budgets are exhausted and are not reused. Proposed maxima: **29 Statement API submissions (26 READ + 3 CREATE VIEW), 33 metadata GETs, 900 active seconds including auth/checks**. Zero uploads, Jobs, ingestion DML, table creation, schedules, compute/grant/configuration changes or old-view changes.

1. **Read-only gates first:** 18 metadata GETs establish identity/warehouse/use, no active Jobs, catalog/schema privileges, exact V2 contracts/ownership/SELECT and all four protected Gold definitions. SQL 1–15 snapshots all four COMPLETE manifests, checks all four original CSV fingerprints, runs selection/hierarchy guards, compares full weekly/daily results and a bounded hourly summary, checks all 89 fourth-week hourly metric rows (about 26 KB values), compares each original three-week product with its complete candidate subset via `EXCEPT ALL`, and requires Delta **4/5/17**. Native result shape, counts and values must match pinned offline evidence. Stop on unresolved privilege mapping or any mismatch; do not change permissions.
2. **Final gate and create-only publication:** one fresh active-run GET and SQL 16 check all target names absent. Information-schema visibility is permission-limited; create-only DDL still fails on any hidden conflict. Only if all previous gates pass, SQL **17–19** creates these exact objects sequentially:

   - `workspace.default.winterops_v2_gold_20260105_20260201_v1_hourly_observations`
   - `workspace.default.winterops_v2_gold_20260105_20260201_v1_daily_activity`
   - `workspace.default.winterops_v2_gold_20260105_20260201_v1_weekly_quality`

   No `OR REPLACE`, `IF NOT EXISTS`, alias redirection or changes to current three-week/legacy views. The [official CREATE VIEW contract](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-create-view) requires appropriate catalog/schema usage and CREATE TABLE privilege; replacement has different ownership/grant consequences and is excluded here. Read privileges/ownership on dependencies must also be established. Three metadata GETs verify each new object's type, authenticated ownership, complete definition and expected column names/positions/full type declarations, then pin identities.
3. **Postflight and preservation:** SQL 20–22 compares each published product's full multiset/all columns against the candidate, one product per request. SQL 23 repeats published weekly results and compares with the earlier candidate. SQL 24–29 rechecks old Gold baselines, every manifest field/timestamp, Delta **4/5/17**, and all CSV hashes. Eleven final metadata GETs preserve warehouse/protected contracts and all three newly pinned view identities/definitions. The native executor must record actual DDL outcomes separately from verified published results. Current published views remain the default until a later explicit consumer choice; no cutover is included.

Keep **30-second wait / CANCEL**, **45-second SQL client deadline**, INLINE **200-row / 65,536-byte** limits; metadata **30 seconds / 1 MiB**; no result polling/chunk fetching or retries. Original CSV guards cover 23,467,248 bytes total, within 16 MiB/file and 32 MiB combined caps. Never export all 325 hourly rows in one response; the projection for the new week fits 89 rows, while old hourly rows are compared in SQL. Count and reject truncation, unexpected schema/type/response or incomplete results. Check the remaining whole-scope deadline before every request; stop rather than expand limits. Local SQLite timings are not native performance predictions. The prior combined published reconciliation timed out natively; this proposal uses separate per-product comparisons and no fallback cascade.

The three DDL operations are **not atomic**. Stop at the first error, timeout/cancellation, conflict, unexpected write or integrity mismatch. Record exactly which views exist and preserve any partial publication. No automatic DROP, ALTER, overwrite, cleanup, repair or retry is authorized. A later separately reviewed recovery may verify/reuse an exact created subset or choose a new version suffix; it must not silently replace unrelated objects. Active-writer checks are point-in-time checks, not a cross-writer lock.

## Exact proposal fingerprints and pending work

- Native plan JSON UTF-8/LF: **`1d22f9c99d2d540111296c890c3173ede71921665c5a1ac8cc938f64c589330e`**.
- Private SQL matrix: **`1a121d0a72f62681b3fcaf1a1f91d844d34fd91ab26e365f5ba29e6bdc80a3de`**.
- Private metadata plan/bindings: **`1ef8fcf73e9931422d10ecbfdf9b1d996d8caec6cf501a352ceeea1e9c6cc688`**.

The plan also pins code, selection, expected private aggregate results and public/native evidence hashes. Current remote target absence, privileges, schema, protected baselines and four-scope optimizer/performance behavior are **unverified**. No new views are published by this preparation. The recommended next action is review/approval of this single conditional plan, then three create-only view statements after all read-only gates pass; no ingestion rerun or new infrastructure is needed.

Source attribution: Contains information licensed under the [Open Government Licence — The Corporation of the City of Windsor](https://opendata.citywindsor.ca/Documents/OpenDataTermsofUse.pdf).
