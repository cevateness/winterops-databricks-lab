# Lesson 7 — Controlled Silver/Gold publication

**Phase A: PASS. Phase B: PUBLISHED_VERIFIED_STABLE after explicit approval.**

Read-only preflight performed on 2026-10-28. The initial principal-attribution gap was resolved by the user's Catalog Explorer confirmation, corroborated by current API metadata and SCIM memberships. No DDL was submitted during Phase A. After a separate explicit approval, Phase B created all three views and passed postflight plus repeated read-only verification on the same date.

## Repository and validated implementation

- PR #2 merged at `2645dc9`; its validated head is `adb732e`. CI passed for both commits.
- Follow-up branch: `feat/lesson7-publication-preflight`, based on merged `origin/main`. The merged tree matches the validated PR head.
- Original uncommitted `.gitignore`, `.vscode/settings.json` and `databricks.yml` bytes were snapshotted and preserved. They are not part of this change.
- The two source preflight statements and candidate CTE statement reproduce the exact query hashes from the successful Lesson 6 run. All three publication SELECT bodies occur unchanged in that validated candidate plan, with only prospective view references replaced by statement-local aliases during validation.

## Actual Phase A results

| Check | Actual outcome |
|---|---|
| Authenticated identity and expected warehouse | PASS; SQL identity matches SCIM identity; same previously verified warehouse/configuration |
| Silver required schema | PASS; all 17 required types, including `TIMESTAMP_NTZ`; 18 metadata rows |
| Existing source preflight | SUCCEEDED; all six assertions PASS |
| Existing payload preflight | SUCCEEDED; payload assertion PASS |
| Exact current Volume CSV | PASS; 8,671,212 bytes; byte hash matches selected version |
| Catalog/schema metadata and direct/effective grants | Readable, HTTP 200 |
| Schema creation privilege | CONFIRMED by user in Catalog Explorer and corroborated by current workspace-users grant/SCIM metadata |
| Target metadata lookups | Each returned HTTP 404 / `TABLE_DOES_NOT_EXIST`; full namespace visibility is unconfirmed |

Selected source-file SHA-256: `f5d7633c910e1ad6be23b4111445bf0bc14fe2071c6ea0f0d4cd456295ea9e94`.

Dataset, filename, canonical Volume path and half-open source-local/naive window are unchanged from [SOURCE_VERSION_EVIDENCE.md](SOURCE_VERSION_EVIDENCE.md). Preflight reconfirmed Bronze/Silver = 110,337 each; HEADER = 26; VALID = 110,311; other INVALID = 0; valid truck identifiers = 251; plow-active observations = 79,471; spreader-active observations = 68,870. No source records or vehicle identifiers were returned.

Six bounded read-only SQL statements succeeded: two identity/group-membership diagnostics plus the four source/schema/checksum checks above. Native source assertions, payload checks and checksum were not retried. There were no Databricks SQL runtime errors, cancellations or truncated results. An initial local helper binding error was corrected before any SQL submission.

SQL requests used a 30-second wait with `on_wait_timeout=CANCEL`, 25-row/65,536-byte inline result limits and hard 45-second client deadlines, with no automatic retries. Metadata requests used bounded deadlines. No resource configuration, object, data, grant, owner, job or schedule was changed.

## Ownership, grants and conflict assessment

Readable catalog grants include `USE_CATALOG`; schema grants include `USE_SCHEMA` and `CREATE_TABLE`, which is the schema privilege required by CREATE VIEW. The user confirmed the CREATE TABLE assignment on `workspace.default` in Catalog Explorer through its workspace-users system principal. The full principal identifier remains private.

Follow-up API metadata recognized `_workspace_users_workspace_<workspace-id>` as the catalog/schema grantee and the corresponding workspace-admins system principal as their owner. All share the same workspace namespace. SCIM confirms that the current identity belongs to workspace `users` and `admins`. These checks corroborate the user's confirmation and resolve the earlier mismatch against literal SQL/group-name probes; no permission or ownership change was needed.

Working source SELECTs establish effective usage/read access. Creation readiness additionally relied on the explicitly confirmed schema grant and corroborating metadata. That permission confirmation was **not** publication approval: publication proceeded only after the user separately answered yes to the exact three-object create-only request. Successful Phase B CREATE VIEW execution now confirms creation authority for this run.

| Exact target | Phase A baseline | Phase B publication verification |
|---|---|---|
| `workspace.default.winterops_silver_windsor_valid` | 404 | CREATED; type VIEW, owner and definition verified; 110,311 observations reconcile |
| `workspace.default.winterops_silver_windsor_quarantine` | 404 | CREATED; type VIEW, owner and definition verified; 26 observations reconcile |
| `workspace.default.winterops_gold_windsor_hourly_observations` | 404 | CREATED; type VIEW, owner and definition verified; 79 hourly buckets reconcile |

The Phase A 404 responses were not used as proof of global absence. Phase B repeated the target lookups and used fail-if-exists CREATE VIEW, so a hidden or racing object could not be silently replaced. After each successful creation, the new object identifier, type, authenticated-creator ownership, definition and readable direct/effective grants were inspected. Identifiers/identities and grant snapshots remain private. No replacement, grant or owner change was requested; parent grant snapshots remained unchanged.

## Approved create-only publication — completed

