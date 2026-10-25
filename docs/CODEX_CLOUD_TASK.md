# Codex Cloud task — WinterOps canonical repository hardening and next analytics slice

Use this document as the **initial coding-task prompt** in the published Codex Cloud environment. Repository root is the canonical `winterops-databricks-lab` repo. Review `AGENTS.md`, `PROJECT_REFERENCE.md`, `docs/STATUS_HANDOFF.md`, `docs/DECISIONS.md` first.

## Context (already achieved, user-reported)

We are building an independent, public Databricks Free Edition **learning** project for municipal winter operations, not migrating a separate industrial ETA estimator or sports project. Existing Python notebooks 01–05 (synthetic Bronze/Silver; Windsor CSV profiling; real Bronze; real one-week Silver) are already preserved in the repository. The user ran notebooks and SQL checks in Databricks and reported for `snowplow-2026-01-12_2026-01-18.csv`: **110,337** Bronze rows, **110,337** Silver rows, **26** repeated headers (`HEADER`), **110,311** `VALID`, **0** other invalid, **251** distinct truck IDs; 79,471 plow-active observations and 68,870 spreader-active observations. These metrics are **observational reports from the user's workspace**, not an available raw dataset or CI-executed integration test. Actual event timezone, duplicate nature, road coverage, and eastern longitude outliers are unresolved. Do not misrepresent them.

The user attempted `winget install Databricks.DatabricksCLI` on Windows PowerShell, but `winget` is not recognized. This repo includes `scripts/install_databricks_cli.ps1` (official GitHub binary fallback) and `scripts/test_databricks_connection.ps1` (read-only API probe); **cloud tasks must not assume they can run on the user's Windows computer or inherit local OAuth credentials**.

## Required tasks (ordered, independently testable)

1. **Audit & align repository:** Run the existing standard-library test suite and aggregate QA fixture validator. Verify README and handoff match the actual notebook code and user-reported observations; fix documentation drift rather than claiming unverified execution. Keep all five lesson notebooks and their original SQL checks accessible. Review GitHub Actions for safe offline checks. If public-source attribution or license terms appear unclear, document uncertainties without inventing rights.
2. **Refactor minimally for maintainability:** Create small, portable, pure-Python modules for configuration/data-contract validation where appropriate. Avoid re-implementing Databricks APIs. Centralize table names and safe defaults only where this reduces drift. Do not rewrite Bronze or single-week Silver semantics accidentally. Keep notebooks as thin executable entrypoints when practical, but preserving working baseline takes priority.
3. **Publish clean Silver access:** Introduce idempotent `VALID` and quarantine consumer views (or carefully justified equivalents) sourcing `workspace.default.winterops_silver_windsor_week_sample`. Preserve full audit-classified Silver table and original Bronze. Write SQL assertions/reconciliation checks that detect a wrong source version or unexpected row changes. Do not delete header records from Bronze or silently deduplicate genuine repeats. Implement view creation as an explicit, reviewable, bounded step, not automatically during unrelated setup.
4. **First Gold data product:** Build a *small* hourly observation-count table or view based on the **validated** Silver consumer only. Group by hour of `event_time_unzoned` (`TIMESTAMP_NTZ`), and optionally truck/status. Name hour buckets as **source/unzoned**, not UTC. Provide metrics for total/plow-active/spreader-active **observation counts**, distinct truck IDs, and flagged duplicates if useful. Do NOT call them work hours, cleared road kilometers, response times, fleet capacity or route coverage. Limit the initial job to the one validated week; guard against multi-version Bronze leakage.
5. **Tests and CI:** Add local tests for parsing/counters/schema policy/invariant checks using synthetic fixtures, plus SQL text/plan checks when a Spark engine isn't available. Separate offline unit tests from Databricks integration tests. GitHub Actions must run **without Databricks secrets, production data, or billable remote compute**. Show exact commands and results. Avoid introducing heavy Spark dependency into a small offline CI job merely to parse a fixture.
6. **Programmatic deployment investigation:** Confirm the current Databricks CLI/SDK commands, workspace-level API access possibilities and Free Edition limitations. Provide a safe, optionally runnable deployment/check script (CLI/SDK or bundle if supported) that targets a named **profile** and named **workspace**, runs read-only checks by default, and never creates long-running or billable jobs without explicit user action. If cloud auth isn't available, leave clear `BLOCKED` integration-test status and document the one-time **local** CLI smoke test instead of pretending to execute it.
7. **Improve portfolio:** Add a short architecture illustration in Markdown/Mermaid if useful, explain separation of observed GPS records vs actual winter-service performance, document source licensing/attribution and public-data exclusions, and update `docs/STATUS_HANDOFF.md`/`docs/DECISIONS.md` with actual accomplished work.

## Explicit non-goals

- No downloading/committing full City of Windsor telemetry into this public repo; no Git LFS for raw data as a workaround.
- No sharing/seeking user tokens in code review, prompts or git files.
- No destructive overwrite of existing Bronze/Silver or changes in a real Databricks workspace by default.
- No premature weather prediction, real-time integration, snow-routing optimization, or commercial/production infrastructure.
- No claim that dashboard measurements represent plowed road lengths, crew hours, or confirmed service coverage.
- Do not spend time fixing the user's local Windows package manager within a remote Linux cloud agent; provide/check the documented fallback instead.

## Acceptance criteria

- Offline CI and unit tests pass and are reproducible from a clean clone.
- Existing Lessons 1–5 remain accessible and their results/contracts are accurately documented.
- Code or SQL for clean/quarantine Silver consumers and one honest Gold hourly observation-count product is present, idempotent, with source/version/quality guards.
- Data quality reconciliation explicitly handles 110,337 total / 26 headers / 110,311 valid as a **one-week reported fixture**, not a global hardcoded invariant.
- Public repository contains no secrets/raw telemetry.
- Windows CLI installation alternatives and exact Databricks connectivity probe are documented; no unsupported cloud credential claims.
- Deliver a concise final report: changed files, tests with results, remote checks genuinely run versus blocked, architectural decisions and residual risks. Open a PR for review rather than force-pushing main.

Begin with a repo audit and small verified commits/PR scope; do not ask the user to repeat facts recorded in `docs/STATUS_HANDOFF.md`.
