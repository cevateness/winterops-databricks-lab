# WinterOps — Coding Agent Instructions

This repository is the **canonical source of code and documentation** after GitHub publication. Read `PROJECT_REFERENCE.md` and `docs/STATUS_HANDOFF.md` before working. Only modify what the current task authorizes.

## Engineering constraints

- Preserve **learning MVP / research extension / future commercial option** as distinct scopes. No speculative startup infrastructure.
- Prefer portable, testable Python modules, Spark SQL and Databricks Free Edition-compatible jobs; use notebooks as small entrypoints, not as the sole home of business logic.
- Existing Bronze and Silver exercises are completed **based on user-shared workspace SQL results**. They are not verified from this cloud/CI environment. Do not rewrite them destructively to make tests pass.
- Keep raw ingestion auditability: one original parsed CSV observation per Bronze row; do not deduplicate repeated GPS records solely from their payload hash.
- Keep `HEADER` / `INVALID` classification auditable; expose clean Silver view(s) for Gold without altering Bronze.
- Use the actual source JSON keys: `Truck`, `Date time`, `Latitude`, `Longitude`, `Plow status`, `Spreader status`, `Engine status`.
- `event_time_unzoned` is `TIMESTAMP_NTZ`. Do not label it UTC, infer the timezone, or convert it to an instant without evidence.
- `quality_status='VALID'` covers explicit parsing/domain checks only; it is not proof of service coverage or plowing.
- 110,337 Bronze rows, 26 HEADER, 110,311 VALID, 0 other INVALID, 251 truck identifiers: **reported observations for one file version**, not hard-coded general thresholds for every future dataset.
- Never infer working hours, kilometers serviced, road coverage, SLA attainment or productivity from raw GPS-record counts without validating observation cadence and route geometry.
- Any Gold hourly time buckets based on `event_time_unzoned` must be named **source-local/naive** and count observations rather than minutes worked.

## Safety / repeatability

- Public repo: do not commit raw operational datasets, credentials, access tokens, `.databrickscfg`, `.env` files, real customer files, or detailed unreviewed vehicle trajectories.
- Do not print tokens, credential files, or private Databricks URLs into GitHub Actions logs, commits or public reports. Store Databricks auth only in approved local profiles or protected deployment credentials when formally enabled.
- Codex Cloud does **not** have the user's local browser sign-in or their Databricks workspace data by default. Lack of connectivity is a **blocked integration test**, not permission to invent successful results.
- Never mutate/delete existing Databricks tables or enable scheduled jobs by default. Any remote execution requires validated auth, explicit workspace target, bounded resource usage and user approval.
- No destructive force pushes, repo replacement, automatic raw-data downloads into Git history, or secret-bearing GitHub Actions.
- Keep all writes idempotent when possible, include scoped version selection, and test rerun invariants.
- Separate pure/offline unit tests from Spark/Databricks integration tests; CI must pass without Databricks access.
- Prefer standard libraries for tiny local quality checks; avoid heavyweight dependencies by default.

## Work report format

On completing a task, report: changed files; local tests and exact results; Databricks tests actually run vs blocked; artifacts/tables affected; assumptions/risks; next sensible, small milestone. Do not claim live success from static inspection.
