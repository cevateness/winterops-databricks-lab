# Architecture decision log

## ADR-001 — Separate public learning lab (2026-10-16)
Keep WinterOps fully separate from proprietary ETA projects and Sports-Market-Edge. Use historical public municipality data; Databricks Free Edition for learning.

## ADR-002 — Preserve raw file and source records (2026-10-21)
Raw CSV is retained in Unity Catalog Volume. For the **real** Windsor feed, Bronze holds one row per Spark-parsed source record, including repeated headers and identical payloads. Original physical CSV line order is not preserved. File and JSON record hashes support traceability; they do not prove data correctness.

## ADR-003 — Separate validation from observation preservation (2026-10-22)
Silver stores typed fields and quality classifications. Header-like rows are `HEADER`; malformed data `INVALID`; explicitly validated rows `VALID`. Keep an audit record for each Bronze observation. Publish a consumer view with `quality_status='VALID'`, and quarantine view separately. Never automatically discard repeated GPS payloads.

## ADR-004 — Code-first, remote execution gated (2026-10-23)
GitHub is canonical source once published; Codex Cloud generates/test code through PR workflow; Databricks runs bounded SQL/PySpark data processing. Code-first does not imply that Codex Cloud inherits local Databricks credentials or that Free Edition permits every API. Start with offline CI; add remote execution only after the user's CLI smoke test passes and a secure cloud auth mechanism is verified.

## ADR-005 — Publishability and licensing (2026-10-23)
Publish project **code, synthetic fixture, documentation, and aggregate QA evidence**, not raw telemetry or sensitive information. City of Windsor attribution required for source-derived results. Public visibility is not the same as granting code reuse; an explicit code license remains an owner decision. Commercial use of Databricks Free Edition is out of scope.

## ADR-006 — Local development while Cloud selection is deferred (2026-10-25)
The user reports publishing a Cloud environment but cannot select it in the extension. Continue the repository task locally on a feature branch with offline CI and a review PR. Preserve the Cloud environment and its draft; do not make Cloud setup a prerequisite for code development.

## ADR-007 — Exact-version, observation-only consumer views (2026-10-25)
Prepare three views: `VALID` Silver, quarantine Silver and source-local/naive hourly Gold observations. Require a reviewed file SHA-256, full source identity, a window of at most seven naive days and explicit expected aggregate evidence. Validate schema, counts and payload multiplicities before DDL; retain all Bronze/Silver rows and repeated payloads. Use one shared Python SQL plan, offline synthetic tests and a dry-run notebook. View data remains dynamic and multi-view publication is not transactional; rerun QA when source tables change. Databricks integration is blocked until actual target/auth/resource approval, never inferred from offline tests.

## ADR-008 — Minimal read-only CLI acceptance gate (2026-10-25)
Use the official standalone CLI through a dependency-free Python checker, with a PowerShell wrapper. Require a named local profile and matching expected HTTPS workspace host. Capture CLI output, report sanitized statuses, bound timeouts and keep the Jobs metadata probe optional. No SDK, bundle, job submission or schedule is added. Authentication and any later workspace writes remain separate explicit actions.
