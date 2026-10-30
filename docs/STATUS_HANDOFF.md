# WinterOps — Status handoff (2026-10-29)

This file resolves **stale status text** in earlier lesson ZIPs. It records known evidence; the user can resume after long pauses without replaying every lesson.

## Current verified native state (2026-10-30)

- **Three-week V2/Gold: PUBLISHED_AND_VERIFIED.** From merged PR #8 / main `2a3b75a`, explicit approval of `146088df…39aef3` covered three immutable uploads, the middle-only 110,337-row Bronze/Silver append, COMPLETE manifest and three create-only Gold views. Candidate reconciliation passed; the first combined published check canceled at the 30-second wait. The matrix stopped with no retry. Separately approved read-only plan `9f5896dc…d31888` then passed all 16 requests, including independent full hourly/daily/weekly multiset comparisons and final preservation/hash/metadata/grant/warehouse checks. Three selected COMPLETE versions reconcile to 231,306 Bronze/Silver = 79 HEADER + 231,227 VALID + 0 other INVALID; published Gold has 236 hourly rows, 20 daily rows, three weekly rows, 175,008 plow / 119,439 spreader observations and 863 independent geography warnings. Both prior V2 weeks and their full-precision manifests are unchanged; middle rerun decision is read-only/no DML. Legacy Gold remains 79 buckets / 110,311 observations / 79,471 plow / 68,870 spreader, with original Delta versions 2 and 0. All original CSV hashes and 11 object identities/definitions/schemas, effective grants and warehouse configuration matched after completion. Total: 45 SQL submissions (44 succeeded / one canceled), 365.451 active seconds, zero automatic retries. No notebook/PySpark execution, jobs, schedules, grant/config changes, cleanup or rollback. Current fixes/evidence use `feat/threeweek-native-integration`; preserve unrelated user files. See [native report](THREE_WEEK_NATIVE_INTEGRATION.md), [actual aggregates/timings](THREE_WEEK_NATIVE_RESULTS.json) and [executed read-only scope](THREE_WEEK_POSTFLIGHT_PLAN.json). Next: review the single final commit/CI; do not replay append or CREATE operations. Performance headroom is narrow; time/identifier/CRS interpretation limits remain unresolved.

## Current verified state (2026-10-29)

