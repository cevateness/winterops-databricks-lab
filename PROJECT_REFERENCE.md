# WinterOps — Project Reference

**Working name:** WinterOps  
**Subtitle:** Weather-Driven Municipal Operations Intelligence  
**Project type:** Independent Databricks learning laboratory with optional future commercialization  
**Status:** Bronze/one-week Silver user-verified; canonical GitHub connected; scoped Silver/Gold view code tested offline, awaiting Databricks acceptance
**Reference date:** 2026-10-16; updated 2026-10-28

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

**Next action:** Review the read-only validation change and CI. After reviewing the exact source hash and matching aggregate evidence, execute `mode=validate` within the approved bounded read-only compute scope. Any `mode=apply` execution requires separate approval. No forecasting or optimization should be rushed. See `docs/ANALYTICS_SLICE.md` and `docs/STATUS_HANDOFF.md` for details.
