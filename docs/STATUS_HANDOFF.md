# WinterOps — Status handoff (2026-10-25)

This file resolves **stale status text** in earlier lesson ZIPs. It records known evidence; the user can resume after long pauses without replaying every lesson.

## What is implemented (source code exists)

1. Synthetic CSV → Bronze Delta: `notebooks/01_bronze_ingestion.py`; special demonstration groups identical rows with `occurrence_count` (13 source observations / 12 unique JSON rows).
2. Synthetic Bronze → typed demo Silver: `notebooks/02_silver_typing.py`.
3. Real Windsor CSV, read-only profiling: `notebooks/03_profile_real_csv.py`.
4. Real Windsor weekly CSV → distinct real Bronze table, one row **per parsed source observation** and file-version scope: `notebooks/04_bronze_real_ingestion.py`.
5. One-week real Bronze → quality-classified Silver table: `notebooks/05_silver_real_windsor.py` and `sql/real_silver_checks.sql`.

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

## What remains unimplemented

- Clean validated Silver and quarantine **consumer views** (suggested, not yet created).
- Automated QA execution and machine-readable evidence from actual Databricks jobs.
- Gold tables for hourly counts and zone distributions.
- Real weather alignment, forecast-vs-actual provenance, geofencing and map matching.
- Prediction, model evaluation, optimization, or simulation.
- Codex Cloud environment or proven Databricks CLI/API access. The canonical GitHub repository and local Git connection are now established; see publication evidence below.

## GitHub publication (2026-10-25)

- The user-created public repository is https://github.com/cevateness/winterops-databricks-lab. It was confirmed empty before the first upload.
- The local project is initialized with Git; `main` tracks `origin/main` using the HTTPS remote. Git Credential Manager already has the user's GitHub account configured.
- Publication preserves the existing notebooks, SQL, Python modules and tests. Setup/status documentation now describes the connected checkout and normal pull/commit/push workflow.
- Local Python 3.14.4 verification: **13 tests passed**, `python -m compileall -q src scripts notebooks` passed, and aggregate fixture validation passed. Two temporary-file tests initially encountered sandbox permissions; the unchanged suite passed when run outside that sandbox.
- Offline GitHub Actions is configured in `.github/workflows/ci.yml`; consult the repository's Actions page for the actual run status.
- No Databricks tests were run for publication. Workspace integration remains unverified; no Databricks tables or scheduled jobs were affected.

## Work-mode decision

As of 2026-10-23, user requests a **public canonical GitHub repo**, **Codex Cloud development**, and **programmatic Databricks execution** where feasible. Manual exercises are no longer required for each iteration. Keep the learning objective through design and validation review, not notebook copy-paste.

## Next high-value milestone

- Verify the first offline CI run, then configure Codex Cloud separately when requested (does **not** require Databricks access).
- Implement clean/quarantine views and tests without rewriting known Bronze/Silver tables.
- Implement an explicitly **observation-count-based** hourly Gold summary, not inferred plowing time or road coverage.
- Probe CLI/API access in the user's Free Edition workspace as a separate, permission-aware acceptance gate. Remote jobs only after connectivity and explicit target checks.