- **Unified three-week foundation: LOCAL PASS; native extension NOT EXECUTED.** Branch `feat/unified-threeweek-gold` starts at merged main `7662ece`. The existing middle CSV was downloaded via bounded read-only HEAD/GET and matches its documented hash/8,671,212 bytes. V2 local backfill matches legacy classifications and activity counts, adding 186 geographic warnings without invalidating rows; both earlier local weeks and manifests are unchanged. Explicit COMPLETE-only source/policy selection and hourly/daily/weekly SQL pass synthetic and real-data SQLite-adapted reconciliation: 231,306 rows = 79 HEADER + 231,227 VALID + 0 other INVALID, 236 hourly buckets, 20 daily rows and three weekly rows. The full 126-test offline suite passes. Immutable original-CSV landings for the outer weeks, a middle gzip artifact and three new Gold views are prepared in one exact 45-statement plan requiring separate approval. No native SQL, uploads, data/object writes, jobs, grants or warehouse changes were performed in this task; read-only metadata readiness is documented separately. Existing published functionality remains the PR #7 outer-week V2 tables and legacy one-week views. See [contracts/evidence](THREE_WEEK_GOLD.md), [source results](THREE_WEEK_SOURCE_EVIDENCE.json), [local SQL results](THREE_WEEK_LOCAL_SQL_RESULTS.json) and [bounded plan](THREE_WEEK_INTEGRATION.md).
- **V2 native integration: PASS after separate approval of the revised gzip scope.** At `c1d8de3` on `feat/v2-native-integration` / PR #7, fresh workspace/warehouse, privileges, protected baselines and conflict checks passed. One 9,920,290-byte gzip upload completed in 23.959 seconds; both source artifacts/input guards passed before DDL. All 38 integration statements succeeded in 130.391 seconds (45 including readiness). Three isolated development tables now hold 120,969 Bronze rows, 120,969 Silver rows and two COMPLETE manifest entries. January 5–11 reconciles to 2,810 = 19 HEADER + 2,791 VALID; January 19–25 to 118,159 = 34 HEADER + 118,125 VALID; other INVALID is zero. Planned Bronze-only checkpoint recovery, both unchanged rerun decisions with zero additional DML, and full-multiset first-week preservation after append passed. Original one-week data/published aggregates, Delta versions, metadata, parent grants and warehouse configuration matched afterward. No retries, runtime errors, truncation, notebook/PySpark execution, cleanup or protected writes occurred in this run. The earlier 180-second upload failure remains recorded, with zero SQL in that stopped attempt. There are 110 passing offline tests. See [outcome](DATA_FOUNDATION_V2_NATIVE.md), [sanitized evidence](DATA_FOUNDATION_V2_NATIVE_RESULTS.json) and [executed scope](DATA_FOUNDATION_V2_INTEGRATION.md).
- **Original Data Foundation V2 implementation milestone: local validation PASS (before native follow-up above).** Branch `feat/data-foundation-v2` starts at merged PR #5 / main `929ffd6`. Official source review confirms activity-triggered nominal 15-second reporting, not a continuous availability feed. Both additional weekly CSVs were downloaded and staged outside Git. January 5–11: 2,810 Bronze/Silver = 19 HEADER + 2,791 VALID; January 19–25: 118,159 = 34 HEADER + 118,125 VALID. No other INVALID or missing non-header fields occurred. The configured review envelope flags 677 smaller-week observations without invalidating them. Only one raw identifier string is shared between the two new files; no fleet-size or identity-lifecycle explanation is established. Local rerun and earlier-week preservation passed; synthetic lifecycle tests cover source revisions, changed policy, interruptions and scoped repair. That milestone passed 107 tests; the gzip/native follow-up passes 110. See [implementation/source contract](DATA_FOUNDATION_V2.md), [sanitized reports](DATA_FOUNDATION_V2_SOURCE_REPORT.json) and [one bounded integration proposal](DATA_FOUNDATION_V2_INTEGRATION.md). That original implementation milestone performed no V2 remote execution; the separately approved integration above is the later native evidence.
- **Native Gold analytics validation: PASS.** After PR #4 merged at `402c820`, separate explicit approval covered one bounded SQL API run. One schema query with a synthetic NTZ/DECIMAL/LAG clock probe, both guards and all eight unchanged products succeeded: 11 statements, complete/untruncated results, no errors, cancellations or retries. The source/hourly and product guards passed all four assertions. Seven daily and 79 hourly grains reconcile to 110,311 valid observations, 79,471 plow-active and 68,870 spreader-active observations. Native leap-day midnight arithmetic retained a 500,001-microsecond gap and timestamp tie. See [actual metrics/timings](GOLD_ANALYTICS_NATIVE_VALIDATION.md), [sanitized results](GOLD_ANALYTICS_NATIVE_RESULTS.json) and [definitions/dashboard/architecture](GOLD_ANALYTICS_PRODUCTS.md). No code correction, DDL, jobs or source/object changes were needed; evidence/status changes use `feat/native-gold-validation`.
- **Lesson 7 Phase B: PUBLISHED_VERIFIED_STABLE after separate explicit approval.** All three exact views were created once with CREATE VIEW only from `f240d60`, after fresh source/schema/checksum/privilege checks. Object type, authenticated-creator ownership and definitions matched. All 11 bounded SQL statements succeeded, with no errors, cancellation, truncation, retries or rollback. Published postflight and safe Gold aggregates passed twice with identical results. See [LESSON_7_PUBLICATION.md](LESSON_7_PUBLICATION.md) and [safe aggregate evidence](LESSON_7_GOLD_RESULTS.json).
- **Databricks CLI v1.22.1 is installed and the named `winterops` profile is configured. Live read-only connectivity: PASS.** The sanitized checker verified the profile/host match, `current-user me`, and `workspace list /Workspace` after the workspace origin was corrected. Credentials, identity details, workspace listings and private URLs were suppressed.
- Follow-up source audit: warehouse listing and bounded Statement Execution API calls succeeded on the existing serverless 2X-Small warehouse. Source hash `f5d7633c910e1ad6be23b4111445bf0bc14fe2071c6ea0f0d4cd456295ea9e94`, dataset/filename/path, Bronze/Silver counts, all established one-week activity aggregates, required schema types and payload multiplicities matched. The current 8,671,212-byte Volume CSV was independently checksummed and matched that hash; only hash/size were returned. See [SOURCE_VERSION_EVIDENCE.md](SOURCE_VERSION_EVIDENCE.md) for scope, exact results and limitations.
- **Lesson 6 shared candidate SQL validation: PASS through the Statement Execution API.** After explicit user approval from `11dba68`, the required Silver types were rechecked and the unchanged two preflight statements plus candidate CTE reconciliation executed sequentially. All four statements were `SUCCEEDED`; all nine assertion outputs passed. Gold `consumer_check` and `hourly_check` passed, with no errors, cancellations, truncation or retries. Limits remained 30-second server wait / CANCEL, 25 rows, 65,536 bytes and a hard 45-second client deadline.
- Published Gold has 79 source-local/naive hourly buckets, 110,311 observations, 79,471 plow-active, 68,870 spreader-active and 2,210 repeated-payload observations. Per-hour distinct truck identifiers range from 1 to 20; all 79 hourly counts are recorded without identifiers/coordinates. These are observation counts, not working time, coverage or productivity.
- The notebook and Spark entrypoint were **not executed**. Only the three approved views were created; Bronze/Silver source tables, source files, jobs, schedules, parent grants and warehouse configuration were unchanged. Stable read verification passed; repeated DDL/replacement and future source stability remain untested.
- The offline suite has 80 passing tests. Current native diagnostics show 41,441 plow-only / 30,840 spreader-only / 38,030 both-active observations; neither-active and engine-off counts are zero. Reporting diagnostics show 251 identifiers, 2,210 repeated-payload observations and 95 above-threshold gap pairs involving 82 identifiers. These do not establish fleet availability, engine effectiveness, time worked, downtime or productivity. Published Lesson 7 state remains unchanged. The native run verified published source metadata and view reconciliation, not a fresh raw-file checksum or Bronze audit.

