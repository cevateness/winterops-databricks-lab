# Lesson 7 — Controlled Silver/Gold publication

**Phase A: BLOCKED pending creation-privilege verification and separate publication approval. Phase B: NOT RUN.**

Read-only preflight performed on 2026-10-28. This is a verification gap, not an observed DDL permission denial: no DDL was submitted to test permissions.

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
| Effective schema creation privilege for current identity | UNRESOLVED; see below |
| Target metadata lookups | Each returned HTTP 404 / `TABLE_DOES_NOT_EXIST`; full namespace visibility is unconfirmed |

Selected source-file SHA-256: `f5d7633c910e1ad6be23b4111445bf0bc14fe2071c6ea0f0d4cd456295ea9e94`.

Dataset, filename, canonical Volume path and half-open source-local/naive window are unchanged from [SOURCE_VERSION_EVIDENCE.md](SOURCE_VERSION_EVIDENCE.md). Preflight reconfirmed Bronze/Silver = 110,337 each; HEADER = 26; VALID = 110,311; other INVALID = 0; valid truck identifiers = 251; plow-active observations = 79,471; spreader-active observations = 68,870. No source records or vehicle identifiers were returned.

Six bounded read-only SQL statements succeeded: two identity/group-membership diagnostics plus the four source/schema/checksum checks above. Native source assertions, payload checks and checksum were not retried. There were no Databricks SQL runtime errors, cancellations or truncated results. An initial local helper binding error was corrected before any SQL submission.

SQL requests used a 30-second wait with `on_wait_timeout=CANCEL`, 25-row/65,536-byte inline result limits and hard 45-second client deadlines, with no automatic retries. Metadata requests used bounded deadlines. No resource configuration, object, data, grant, owner, job or schedule was changed.

## Ownership, grants and conflict assessment

Readable catalog grants include `USE_CATALOG`; schema grants include `USE_SCHEMA` and `CREATE_TABLE`, which is the schema privilege required by CREATE VIEW. Their grantee and owner principals could not be matched to the current SQL/SCIM identity, its aliases, or its SCIM groups/identifiers. Literal membership probes for those principals returned false. SCIM confirms membership in the workspace `users` and `admins` groups, but that alone was not used to assert ownership of these Unity Catalog containers.

Working source SELECTs demonstrate effective catalog/schema usage and source read access. They do **not** prove CREATE VIEW authority. No permission denial was observed; creation privilege attribution remains unverified. Catalog Explorer or another authoritative read-only privilege inspection must resolve this before `READY_TO_APPLY`.

| Exact target | Accessible metadata | Current publication verification |
|---|---|---|
| `workspace.default.winterops_silver_windsor_valid` | 404 / not found in accessible metadata | NOT PUBLISHED BY THIS WORK; not verified |
| `workspace.default.winterops_silver_windsor_quarantine` | 404 / not found in accessible metadata | NOT PUBLISHED BY THIS WORK; not verified |
| `workspace.default.winterops_gold_windsor_hourly_observations` | 404 / not found in accessible metadata | NOT PUBLISHED BY THIS WORK; not verified |

There is no accessible target owner, definition or direct grant set to inspect. Because full namespace visibility is not established, these 404 responses are not treated as proof that unrelated hidden objects cannot exist. Parent grants were inspected without changing them. Any existing target discovered later requires review; no replacement is authorized.

## Concrete publication proposal — not executed

The package templates currently use `CREATE OR REPLACE VIEW`. For this first controlled publication, propose **CREATE VIEW only**, without `OR REPLACE` or `IF NOT EXISTS`. This changes only the DDL prefix; SELECT bodies and comments remain identical. A concurrently created or hidden object will cause failure rather than replacement or an ignored no-op. Existing templates and notebooks were not modified.

Prepared ignored artifacts:

- `.venv/winterops-lesson7-create-only.sql`: the exact three proposed definitions.
- `.venv/winterops-lesson7-postflight.sql`: existing reconciliation statement.
- `.venv/winterops-lesson7-published-summary.sql`: proposed safe aggregate query, not runtime-tested yet.
- `.venv/winterops-lesson7-publication-plan.json`: limits, exact targets and current blockers.

After privilege verification and explicit approval of the three exact targets:

1. Reconfirm workspace/warehouse, schema, source preflight, payload preflight and exact CSV hash. Reinspect target metadata and source stability. Stop on any mismatch or conflict.
2. Execute create-only definitions sequentially: valid Silver, quarantine Silver, then hourly Gold. Stop on the first error, cancellation or unexpected result. Inspect each created object's identity, owner and definition before proceeding; do not change grants.
3. Execute the existing postflight assertions against the published views.
4. Return one safe summary row: hourly bucket count, observation/plow/spreader/repeated-payload totals, hourly truck-count minimum/maximum and an ordered JSON array of per-hour distinct-truck counts. No truck identifiers are selected. At most 168 hourly entries fit within the response cap; truncation is a failure. Do not sum hourly distinct-truck counts into a weekly truck count.
5. Require totals of 110,311 valid observations, 79,471 plow-active observations and 68,870 spreader-active observations. Repeat only read-only postflight and summary, comparing results for stability.

Proposed maximum: **11 SQL statements**, including four source/schema/checksum checks, three DDL statements and four post-publication/read-repeat statements. Each retains the 30-second wait/CANCEL, 25-row/65,536-byte response and 45-second client bounds. Metadata inspection is read-only and bounded. No automatic retries, warehouse configuration edits, jobs, schedules or extra ingestion are included.

No Gold summary or hourly truck counts have been queried from published views in Phase A. Lesson 6 candidate reconciliation remains separate evidence; it is not proof of published-view results. Neither phase uses the Databricks notebook or Spark entrypoint.

## Non-atomic recovery and rollback

The three DDL statements are not one transaction. Create-only execution is intentionally not an idempotent DDL rerun: an existing name must fail and be reviewed. Stable read-only verification does not establish repeated publication behavior.

- Record each successful creation and its object identifier, owner, definition and accessible grants privately. If a later step fails, stop and report the exact partial state. Do not retry or replace objects automatically.
- A client timeout or cancellation can leave DDL outcome uncertain. Inspect exact target metadata before inferring success, failure or any recovery action.
- Prefer a reviewed forward recovery of only missing definitions after source/privilege rechecks and renewed approval. A failure does not authorize resuming publication.
- Rollback would require **separate explicit approval**. Only newly created, still-identical objects attributable to this run may be considered, in reverse dependency order: Gold, quarantine, valid. Never drop a table, unrelated object, pre-existing object, or any Bronze/Silver source. If ownership, identity or definition changed, stop for review.
- No automatic DROP, grant restoration, owner transfer or warehouse change is included in the proposed publication approval. No rollback/recovery operation has run.

## Approval boundary

No DDL is currently approved. Resolve the creation-privilege verification gap, then explicitly approve create-only publication of the three exact targets above against the existing `winterops` workspace/warehouse and verified hash. Approval cannot silently extend to replacements, grant/owner changes, rollback DDL or notebook execution.

References reviewed: [CREATE VIEW privileges and replacement behavior](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-ddl-create-view), [effective grants](https://docs.databricks.com/api/uc-grants/v1/get-effective-permissions), [table metadata visibility](https://docs.databricks.com/api/uc-tables/v1/get-table), [workspace/account group membership](https://docs.databricks.com/aws/en/sql/language-manual/functions/is_member).
