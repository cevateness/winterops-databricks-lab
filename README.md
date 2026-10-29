# WinterOps | Weather-Driven Municipal Operations Intelligence

[![CI](https://github.com/cevateness/winterops-databricks-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/cevateness/winterops-databricks-lab/actions/workflows/ci.yml)

**Status (2026-10-28):** Databricks Free Edition learning MVP. **One real Windsor historical week** has been processed through Bronze and quality-classified Silver. Its exact source hash, schema and established aggregates are SQL-verified. After Lesson 6 candidate validation and separate approval, **all three Silver/Gold views were created and reconciled through the Statement Execution API**; repeated read-only verification was stable. See [live evidence](docs/SOURCE_VERSION_EVIDENCE.md). The original Windsor CSV is **not included** in this public repository. The canonical public repository is [cevateness/winterops-databricks-lab](https://github.com/cevateness/winterops-databricks-lab). Notebook/Spark entrypoint execution remains untested.

**Lesson 7:** PUBLISHED_VERIFIED_STABLE: 79 source-local/naive hourly buckets, 110,311 observations, 79,471 plow-active and 68,870 spreader-active observations. Per-hour distinct truck identifiers range from 1 to 20. See [publication evidence](docs/LESSON_7_PUBLICATION.md) and [all safe hourly counts](docs/LESSON_7_GOLD_RESULTS.json). These are observation counts, not working time or coverage.

**Gold analytics expansion:** Daily activity, hourly/daily equipment composition and aggregate fleet-reporting diagnostics passed native Databricks validation on 2026-10-29: both guards and all eight products succeeded unchanged. See [actual metrics, compatibility and timings](docs/GOLD_ANALYTICS_NATIVE_VALIDATION.md), [sanitized aggregate evidence](docs/GOLD_ANALYTICS_NATIVE_RESULTS.json), and [metric definitions, queries, four-chart dashboard and architecture review](docs/GOLD_ANALYTICS_PRODUCTS.md). No Databricks objects were changed.

**V2 native integration: PASS.** After a stopped large-file upload and separate approval of lossless gzip transport, all 38 integration statements succeeded. Two isolated development versions reconcile to 120,969 Bronze/Silver rows and two COMPLETE manifests; planned recovery, no-write reruns and original-object preservation passed. See [actual native evidence and limitations](docs/DATA_FOUNDATION_V2_NATIVE.md).

**Data Foundation V2:** Reusable multi-week local staging, immutable source versions, a recoverable manifest, observation-preserving Bronze/Silver and configurable quality diagnostics are implemented. January 5–11 and January 19–25 were processed privately outside Git; the original workspace pipeline is unchanged. See [source contract, implementation and trade-offs](docs/DATA_FOUNDATION_V2.md), [aggregate source evidence](docs/DATA_FOUNDATION_V2_SOURCE_REPORT.json) and [bounded integration scope](docs/DATA_FOUNDATION_V2_INTEGRATION.md). Native SQL-warehouse integration is verified in three isolated development tables. The optional PySpark adapter/notebooks remain unexecuted.

**Primary objective:** Learn reproducible data engineering, lakehouse architecture, PySpark/SQL, data quality, MLOps, and eventually decision analytics. **Secondary:** Public technical portfolio. **Longer term:** Explore commercial winter-service decision intelligence only if actual evidence warrants it; this version is non-commercial.

## Architecture today

```text
Original City of Windsor weekly CSV in the user's Databricks Unity Catalog Volume
   -> 04_bronze_real_ingestion.py: raw JSON, record/file SHA-256,
      one row per observed CSV record, including repeated headers and duplicate payloads
   -> workspace.default.winterops_bronze_windsor_activity (Delta)
   -> 05_silver_real_windsor.py: typed fields, quality_status, issue codes,
      repeated-payload warnings; one row per Bronze observation
   -> workspace.default.winterops_silver_windsor_week_sample (Delta)
   -> 06_silver_consumers_hourly.py (prepared; not run in Databricks):
      exact-version VALID + quarantine views -> source-local/naive hourly observation counts
```

Synthetic learning exercises (not the real pipeline) live in notebooks 01 and 02. Notebook 03 is a **read-only profiler**. No weather integration, routing, SLA measurement, or optimization has been implemented.

## User-reported real-week observations (not bundled data)

| Metric | Reported result |
|---|---:|
| Source file | `snowplow-2026-01-12_2026-01-18.csv` |
| Bronze rows | 110,337 |
| Silver rows | 110,337 |
| `HEADER` (repeated in-body CSV headers) | 26 |
| `VALID` under current limited checks | 110,311 |
| Other `INVALID` | 0 |
| Distinct truck IDs in valid rows | 251 |
| Plow-active valid observations | 79,471 |
| Spreader-active valid observations | 68,870 |

`VALID` is limited to parsing, basic coordinate-world bounds, ID, time and Boolean checks; it does **not** imply correct road location, completion, or actual vehicle deployment. Source timestamps are stored as `TIMESTAMP_NTZ`: the timezone has **not** been established. Exact repeat-payload count and geographic outlier root causes have **not** yet been independently reviewed. The single-week Silver table is rewritten per notebook execution.

## Layout

- `PROJECT_REFERENCE.md` — project charter, with current status appended.
- `AGENTS.md` — instructions for Codex and code reviewers.
- `docs/STATUS_HANDOFF.md` — latest verified versus pending work, known pitfalls.
- `docs/CODEX_CLOUD_TASK.md` — ready-to-paste Codex Cloud task.
- `docs/WINDOWS_SETUP.md` — fixes for missing `winget`, CLI authentication checks, Windows setup.
- `docs/GITHUB_CODEX_WORKFLOW.md` — public GitHub and Codex Cloud connection workflow.
- `docs/ANALYTICS_SLICE.md` — source/version contract, view definitions and integration acceptance gate.
- `scripts/install_databricks_cli.ps1` — optional portable official CLI installer, no WinGet/Admin required.
- `scripts/test_databricks_connection.ps1` — read-only connectivity and permissions diagnostics.
- `scripts/publish_to_github.ps1` — first push into a **user-created empty** public GitHub repository.
- `src/winterops/quality.py` and `scripts/validate_quality_snapshot.py` — dependency-free validation of aggregate QA evidence.
- `src/winterops/analytics.py` and packaged `src/winterops/sql/` — shared bounded SQL plan and offline reference counts.
- `scripts/render_analytics_sql.py` — offline renderer requiring a reviewed file SHA-256 and expected summary; `--validation-only` emits queries without view DDL.
- `src/winterops/gold_products.py` and `scripts/render_gold_products.py` — SELECT-only analytical products, independent Python reference calculations and offline dashboard SQL rendering.
- `sources.py`, `foundation.py`, `ingestion.py`, `spark_ingestion.py` and `scripts/windsor_history.py` — V2 discovery/staging, version/policy manifest, local incremental processing, aggregate diagnostics and isolated native plans. Record-bearing files are rejected under Git roots.
- `scripts/check_databricks.py` — named-profile/host-gated read-only CLI probe with sanitized output.
- `data/fixtures/windsor_week_2026_01_12_18_summary.json` — **aggregate results only**, no source telemetry.
- `.github/workflows/ci.yml` — offline tests on public GitHub, no Databricks secrets.
- `notebooks/01..05` and `sql/` — existing learning work, preserved.

## Work locally and sync

The existing local project folder is connected to GitHub. Continue working in that folder; use the [Git sync workflow](docs/GITHUB_CODEX_WORKFLOW.md#everyday-sync) to pull changes and push reviewed commits. Git sync happens when you run these commands; saving a file does not upload it automatically.

For a new computer or checkout:

```powershell
git clone https://github.com/cevateness/winterops-databricks-lab.git
cd winterops-databricks-lab
python -m pip install -e .
python -m unittest discover -s tests -v
```

The task in `docs/CODEX_CLOUD_TASK.md` can be implemented locally; Cloud selection is deferred. For optional Databricks CLI access, use `docs/WINDOWS_SETUP.md`. A live workspace target, reviewed source hash and user approval are required before applying the new views; see `docs/ANALYTICS_SLICE.md`.

## Run offline checks

Python 3.10+; no Spark installation required for basic tests:

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
python scripts/validate_quality_snapshot.py data/fixtures/windsor_week_2026_01_12_18_summary.json
```

The aggregate fixture verifies **reported** invariants; it does not query Databricks or replace integration tests.

The expanded suite has 110 tests: existing analytics/contracts plus synthetic V2 revisions, policy changes, reruns, multiple weeks, interruptions, corruption/repair, source-quality edge cases, lossless gzip transport and SQL/Python reconciliation. SQLite tests adapt dialect/type details; they do **not** verify native V2 Spark/Delta writes or privileges. Notebook 06 defaults to `mode=render`; its apply path requires explicit approval and must not be used to replace the existing published views by default. The product and V2 plan renderers never execute SQL or create objects.

## Data handling, attribution and source claims

Raw operational CSVs, downloaded telemetry, Delta/Parquet files, database credentials, workspace profiles, API tokens, and personal files must **not** be committed. Use the synthetic demo fixture and aggregate reporting samples for the public repository. The original real file remains in the user's Databricks workspace.

When using public City of Windsor information, provide attribution:

> Contains information licensed under the Open Government Licence – The Corporation of the City of Windsor.

Licence: https://opendata.citywindsor.ca/Documents/OpenDataTermsofUse.pdf . The city does not endorse this project. Code licensing is **not yet selected**; public visibility does not by itself grant code reuse rights. Choose and add an explicit license before an intended open-source release.

Databricks Free Edition is for personal/non-commercial development and has quotas, security, and reliability limitations. Any future commercial system will require separate data-use, platform, and customer validation.

## Project boundaries

- No connection/migration from Sports-Market-Edge or industrial ETA Estimator.
- No claimed GPS coverage, working hours, response SLAs, workforce availability or savings inferred directly from counts of records.
- No assumption that a vehicle ID identifies a dedicated snowplow.
- No deletion of source observations in Bronze; quarantine questionable Silver records.
- No forecast leakage: historic **actual** weather must not be substituted for forecast data that existed at decision time.

Read `AGENTS.md`, `docs/STATUS_HANDOFF.md`, and the project charter before making changes.