## Initial integration-readiness audit (2026-10-28)

- Initial working tree: clean at `584b2f6` on the previous analytics feature branch. GitHub PR #1 was verified merged; refreshed `origin/main` is merge commit `9c92008`. Changes for this audit use `feat/lesson6-readonly-validation`, based on that merged main.
- All **46 existing offline tests passed**, with no failures or errors. The expanded suite now passes **57 tests**, including read-only candidate SQL and notebook mode dispatch. Aggregate fixture validation, Python syntax checks and the built-wheel smoke test passed; the wheel includes the read-only API and all six SQL templates. These are offline results, not Databricks runtime evidence.
- CLI verification: `databricks` is absent from PATH and was not found in the documented portable installation or checked WinGet, Scoop, Chocolatey and project-venv locations. A CLI version could not be queried. No installer was run or authentication profile created.
- Authentication configuration: the default Databricks profile file does not exist, no alternate config-file environment variable was set, and no `DATABRICKS_*` environment variables were present. No credential values or private workspace URLs were printed. This does not assess the user's browser sign-in.
- Lesson 6 review identified a missing read-only runtime path. The notebook now offers `render` (default), `validate` (schema + source/candidate queries only) and `apply` (explicit view writes). A saved legacy `apply_views` value is ignored.
- `validate_plan(...)` and renderer `--validation-only` derive candidate consumer CTEs from the existing SQL definitions. They require no published consumer objects and perform no DDL. Exact source/path/hash/window guards, observation multiplicities and source-local/naive semantics are preserved.
- **Databricks connection: BLOCKED / not attempted.** No CLI, configured profile or explicit workspace target is available. **Spark/schema/source/candidate validation: BLOCKED / not run.** The actual file hash and runtime access still need review. View application has not been approved; no Databricks objects, jobs, source data or Cloud setup were changed.
- Next gate: install the official standalone CLI and authenticate the named `winterops` profile locally, verify the explicit workspace host with the sanitized checker, obtain/review the file SHA-256 and matching evidence, then execute `mode=validate` within the approved read-only compute scope. View creation/replacement remains a separate approval.

