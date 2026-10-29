# WinterOps — Project Reference

**Working name:** WinterOps  
**Subtitle:** Weather-Driven Municipal Operations Intelligence  
**Project type:** Independent Databricks learning laboratory with optional future commercialization  
**Status:** One-week source evidence and published Silver/Gold views SQL-verified; repeated published-view reads stable; notebook/Spark entrypoint remains untested
**Reference date:** 2026-10-16; updated 2026-10-29

## 1. Purpose

Build a **reproducible, data-driven demonstration of winter municipal service operations** that integrates historical weather, snowplow activity, service requests, and road-network information to support operational analytics, workload forecasting, and eventually resource-allocation decisions.

**Primary objective — learning:** Develop hands-on, industry-relevant capabilities in cloud data engineering, data architecture, data quality, analytics engineering, MLOps, and the interface between machine learning and mathematical optimization, using Databricks Free Edition wherever practical.

**Secondary objective — portfolio:** Publish a technically credible, well-documented project with reproducible pipelines, meaningful evaluation, honest assumptions, and no confidential data.

**Long-term option — business:** If evidence supports it, evolve the work into a weather-aware planning and decision-intelligence solution for municipalities, snow-removal contractors, campuses, airports, or other facilities. This is **not** a commitment to build or launch a commercial product at this stage.

## 2. Problem framing

Operational questions the project may progressively address:

1. **Before a snow event:** Which geographical zones may require service, how much workload is expected, and what fleet/crew capacity may be required?
2. **During an event (future capability):** Where might coverage delays or service-level violations arise, and how could resources be reallocated?
3. **After an event:** Where and when did service occur? How complete was coverage? What can be learned for future planning?

The intended differentiator is **predictive demand/capacity intelligence and defensible decision support**, rather than another basic fleet GPS dashboard.

## 3. Scope and boundaries

### In scope for the initial learning lab

- **One city and one manageable historical winter period** (initial candidate: Windsor, Ontario, Canada).
- Offline, batch-based analysis with public or appropriately licensed data.
- Snowplow activity ingestion; weather and location/time alignment; spatial and temporal aggregations.
- A simple Bronze → Silver → Gold data model using Delta Lake.
- Data profiling, schema validation, quality checks, incremental/re-runnable processing, and lineage-friendly documentation.
- SQL/PySpark notebooks, lightweight visual analytics, tests, and version-controlled source code.
- Baseline forecast(s) and experimental tracking when the data foundation is reliable.
- Small-scale, **scenario-based** resource-allocation optimization only after predictive and operational definitions are clear.

### Not in scope initially

- Migrating or connecting the existing Sports-Market-Edge or industrial ETA Estimator projects.
- Real-time GPS streaming, 24/7 operations, production APIs, or customer integrations.
- A full vehicle-routing optimizer, mobile application, enterprise security architecture, or monetization.
- Claims of proven operational savings, service improvements, or predictive superiority without appropriate evaluation.
- Publishing restricted data or proprietary business information.

## 4. Candidate data sources (verify availability and license before use)

| Source | Intended role | Key caution |
|---|---|---|
| City of Windsor open data: snowplow activity / winter operations | Historical vehicle activity and coverage patterns | Confirm downloadable fields, temporal coverage, accessibility, and terms |
| City of Windsor winter service requests or other municipal open data | Citizen-reported service demand | A request is not necessarily an actual road service task |
| Open-Meteo historical weather / historical forecasts | Snowfall, temperature, precipitation and forecast features | Distinguish observations/reanalysis from information actually available at decision time; confirm usage rights |
| OpenStreetMap | Road network and road-type context | Respect ODbL attribution and applicable reuse obligations |

The first milestone is **source inspection**, not assuming that all proposed feeds are usable. Keep a data-source register with URL, extraction method, snapshot date, license, schema, spatial coverage, and known gaps.

## 5. Provisional technical architecture

```text
Public datasets / approved downloaded files
          ↓
Bronze Delta tables — raw, timestamped, traceable input
          ↓
Silver Delta tables — typed, quality-classified observations with repeats preserved
          ↓
Gold Delta tables — event / area / time aggregates, model-ready features
          ├── SQL analytics + spatial coverage dashboard
          ├── Forecasting experiments + MLflow
          └── Scenario-based resource allocation + policy comparison
```

