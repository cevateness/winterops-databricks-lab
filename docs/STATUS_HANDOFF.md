# WinterOps — Status handoff (2026-10-28)

This file resolves **stale status text** in earlier lesson ZIPs. It records known evidence; the user can resume after long pauses without replaying every lesson.

## Current verified state (2026-10-28)

- **Lesson 7 Phase A: READY_TO_APPLY, pending separate exact-object publication approval.** PR #2 is merged at `2645dc9`; follow-up work is on `feat/lesson7-publication-preflight`. Source/schema/checksum and existing preflight checks pass. The user confirmed CREATE TABLE on `workspace.default` through its workspace-users system principal; current API grant/owner metadata and SCIM memberships corroborate that attribution. Target lookups return 404, so create-only SQL will fail on any hidden/racing conflict. No DDL has run; the grant confirmation is not publication approval. See [LESSON_7_PUBLICATION.md](LESSON_7_PUBLICATION.md) for the evidence and recovery plan.
- **Databricks CLI v1.22.1 is installed and the named `winterops` profile is configured. Live read-only connectivity: PASS.** The sanitized checker verified the profile/host match, `current-user me`, and `workspace list /Workspace` after the workspace origin was corrected. Credentials, identity details, workspace listings and private URLs were suppressed.
- Follow-up source audit: warehouse listing and bounded Statement Execution API calls succeeded on the existing serverless 2X-Small warehouse. Source hash `f5d7633c910e1ad6be23b4111445bf0bc14fe2071c6ea0f0d4cd456295ea9e94`, dataset/filename/path, Bronze/Silver counts, all established one-week activity aggregates, required schema types and payload multiplicities matched. The current 8,671,212-byte Volume CSV was independently checksummed and matched that hash; only hash/size were returned. See [SOURCE_VERSION_EVIDENCE.md](SOURCE_VERSION_EVIDENCE.md) for scope, exact results and limitations.
- **Lesson 6 shared candidate SQL validation: PASS through the Statement Execution API.** After explicit user approval from `11dba68`, the required Silver types were rechecked and the unchanged two preflight statements plus candidate CTE reconciliation executed sequentially. All four statements were `SUCCEEDED`; all nine assertion outputs passed. Gold `consumer_check` and `hourly_check` passed, with no errors, cancellations, truncation or retries. Limits remained 30-second server wait / CANCEL, 25 rows, 65,536 bytes and a hard 45-second client deadline.
- The notebook and Spark entrypoint were **not executed**. No source objects, views, jobs or schedules were created or changed; no warehouse configuration was changed. The existing warehouse served the approved SQL. Candidate SQL is ready for publication review; actual DDL privileges, grants/ownership effects, published-view reconciliation and rerun invariants remain unverified.
- The offline suite has 57 passing tests. Next small milestone: obtain explicit approval for the exact create-only publication scope, then perform fresh source/metadata rechecks before any DDL. Publication remains unapproved.

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
6. Exact-version Silver clean/quarantine consumer views and source-local/naive hourly Gold observations, including read-only candidate validation: `src/winterops/analytics.py`, packaged SQL templates and `notebooks/06_silver_consumers_hourly.py`. **Shared SQL passed read-only warehouse validation; publication and notebook/Spark execution have not run.**

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
- The standalone CLI, named profile, source-file version/evidence and bounded Lesson 6 shared SQL validation are verified. The SQL candidate is ready for publication review on the tested warehouse.
- Lesson 7 source checks, privilege attribution and publication/recovery preparation are complete. Obtain separate publication approval. Target 404 responses are not full-visibility absence proof; retain create-only conflict protection and fresh checks. Direct notebook/Spark execution remains untested.
- After separate approval for view creation/replacement, run `mode=apply` twice and inspect reconciliation and rerun invariants.
- Keep publication and notebook/Spark execution marked NOT RUN until actually executed; no forecasting, service-coverage claims or scheduled jobs are part of this milestone.
