# Architecture decision log

## ADR-015 — Shared offline map, source-specific snapshots and conservative geography (2026-11-05)

Use one Leaflet component with bundled official streets and a separate hash-verified local-file payload; never treat a front-end mode switch as access control. Fixed public cell/week totals prevent finer filter differences. Preserve the original four-week contracts, reuse UnifiedGold and weather summary expressions, and extend only local versioned history. Extract ArcGIS through bounded count/ID reconciliation; snapshot OIDs are not permanent business keys. Compare overlap as multisets rather than append it. Prefer the attributed legacy named centreline because actual replacement attributes are null, while preserving both source identities. Road proximity and gap-limited observed fragments expose uncertainty and do not become service outcomes. Requests and another city's published statuses retain separate grains/provider semantics. [Evidence and rejected alternatives](GEOSPATIAL_V3.md).

## ADR-014 — Reporting overlap, censored episodes and private spatial playback (2026-11-04)

Keep source observations and identifiers distinct from reporting-window counts. Group tied timestamps before transitions; conflicting states, long gaps and source starts are unknown. Separate episode-gap sensitivity from the stricter transition continuity threshold. Retain censored private episode audit records; publish pooled city/source summaries only. Match retrospective weather at the containing-hour context and count distinct supporting facts without treating pings or shared episode weather as independent exposure. Keep hour/day/equipment geographic playback and returned-grid overlays in a separate private offline page with no exports; public V1 spatial grain is unchanged. See [definitions, trade-offs and reproduction](OPERATIONAL_DIAGNOSTICS_V2.md).

## ADR-013 — Local operational analytics product with reusable Gold semantics (2026-11-04)

Execute the existing UnifiedGold product CTEs locally over exact pinned CSV reconstructions; add coarse cell/hour metrics using the same equipment expressions. Reuse cached weather and the existing conditional matcher, deduplicate grid/time facts before weather summaries, and publish an allowlisted aggregate-only standalone dashboard. Keep detailed real cell/hour products private; suppress under-20 cell/week map groups with explicit accounting. Separate public replay, actual detail rebuild, native publication and model readiness. No native manifest simulation, ingestion changes, new providers or hosted deployment. See [contracts, execution and trade-offs](OPERATIONAL_ANALYTICS_V1.md).

## ADR-012 — Corroborate the source clock without rewriting NTZ (2026-11-04)

Use the official replacement layer's explicit date-field timezone, exact selected local-hour count crosswalk and direct timestamp-only samples to corroborate Toronto for the pinned January weeks. Preserve source NTZ and conditional Toronto/UTC outputs because the historical CSV exporter clock remains undocumented. Exclude scraper timezone and observed inconsistent date MIN/MAX representations from clock proof. Analyze saved, hash-pinned weather matches at source-day/hypothesis grain, deduplicating weather grid/hours and retaining sampling/missing-day limits. No new collection or native/runtime validation gates. See [evidence and trade-offs](TEMPORAL_ALIGNMENT_REVIEW.md).

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

## ADR-009 — Snapshot weather and expose temporal uncertainty (2026-11-03)

Use a bounded single-point ERA5-requested Open-Meteo historical batch, preserving response bytes and request/retrieval provenance separately from typed UTC staging. Allow this attributed public weather sample in Git; the prohibition on raw municipal telemetry is unchanged. Request epoch/GMT timestamps and align preceding-hour accumulation intervals explicitly. Do not zone the existing activity NTZ fields without source evidence: daily joins compare labelled Toronto/UTC hypotheses, retain null missing-activity days and are retrospective only. Defer forecast-as-of features, streaming and native weather deployment. Keep successful municipal orchestration intact; distinguish release acceptance from routine integrity checks in one runbook. See [implementation/trade-offs](DEVELOPMENT_REVIEW_2026_11_03.md).

## ADR-010 — Derive weather demand from private activity time and location (2026-11-03)

The first fixed-point snapshot is a reproducibility/temporal fixture, not a location-matched end product. Screen selected VALID Silver privately, preserve source-record multiplicity, suppress sparse coarse bin/hours and derive both timezone hypotheses before planning unique representative/date requests. Use returned grid coordinates/elevation and single-location response identity, with nearest-cell/grid-elevation requests, to deduplicate demanded facts without inventing street precision. Keep real input/projection/cache private and fail on ambiguous joins or conflicting grid/hour data. Implement/tests are synthetic until authorized private Silver is available; no native changes or expanded Gold authority. See [review revision](WEATHER_ACTIVITY_REVISION.md).

## ADR-011 — Coarse hull for region review; occupied demand for collection (2026-11-03)

Discover the region from screened Silver locally. Compute bounding box/convex hull over deduplicated coarse cell corners, not raw trajectories, and distinguish eligible versus sparse-suppressed retained footprints. Preview hull/bounding-box collection sizes but keep requests on occupied bins and required times. A hull can fill unobserved gaps, and multiple candidates can resolve to one returned weather grid. Do not interpret geometry as a city boundary or independent weather information. Cache source dimensions per scope to avoid per-observation metadata recomputation.


## 2026-11-06 — V3.1 evidence, exposure and privacy

- Use bounded heading plus actual provider-node/endpoint connectivity for candidate fragments; keep nearest-road as a control and unmatched/ambiguous outcomes explicit. No routing solver, inferred service distance or completion label.
- Retain conflicting timestamp groups as unknown; source ordinals cannot establish within-second physical transitions. Reported ID strings are not verified physical assets across weeks.
- Extend weather with two fixed public regional references and continuous hours independent of telemetry. Preserve existing activity-matched archive and alternative clocks. Missing recording is unknown deployment; reanalysis is retrospective.
- Do not append the replacement portal overlap: one window doubles existing payload multiplicities. Snapshot OIDs and matching payloads do not establish new operational events or independent sensor corroboration.
- Extend the existing shared Leaflet component. Public corridor metrics are fixed pooled totals; finer road/time/state intersections are local-file-only. Index by hour and bound drawing, while keeping analytical totals uncapped.
- Keep the January-2025-posted named streets as an explicitly imperfect historical reference; do not attach attributes by proximity. A named major-road subset is supplementary feasibility, not a complete replacement.
- No native Gold/ingestion writes. Obtain independently labeled historical service evidence and documented identifier/clock semantics before predictive work.