**Core learning stack:** Databricks Free Edition, Python, Spark SQL/PySpark, Delta Lake, Unity Catalog, Databricks Jobs/Workflows where supported, Git/GitHub. Use MLflow for suitable modeling experiments. Evaluate Databricks H3 spatial functions for practical geospatial aggregation.

**Modeling / OR approach:** Start with interpretable baselines and simple allocation policies; introduce more sophisticated time-series, spatial models, uncertainty scenarios, and optimization formulations only where they serve a clear question. Keep reusable modeling/optimization logic in portable Python packages rather than embedding everything in notebooks.

**Free Edition principle:** Treat Databricks as a learning and analytics environment, not a permanent commercial host. Minimize unnecessary compute; use sampled historical event windows initially; plan for restricted external connectivity, compute quotas, and application uptime limits.

## 6. Phased progression and evidence gates

| Phase | Main deliverable | Completion evidence |
|---|---|---|
| **0. Source feasibility** | Data inventory and architecture sketch | Verified access, legal reuse considerations, field completeness, feasible scope |
| **1. Data foundation** | Bronze/Silver/Gold historical data pipeline | Re-runnable ingestion, no unintended duplicates, key tests pass |
| **2. Operational analytics** | Spatial-temporal coverage and activity dashboard | Reproducible metrics with clear interpretation and data caveats |
| **3. Prediction** | Weather-related workload / delay baselines | Out-of-time evaluation versus simple baselines; uncertainty and leakage controls |
| **4. Decision analytics** | Fleet/crew allocation policy simulator or optimizer | Explicit capacity assumptions, feasibility checks, comparison with baseline policies |
| **5. Portfolio release** | Public repository, diagrams, reproducibility guide, technical write-up | Another person can follow the workflow and understand limitations |
| **Later: commercial exploration** | Stakeholder interviews and operational pilot hypothesis | Evidence of customer problem, integration feasibility, and measurable value |

These are **stages, not deadlines**. Progress can remain occasional and exploratory. Do not advance a phase merely to add technical complexity.

## 7. Analytical integrity rules

- **No future-data leakage:** For historical decision-time prediction, use weather forecasts and operational information actually available as of the prediction timestamp, rather than later-observed snowfall or later-updated records.
- **Observed vs assumed resources:** GPS or service-request data do not automatically reveal staff hours, service productivity, costs, or true service demand. Label inferred quantities and simulated capacities explicitly.
- **No unverified outcomes:** Scenario-based optimization gains are simulated/counterfactual, not observed municipal savings.
- **Data contracts first:** Document event time, ingest time, IDs, spatial references, null handling, duplicates, and late-arriving records.
- **Evaluation discipline:** Prefer temporally held-out events and sensible baseline models; report performance by storm/event/area where possible.
- **Portability:** Keep data acquisition, transformations, model training, optimization and presentation loosely coupled. Version-control code and key configurations outside Databricks.
- **Licensing and privacy:** Verify source rights before redistribution or commercial use; avoid confidential workplace datasets and personal tracking data in public outputs.

## 8. How to work on this project in ChatGPT

This Project is a **reference workspace** for occasional visits, not a scheduled workflow. On each visit:

- Use this document as the project charter, while incorporating any later decisions documented in the conversation.
- Answer the user's actual question first; do not force the next roadmap step or assume continuous progress.
- Teach relevant engineering concepts through choices and trade-offs, grounded in this application.
- Favor one small, verifiable milestone at a time, with clean examples and explicit acceptance criteria.
- Distinguish confirmed implemented work, experimental proposals, assumptions, and future commercial ideas.
- If a design choice changes, suggest an update to this document or a short decision log.
- When current platform behavior, data availability, pricing, or licenses matter, verify against up-to-date documentation.

## 9. Current decisions and next starting point

**Agreed decisions (2026-10-16):**

- Select **WinterOps** over the other candidate domains for the first Databricks side project.
- Focus on **learning industrial data-engineering / ML practices first**; aim for a public portfolio release later.
- Keep it **fully separate** from existing Sports-Market-Edge and ETA Estimator work.
- Keep **commercial potential** as a design consideration, not an immediate build requirement.
- Start with **Databricks Free Edition** and a historical, offline, modest-size dataset.
- Work **occasionally, on demand**; no automatic cadence or deadlines.