## CLI setup follow-up (2026-10-28)

- The user reported `running scripts is disabled`; the effective local policy was verified as `Restricted`, with managed scopes unset. The reviewed installer also had `ZoneId=3`, requiring removal of its Internet-download mark before `RemoteSigned` would allow the unsigned file.
- Only `scripts/install_databricks_cli.ps1` was unblocked. It ran in a child PowerShell process with `RemoteSigned`, downloaded the official Windows amd64 release, verified SHA-256 against release metadata, and installed **Databricks CLI v1.22.1** in the documented user-local directory. Both installer and direct executable version checks passed. The user PATH includes the installation directory; existing terminals may require a local PATH refresh.
- Parent policy remains `Restricted`; no persistent execution-policy setting changed. Downloads now use `-UseBasicParsing`, installer cleanup validates the resolved temporary target, and setup instructions stop after installation/login failures.
- Verification after the setup fix: **57 offline tests passed**, PowerShell parser checks passed, and an installer rerun detected the existing CLI and exited successfully without downloading again. Local-only profile inventory could not complete (exit 1); the default profile file is still absent. No workspace authentication or API check was attempted.
- Installation resolved the initial missing-CLI blocker; authentication and connectivity were initially pending. The user's `https://YOUR-WORKSPACE-HOST` value was a placeholder. No credentials, private workspace URLs, source data or Databricks objects were exposed or changed.
- During login follow-up, a saved profile first included a page path, which the host guard rejected before remote API calls. The Windows setup example now strips paths, queries and fragments before login. After the user repeated authentication with the corrected origin, all three read-only checks passed as recorded above. No private URL or credential values were printed.

## What is implemented (source code exists)

1. Synthetic CSV → Bronze Delta: `notebooks/01_bronze_ingestion.py`; special demonstration groups identical rows with `occurrence_count` (13 source observations / 12 unique JSON rows).
2. Synthetic Bronze → typed demo Silver: `notebooks/02_silver_typing.py`.
3. Real Windsor CSV, read-only profiling: `notebooks/03_profile_real_csv.py`.
4. Real Windsor weekly CSV → distinct real Bronze table, one row **per parsed source observation** and file-version scope: `notebooks/04_bronze_real_ingestion.py`.
5. One-week real Bronze → quality-classified Silver table: `notebooks/05_silver_real_windsor.py` and `sql/real_silver_checks.sql`.
6. Exact-version Silver clean/quarantine consumer views and source-local/naive hourly Gold observations: shared SQL passed read-only validation, then the three views were created and reconciled through the Statement Execution API. **Published views and stable repeated reads are verified; notebook/Spark execution has not run.**

## Local analytics implementation (2026-10-25)

- The user deferred Cloud selection and requested local implementation of `docs/CODEX_CLOUD_TASK.md`. A published Cloud environment is user-reported; extension visibility remains unresolved and is not a prerequisite for development.
- New SQL selects dataset, filename, Volume path and a required file SHA-256. That SHA-256 is not in the reported aggregate fixture and must be supplied from reviewed workspace evidence.
- Preflight validates schema, bounded naive dates, expected aggregate counts and per-payload Bronze/Silver multiplicities before view DDL. Existing notebooks 01–05 and original SQL are unchanged.
- Intended new objects: `workspace.default.winterops_silver_windsor_valid`, `workspace.default.winterops_silver_windsor_quarantine`, and `workspace.default.winterops_gold_windsor_hourly_observations`. All are views; none has been created in the workspace by this work.
- Local Python 3.14.4 verification: **46 tests passed**, including SQLite-adapted SQL reconciliation and mocked CLI tests. Syntax, aggregate validation, SQL rendering, PowerShell parsing and isolated wheel SQL-resource checks passed. These are offline checks, not Spark execution.
- The read-only CLI checker requires a named profile and matching workspace host, suppresses CLI output and bounds command timeouts. Authentication is a separate explicit step.
- Databricks integration: **BLOCKED / not run**. The CLI is absent from the current PATH, no actual workspace target was supplied, and no remote execution was approved. No tables, views, jobs or schedules were affected.
- See `docs/ANALYTICS_SLICE.md` for runtime/grant/concurrency caveats and acceptance steps. CI for this branch must be assessed from its actual GitHub Actions result.

