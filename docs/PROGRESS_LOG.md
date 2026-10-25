# WinterOps — Progress log

## 2026-10-18 — Kickoff

**Scope decision:** Independent Databricks Free Edition learning lab; historical Windsor pilot; source feasibility and one-file Bronze ingestion only. No integration with existing ETA or sports systems. No commercialization work in this milestone.

### Completed or prepared

- [x] Reviewed the project charter and preserved its phase boundaries.
- [x] Verified that Windsor’s public catalogue **lists** weekly snowplow activity CSVs and documented the change to the new portal.
- [x] Reviewed the Windsor Open Government Licence (attribution, exceptions, non-endorsement).
- [x] Produced a source register and Phase 0 checklist; distinguished the historical activity CSV from a possible replacement **routes** layer.
- [x] Created a local repo skeleton, labeled synthetic fixture, CSV profiler, Databricks Bronze notebook, SQL checks, and standard-library tests.
- [x] Ran 3 local tests successfully and compiled the notebook as Python syntax.

### Not completed / not claimed

- [ ] Successfully downloaded and inspected a real City of Windsor snowplow activity file.
- [ ] Verified the field schema, event times, coordinate reference, status semantics, and row-level quality of the real file.
- [ ] Created a GitHub remote repository.
- [ ] Created or accessed a Databricks workspace or executed the Bronze notebook there.
- [ ] Built typed Silver, Gold, ML models, or optimization.

### Next evidence gate

A. Run the synthetic fixture through Databricks (run twice; expect 0 new unique rows on the rerun).
B. Obtain and profile one real weekly official Windsor activity CSV; evaluate schema and actual spatial-temporal observations.

**Important:** A synthetic notebook success is a tooling proof, not evidence that the Windsor real-data ingestion or downstream service-quality metrics are valid.

## 2026-10-18 — Lesson 2 prepared (Bronze → Silver)

**User progress:** Reports successfully completing the initial Databricks setup and getting 4/4 on the conceptual quiz; actual platform outputs have not been independently inspected.

- [x] Created `02_silver_typing.py` for the **synthetic fixture only**. It parses JSON to typed columns, flags record-quality issues, retains multiplicity and source provenance, and overwrites an isolated demo Silver table.
- [x] Added `sql/silver_checks.sql`, lesson guide, and local synthetic-contract tests.
- [ ] Executed Silver notebook and inspected results in the user's Databricks workspace.
- [ ] Obtained real Windsor weekly activity bytes and validated its schema/timezone.

**Design note:** The synthetic timestamps are timezone-naive and stored as `TIMESTAMP_NTZ`, not mislabeled UTC. Real-source processing requires a separate verified schema and appropriate event-time handling.

## 2026-10-18 — Databricks Lessons 1 and 2 user-verified; Lesson 3 prepared

**User-reported completion:** Both synthetic Bronze and Silver notebooks ran in the user’s Databricks Free Edition workspace, and all provided SQL validation checks were executed and viewed successfully. Raw platform outputs have not been shared; this is not an independent runtime audit. User also scored 4/4 on a short conceptual check.

- [x] Synthetic Bronze → Silver workflow exercised by user in Databricks.
- [x] Prepared read-only `03_profile_real_csv.py` source-profiling notebook and lesson guide.
- [ ] Acquired genuine weekly Windsor activity CSV bytes (legacy catalogue lists downloads; availability from our environment unconfirmed).
- [ ] Audited real schema, geographic CRS, timestamp/timezone and operational status fields.
- [ ] Designed real telemetry Bronze/Silver ingestion and acceptance tests.

**Guardrail:** Static Snow Plow Routes / Areas GIS layers are not substitutes for historical 15-second vehicle activity observations.

## Lesson 4 handoff (2026-10-21)

- User reported finishing the Lesson 3 Databricks notebook and its checks; individual field-profile outputs were **not shared** for independent review.
- Confirmed from source code that Lesson 3 is read-only: it does **not** import records into a Delta table.
- Prepared a separate real-data Bronze notebook and validation SQL; **not yet run or independently validated in the user's Databricks workspace**.
- The real Bronze approach intentionally preserves each original parsed CSV observation as a separate Delta row, in contrast with the synthetic aggregate-count demonstration.
- Next acceptance gate: run real Bronze ingestion twice, confirm row-count equality, inspect schema and validate a proposed real Silver data contract from actual profiling evidence.

## 2026-10-22 — Real Bronze quality review / Lesson 5 prepared
- User-reported SQL result: 110,337 Bronze observations in weekly Windsor file, 26 repeated in-body CSV headers, 110,311 candidate data rows and zero basic coordinate failures among candidates.
- Lesson 5 real Windsor Silver transformation **prepared**, not executed/validated in Databricks yet.
- Lesson 5 deliberately retains all observed rows and flags possible duplicates; avoids unverified timezone conversion or service-area validation.
- Await actual Databricks outputs and SQL quality report before claiming Lesson 5 complete.

## 2026-10-23 — Canonical GitHub/Codex transition package

- User shared final real Silver QA: 110,337 Bronze and Silver rows, 26 HEADER, 110,311 VALID, 0 other INVALID; 251 distinct truck IDs and status observation counts.
- Earlier documentation claiming the real source was not ingested is obsolete; `README.md` and `docs/STATUS_HANDOFF.md` are authoritative for current handoff.
- Requested a public GitHub canonical source and Codex Cloud; local Windows `winget` is unavailable.
- Prepared offline CI, portable PowerShell CLI installer, optional API checks and initial Git publishing script. These were **not executed on the user’s machine**, and the GitHub remote/environment is **not yet created**.