**Updated actual progress (2026-10-23):** The user ran Lessons 1–5 in Databricks Free Edition, including a real Windsor CSV Bronze table and a typed, quality-classified one-week Silver table. For one exact source file version, reported Bronze = Silver = 110,337, with HEADER = 26, VALID = 110,311, other INVALID = 0. These were shared SQL summary results, not independently API-verified by this assistant. Source timezone and exact repeated-payload policy are still open. Keep the private workspace's raw data out of public GitHub.

**GitHub update (2026-10-25):** The canonical public repository is [cevateness/winterops-databricks-lab](https://github.com/cevateness/winterops-databricks-lab). Local Git is connected with `main` tracking `origin/main`. Offline checks pass locally; GitHub Actions provides separate remote CI evidence. This publication does not establish Codex Cloud configuration or Databricks API access.

**Local development update (2026-10-25):** Cloud environment publication is user-reported, but extension selection remains unresolved. The user chose local development for now. Exact-version Silver consumer views, source-local/naive hourly observation counts, offline tests and a profile/host-gated CLI probe are prepared in code. Databricks execution is blocked pending CLI availability, workspace target, reviewed file hash/evidence and user approval; no live objects were created.

**Integration-readiness update (2026-10-28):** The original analytics PR #1 is verified merged. All 46 baseline tests passed; 57 tests now pass with a new read-only Lesson 6 validation mode. No local CLI/profile configuration was found in the checked locations, so no Databricks connection or Spark validation was attempted. The new mode evaluates exact-version candidate consumers and hourly counts without creating views. Bronze/Silver implementations and source data remain unchanged.

**CLI setup and connectivity follow-up (2026-10-28):** The reviewed installer was unblocked and executed with `RemoteSigned` limited to a child process. The official release's SHA-256 check and direct version verification passed: Databricks CLI v1.22.1 is installed locally. Persistent execution policies were unchanged. After user authentication with the corrected workspace origin, the sanitized named-profile checker passed the profile/host match, `current-user me` and `workspace list /Workspace`. No SQL, Spark queries, compute-start requests or Databricks object changes were performed.

**Source-evidence follow-up (2026-10-28):** The existing SQL warehouse and Statement Execution API are accessible. Bounded read-only queries matched the exact stored file SHA-256, canonical path/source metadata, required Silver types, all established one-week aggregates and Bronze/Silver payload multiplicities. No mismatch was found; source data and workspace objects were unchanged. Lesson 6 candidate SQL was prepared offline and stopped at the separate approval gate. See `docs/SOURCE_VERSION_EVIDENCE.md` for the hash, results and limitations.

**Lesson 6 validation follow-up (2026-10-28):** The user approved one bounded SQL API run from `11dba68`. The schema recheck, both unchanged source preflight statements and the existing candidate Silver/Gold CTE statement all succeeded sequentially. All nine assertions passed, including Gold consumer/hourly reconciliation; there were no runtime errors, cancellations, truncation or retries. This validates shared SQL on the existing warehouse; the notebook/Spark entrypoint and publication were not executed. No Databricks objects, source data, jobs, schedules or warehouse configuration were changed.

**Lesson 7 Phase A (2026-10-28):** PR #2 was merged. Source/schema/checksum and existing preflight statements passed; publication SQL matched the validated SELECT bodies. The user confirmed the schema CREATE TABLE grant, corroborated by API metadata and SCIM membership. Phase A was marked READY_TO_APPLY; no DDL ran during that phase. A create-only conflict guard and non-atomic recovery procedure were prepared before the separate Phase B approval. See `docs/LESSON_7_PUBLICATION.md`.

**Lesson 7 Phase B (2026-10-28):** After a separate explicit yes to the three-object bounded publication request, all three views were created with CREATE VIEW only. Fresh prechecks, creation metadata, published postflight and repeated aggregate reads passed within 11 SQL statements. Gold contains 79 source-local/naive hourly buckets, 110,311 observations, 79,471 plow-active, 68,870 spreader-active and 2,210 repeated-payload observations; hourly distinct truck identifiers range from 1 to 20. No runtime error, retry or rollback occurred. Bronze/Silver tables, source files, parent grants, jobs and warehouse configuration were unchanged. The notebook/Spark entrypoint was not executed. See `docs/LESSON_7_GOLD_RESULTS.json` for safe hourly aggregates.

**Gold analytics expansion (2026-10-28):** Work from canonical main `685885c` adds daily activity, equipment-status composition and aggregate fleet-reporting products over the existing exact-version valid Silver/hourly Gold views. Source and per-hour guards plus product reconciliation accompany reusable SQL/Python and a four-chart dashboard specification. All 80 offline tests pass; packaging/syntax/rendering checks pass. No new query was executed in Databricks and no objects or source data were changed. See `docs/GOLD_ANALYTICS_PRODUCTS.md` for metric grains, interpretation limits and native acceptance scope.

**Native Gold validation (2026-10-29):** After PR #4 merged at `402c820` and a separate explicit bounded approval, one schema/clock-probe query, both guards and all eight unchanged products passed through the Statement Execution API. All 11 statements were complete/untruncated, without errors, cancellation or retries. Native NTZ, decimal seconds and ordered gaps passed; observation/status totals reconciled to the existing one-week evidence. The new results include 41,441 plow-only, 30,840 spreader-only and 38,030 both-active observations, 251 observed identifiers and 95 above-threshold gap pairs. These are flag/reporting observations, not workforce, availability, duration or productivity measures. No objects or source files changed. See `docs/GOLD_ANALYTICS_NATIVE_VALIDATION.md` and its sanitized JSON evidence.

**Data Foundation V2 (2026-10-29):** From merged main `929ffd6`, a coherent multi-week implementation adds official discovery/private immutable staging, source-version and processing-policy manifests, reusable Bronze/Silver functions, protected development-table adapters and configurable source-quality diagnostics. The requested January 5–11 and January 19–25 CSVs locally reconcile to 2,810 and 118,159 observations, including 19 and 34 internal headers; no records were lost. An unchanged rerun and earlier-week preservation passed. Nominal 15-second activity-triggered reporting is now confirmed from the official catalogue; timezone/CRS and identifier lifecycle remain unresolved. Only aggregate evidence is published. This original implementation milestone was local only; the separately approved native SQL integration below now verifies the two new versions in isolated development tables. Original tables/views remain unchanged.

**V2 native integration (2026-10-29): PASS.** The initial approved attempt stopped at the 180-second upload deadline with zero SQL; its outcome remains recorded. After renewed explicit approval at `c1d8de3`, the 9,920,290-byte gzip artifact uploaded in 23.959 seconds and both real-file guards passed before DDL. All 38 integration statements succeeded in 130.391 seconds (45 statements including readiness). The three isolated development tables contain 120,969 Bronze rows, 120,969 Silver rows and two COMPLETE manifest entries. First-week checkpoint recovery, both read-only reruns, complete-multiset reconciliation and first-week preservation after append passed. Original Delta versions, published aggregates, metadata, parent grants and warehouse configuration remained unchanged. No notebook/PySpark adapter executed. See `docs/DATA_FOUNDATION_V2_NATIVE.md`.

**Unified three-week V2/Gold (2026-10-29): LOCAL PASS; native extension pending.** From merged PR #7 / main `7662ece`, the existing middle CSV was read through HEAD/GET and its 8,671,212-byte hash matched. Local V2 processing preserves the earlier weeks and matches legacy 110,337 / 26 HEADER / 110,311 VALID, with 186 additional geography review warnings that remain valid. Explicit COMPLETE-version SQL for hourly/daily/weekly analytics reconciles all three local weeks: 231,306 Bronze/Silver, 79 headers, 231,227 valid, 236 hourly buckets and 20 daily rows. Sixteen new synthetic tests expand the passing suite to 126. Original CSV landings, middle V2 append and three new Gold views are prepared in one 45-statement bounded plan; none has run natively. Existing V2 outer weeks and legacy views are preserved. See `docs/THREE_WEEK_GOLD.md`.

**Next action:** Review the coherent three-week PR and `docs/THREE_WEEK_INTEGRATION.md`, then approve the exact native scope separately. Source identifier/CRS/timezone semantics remain unresolved; published Gold is still the original one-week view. No automatic retry/cleanup, pipeline redirection, object replacement, weather/H3 ingestion, forecasting, optimization, dashboard application, jobs, schedules or commercial infrastructure is included.