## Databricks evidence shared by the user

Source: `snowplow-2026-01-12_2026-01-18.csv`. The user reports executing the notebooks and SQL checks in Databricks Free Edition.

| Check | Shared value |
|---|---:|
| Bronze rows | 110,337 |
| Silver rows | 110,337 |
| `HEADER` | 26 (`REPEATED_HEADER`) |
| `VALID` | 110,311 |
| Other `INVALID` | 0 |
| Distinct truck IDs (`VALID`) | 251 |
| Earliest `event_time_unzoned` | 2026-01-12 09:42:46 |
| Latest `event_time_unzoned` | 2026-01-18 23:58:54 |
| Plow-active observations | 79,471 |
| Spreader-active observations | 68,870 |
| Min latitude / max latitude | 42.22603988647461 / 42.35206985473633 |
| Min longitude / max longitude | -83.10281372070312 / -82.18211364746094 |

The unusual easternmost longitude, repeated-payload patterns, event timezone, and business status semantics remain **open questions**. No complete Databricks logs or live API access have been provided to independently inspect these results.

## What remains unimplemented or unverified in the workspace

- Apply and verify the prepared clean/quarantine Silver **consumer views** after target/hash review and approval.
- Automated QA execution and machine-readable evidence from actual Databricks jobs.
- Apply and verify the prepared hourly observation-count Gold view. Zone distributions remain unimplemented.
- Real weather alignment, forecast-vs-actual provenance, geofencing and map matching.
- Prediction, model evaluation, optimization, or simulation.
- Proven Databricks CLI/API access. Cloud extension selection is deferred; the canonical GitHub repository and local Git connection are established.

## GitHub publication (2026-10-25)

- The user-created public repository is https://github.com/cevateness/winterops-databricks-lab. It was confirmed empty before the first upload.
- The local project is initialized with Git; `main` tracks `origin/main` using the HTTPS remote. Git Credential Manager already has the user's GitHub account configured.
- Publication preserves the existing notebooks, SQL, Python modules and tests. Setup/status documentation now describes the connected checkout and normal pull/commit/push workflow.
- Local Python 3.14.4 verification: **13 tests passed**, `python -m compileall -q src scripts notebooks` passed, and aggregate fixture validation passed. Two temporary-file tests initially encountered sandbox permissions; the unchanged suite passed when run outside that sandbox.
- Offline GitHub Actions is configured in `.github/workflows/ci.yml`; consult the repository's Actions page for the actual run status.
- No Databricks tests were run for publication. Workspace integration remains unverified; no Databricks tables or scheduled jobs were affected.

## Work-mode decision

As of 2026-10-23, user requests a **public canonical GitHub repo**, **Codex Cloud development**, and **programmatic Databricks execution** where feasible. Manual exercises are no longer required for each iteration. Keep the learning objective through design and validation review, not notebook copy-paste.

On 2026-10-25, the user chose **local Codex development for now** while Cloud environment selection remains unresolved. Continue feature-branch/PR development locally; preserve the published Cloud environment and its draft.

## Next high-value milestone

- The original analytics PR #1 is merged. Review the new read-only validation change and its actual CI result.
- The standalone CLI, named profile, exact source, Lesson 6 shared SQL and Lesson 7 published views/repeated read verification are verified on the existing warehouse.
- PRs #3–#6 are merged. One-week Gold acceptance passed. The first V2 attempt stopped before SQL at its large-upload deadline. Review the evidence and gzip correction, then explicitly approve the revised one-upload/38-statement scope before further writes. Existing Gold remains pinned to its established source; earlier approval does not authorize retry, migration, replacement or cleanup.
- No repeated DDL, replacement, grant changes or rollback is authorized by the completed run. Direct notebook/Spark execution and DDL rerun invariants remain untested.
- Multi-week ingestion is implemented and tested locally; its native persistence remains pending approval. No forecasting, service-coverage claims, new dashboard, optimization or scheduled jobs are included.