The package templates use `CREATE OR REPLACE VIEW`. This approved first publication executed **CREATE VIEW only**, without `OR REPLACE` or `IF NOT EXISTS`. Only the DDL prefix changed; validated SELECT bodies and comments remained identical. Existing package templates and notebooks were not modified.

Prepared ignored artifacts:

- `.venv/winterops-lesson7-create-only.sql`: the exact three proposed definitions.
- `.venv/winterops-lesson7-postflight.sql`: existing reconciliation statement.
- `.venv/winterops-lesson7-published-summary.sql`: safe aggregate query, now executed successfully twice.
- `.venv/winterops-lesson7-publication-plan.json`: original scope, exact targets and limits.
- `.venv/winterops-lesson7-phaseb-f240d60.json`: sanitized runtime report; object/statement identifiers remain local.

The approved procedure executed once from commit `f240d60`:

1. Reconfirm workspace/warehouse, schema, source preflight, payload preflight and exact CSV hash. Reinspect target metadata and source stability. Stop on any mismatch or conflict.
2. Execute create-only definitions sequentially: valid Silver, quarantine Silver, then hourly Gold. Stop on the first error, cancellation or unexpected result. Inspect each created object's identity, owner and definition before proceeding; do not change grants.
3. Execute the existing postflight assertions against the published views.
4. Return one safe summary row: hourly bucket count, observation/plow/spreader/repeated-payload totals, hourly truck-count minimum/maximum and an ordered JSON array of per-hour distinct-truck counts. No truck identifiers are selected. At most 168 hourly entries fit within the response cap; truncation is a failure. Do not sum hourly distinct-truck counts into a weekly truck count.
5. Require totals of 110,311 valid observations, 79,471 plow-active observations and 68,870 spreader-active observations. Repeat only read-only postflight and summary, comparing results for stability.

Actual total: **11 SQL statements**, including four source/schema/checksum checks, three DDL statements and four post-publication/read-repeat statements. All were HTTP 200 / SUCCEEDED. Each used the 30-second wait/CANCEL, 25-row/65,536-byte response and hard 45-second client bounds. No truncation, runtime error, cancellation, automatic retry or rollback occurred. Warehouse configuration and parent grants were re-read and unchanged. No jobs, schedules or extra ingestion were introduced.

## Actual published-view results

| Metric | Published result |
|---|---:|
| Hourly buckets with observations | 79 |
| Total valid observations | 110,311 |
| Plow-active observations | 79,471 |
| Spreader-active observations | 68,870 |
| Repeated-payload observations | 2,210 |
| Minimum per-hour distinct truck identifiers | 1 |
| Maximum per-hour distinct truck identifiers | 20 |

Both existing published postflight assertions passed twice. The two Gold summary results, including all 79 ordered hourly distinct-truck counts, matched exactly. Full safe aggregate results and sanitized statement statuses are in [LESSON_7_GOLD_RESULTS.json](LESSON_7_GOLD_RESULTS.json). No truck identifiers, coordinates or raw observations were returned or committed.

The 79 buckets are source-local/naive hours containing observations, not hours worked. Missing hours do not establish inactivity; repeated-payload observations include all valid observations belonging to repeated payloads, not only excess copies. Hourly truck counts must not be summed into a weekly distinct count. Source timezone remains unverified.

Lesson 6 candidate validation and this actual published-view verification are separate evidence. Neither executed the Databricks notebook or its Spark entrypoint. CREATE VIEW, persistent-view resolution, native NTZ/hour construction and the aggregate JSON summary all ran successfully on the tested warehouse. No runtime compatibility issue was observed in this scope.

## Non-atomic recovery and rollback

The three DDL statements are not one transaction. Create-only execution is intentionally not an idempotent DDL rerun: an existing name must fail and be reviewed. Stable read-only verification does not establish repeated publication behavior.

This run completed all three creations and both verification passes; no partial failure or rollback occurred. The following recovery procedure remains applicable to a future separately approved operation, not an authorization to change the published views now.

- Record each successful creation and its object identifier, owner, definition and accessible grants privately. If a later step fails, stop and report the exact partial state. Do not retry or replace objects automatically.
- A client timeout or cancellation can leave DDL outcome uncertain. Inspect exact target metadata before inferring success, failure or any recovery action.
- Prefer a reviewed forward recovery of only missing definitions after source/privilege rechecks and renewed approval. A failure does not authorize resuming publication.
- Rollback would require **separate explicit approval**. Only newly created, still-identical objects attributable to this run may be considered, in reverse dependency order: Gold, quarantine, valid. Never drop a table, unrelated object, pre-existing object, or any Bronze/Silver source. If ownership, identity or definition changed, stop for review.
- No automatic DROP, grant restoration, owner transfer or warehouse change is included in the proposed publication approval. No rollback/recovery operation has run.

## Approval boundary

The separate Phase B approval was consumed by this completed create-only run. It does not authorize replacements, repeated DDL, grant/owner changes, rollback DDL or notebook execution. Views read the current source tables rather than immutable snapshots: recheck source/preflight and postflight before future use. This run verifies stable repeated reads, not a multi-object transaction, future source stability or DDL rerun invariants.

References reviewed: [CREATE VIEW privileges and replacement behavior](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-create-view), [effective grants](https://docs.databricks.com/api/uc-grants/v1/get-effective-permissions), [table metadata visibility](https://docs.databricks.com/api/uc-tables/v1/get-table), [workspace/account group membership](https://docs.databricks.com/aws/en/sql/language-manual/functions/is_member).
