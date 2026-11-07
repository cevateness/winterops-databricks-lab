# WinterOps V3.1 — review, contracts and reproduction

Start with [actual findings](ROAD_EVIDENCE_V31_FINDINGS.md), open [the unified map](../dashboard/geospatial.html), then inspect the modules below. PRs #18–20 were merged before this work; the follow-up branch `feat/road-passage-evidence-v31` starts at main `4d93d648c4c8fa35080b273cf67ef68bf31e51fa`. No owner branch was rewritten or auto-merged.

## What changed and what did not

V3 already supplied seven local source weeks, 338,746 VALID observations, official geography, conservative movement, sensor summaries, bounded requests and a real local-file Leaflet workflow. This iteration adds road-sequence evidence, threshold comparisons, source/identity case studies, four real fixed-reference weather requests, continuous exposure, further portal overlap and road/quality investigation in that same application. Municipal history remains seven weeks; no additional municipal events were appended. Four January weeks remain native-ingested, three February weeks local-only, and only the original three-week Gold is published natively. No Databricks operations occurred.

[Executed results](ROAD_EVIDENCE_V31_RESULTS.json) are allowlisted aggregates. [Execution receipt](ROAD_EVIDENCE_V31_EXECUTION.json) pins the actual private build; [weather replay](ROAD_EVIDENCE_V31_EXPOSURE_REPLAY.json) is independently reproducible from public snapshots and city/hour aggregates. Private road/sensor detail was actually recomputed, not substituted by synthetic data. Synthetic tests exercise edge cases. Current local/CI results and browser evidence are recorded in [verification](ROAD_EVIDENCE_V31_VERIFICATION.md).

## Grain and evidence contracts

| Product | Key / grain | Metric and cardinality rule |
| --- | --- | --- |
| Silver observation | Processing key + source record ordinal | All 338,746 VALID rows, including repeated payloads. Frozen parsing, quality policy and original NTZ timestamps |
| Timestamp group | Processing key + reported identifier + original timestamp | All tied rows retained; conflicting states or multiple coordinates remain unknown for movement. Ordinals are evidence, not within-second event times |
| Adjacent interval | Source/identifier scope + consecutive timestamp-group pair | Each adjacent pair accounted for once. Conditional elapsed time, geodesic displacement, apparent speed and mutually exclusive first rejection reason |
| Road point candidate | Original coordinate + official road COMPKEY | Proximity only; alternate distinct road keys matter. Not street coverage |
| Road-supported interval | Adjacent interval + explicit method/policy | Nearest-road control, heading-supported or bounded topology method; unmatched/ambiguous remains explicit |
| Passage-candidate fragment | Continuous supported interval run | ≥2 intervals / ≥3 timestamp groups, same source/ID/corridor/equipment/compass quadrant, ≥20m projected progress. Break at rejected intervals or disconnected reference features |
| Public corridor summary | Fixed all-seven-week road-name total | ≥20 fragments across ≥4 source weeks; count and interval support only. No public road/week/hour/state subtables |
| Private display | Source scope + clock window + state / road / episode / evidence filters | City-window cell counts/reporting/onsets remain context; road and episode filters select movement only. Quality overlays are all-state/all-road context, explicitly labeled |
| Weather fact | Provider/requested model + returned grid identity + UTC valid time | Unique facts deduplicated before aggregation. Reanalysis, request-parameter model attestation; exact bytes and units validated |
| Exposure calendar | Fixed public reference + clock hypothesis + source-clock hour | All 1,176 hours created before activity is left joined; absent observations are null/unknown, never zero deployment. Alternative clock cases are not added |
| Weather relationship | Occupied source hour or explicitly weather-defined episode | Mean reporting IDs over occupied 5m buckets. No ping-level independence, spatial precipitation sums, causal effect or deployment-probability claim |

### Road correspondence

`road_passages.py` reuses `geospatial.observation_interval` / `interval_reason` and the existing full-geometry metric `RoadIndex`. Original accepted V3 fragments reconcile to 235,012. Reference rules: ≤60s gap, ≤100km/h apparent speed, >3m displacement, unique endpoint coordinates, known stable equipment. Heading needs ≥10m displacement. Endpoint road distance ≤30m, tangent/chord unsigned orientation difference ≤30°, runner-up max-endpoint-distance separation >10m, path length ≤1.5× displacement +10m.

Same-feature paths or two-feature paths sharing actual nonzero START_NODE/END_NODE values **and** endpoints within 5m can qualify. Each connected leg must be ≥5m. Node attributes join to legacy COMPKEY exactly; no current/legacy proximity transfer. Missing nodes, 549 mismatched node pairs, unsupported turns, alternative roads and candidate overflow remain unresolved. Local tangents use ±5m along the reference line; direction is an observed compass quadrant, not verified one-way legality. More than two road features are not routed. Sharp turns can be rejected conservatively. Sequence coalescing requires shared feature or verified node connection; disconnected same-name lines cannot merge. A junction between different corridor names is context only and receives no forced corridor label.

Sensitivity runs change one of distance (15/60m), heading (15/45°), gap (30/120s), alternative separation (0/20m) or speed ceiling (60/150km/h). These are assumptions, not measured GPS error bounds. The street file was posted January 2025, with no certified January–February 2026 as-of network or legal-turn snapshot. A nearby or connected line is never a cleared-road label.

### Weather interpretation

Fixed Windsor-centre and regional-north references are predeclared public geography, independent of telemetry. Four actual requests cover January 4–February 23 inclusive, using 31-day and 20-day UTC slices per location. This is the minimum two requests per reference under the existing 31-day contract, with a second reference for sensitivity. Original January activity-matched weather is separate and unchanged; no February position-matched collection is claimed.

Temperature at hour start is instantaneous °C. Precipitation/snowfall for [h,h+1) use the preceding-hour accumulation reported at h+1; antecedent two hours use accumulations ending h−1 and h. The intervals do not overlap. Containing-hour weather on a subhour map can include weather after the selected subhour. The exposure calendar distinguishes recorded telemetry, missing telemetry and missing weather. Toronto is corroborated for January but exporter semantics remain unconfirmed; source NTZ values are unchanged. DST ambiguous/nonexistent wall times are rejected by existing functions.

Snow episodes use hourly snowfall ≥0.1cm, separated by at least six dry hours, with 3/12-hour sensitivity. These are descriptive calendar-defined episodes, not official storm IDs. Missing intervening weather yields null accumulation, not zero; boundary context is flagged. Current-hour and antecedent reanalysis are retrospective, not proof of decision-time feature availability. Dispatch labels remain absent.

## One map, two data sources

`templates/geospatial.html` + `dashboard/geospatial_core.js` remain the single Leaflet component. The public payload is losslessly gzip/base64 encoded inside the HTML (538 KB instead of 3.43 MB), decoded in memory by the current browser; this is transport compression, not privacy protection. The baseline `dashboard/geospatial.json` stays unchanged, while the renderer composes V3.1 aggregates and executed private-file pins from the separate public result/receipt files. `--baseline-only` retains original V3 rendering. Official roads/wards/boundaries are bundled offline. There are no tile or telemetry network requests, browser storage or detail exports; CSP blocks data connections. Public mode contains fixed weekly concentration, city-level summaries, independently public weather and fixed pooled corridor counts. Changing week never exposes a road/week intersection.

The local file picker accepts only executed SHA-256/byte-count pins, decompresses in memory, validates scope/count/evidence alignment and builds indexes. Original V3 and V3.1 payloads are supported; V3-only files disable new evidence controls. The public HTML contains neither private body. A front-end mode label is not access control: isolation comes from the separate user-selected file, absence of public endpoints/exports and no private data in committed assets.

New controls select a corridor, sequence evidence and sensor flag; map and panels share one clock/window/state. Fit selected activity reveals regional outliers that Fit Windsor roads would hide. Rejected short GPS jumps may be dashed red; recording gaps have endpoint rings **without a connecting path**. Flags can overlap. Passage counts overlap the window and may be censored; rendered intervals must lie fully within it, including their right endpoint. A passage ending at the left window boundary is excluded.

The map draws at most 4,000 viewport-relevant fragments; quality layers are bounded at 2,000 cells / 1,500 rejected intervals. Metrics use the uncapped selection. Only rendering is reduced. Hour indexes replace full-table scans; a day/state cache avoids rescanning all 144,512 cell rows for every playback tick. Weather, reporting, quality and passages use the same hour indexing. No spatial/time data is sent to external basemap services. The official road vectors provide the missing-tile fallback directly.

## Windows review, no private input required

Run from the repository root in PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[geo]"
python -m unittest discover -s tests
node tests/geospatial_core_test.js
python scripts/replay_weather_exposure.py --output "$env:TEMP\winterops-exposure.json"
python scripts/render_geospatial.py --output dashboard/geospatial.html
python -m http.server 8000 --bind 127.0.0.1 --directory dashboard
```

Open `http://127.0.0.1:8000/geospatial.html`. Review Dougall/Tecumseh summaries; change week and observe that public road totals remain fixed. Compare continuous reference exposure with January activity-matched context. The street basemap works offline. These commands make no weather or Databricks requests. The public replay reruns actual weather associations from exact public snapshots and recorded city/hour means; it does **not** claim to rerun private spatial or sensor calculations.

## Actual private replay

The separately delivered `WinterOps_V3.1_private_replay.zip` includes `v3/` (original private V3 package), `new-source/` (new exact bounded portal snapshots/receipts), the V3.1 local gzip and execution evidence. Extract outside **every Git tree**, for example `C:\WinterOpsPrivate\V31`. Never place it in `dashboard`, a web-server root or a public repository. The picker reads it locally without uploading it.

Load `winterops-v31-local.json.gz` directly to explore the executed build. To reconstruct offline:

```powershell
python scripts/restore_geospatial_inputs.py --package C:\WinterOpsPrivate\V31\v3 --output C:\WinterOpsPrivate\V31\restored
python scripts/run_evidence_investigation.py --inputs C:\WinterOpsPrivate\V31\restored --v3-private C:\WinterOpsPrivate\V31\v3\winterops-local-detail.json.gz --output C:\WinterOpsPrivate\V31\rebuilt
python scripts/review_source_evidence.py --inputs C:\WinterOpsPrivate\V31\restored --source-root C:\WinterOpsPrivate\V31\new-source --output C:\WinterOpsPrivate\V31\source-review.json
node scripts/profile_geospatial.js C:\WinterOpsPrivate\V31\winterops-v31-local.json.gz
```

The restore/rebuild output directories must be new. Full computation reconciles source pins, ordinals, 338,746 observations, 4,147 conflicts, 235,012 legacy intervals and all method scenarios. Current functions reproduce the released private gzip byte-for-byte in this environment; compression/library-version differences elsewhere can change byte identity and must not be bypassed by disabling pins. For an intentionally rebuilt local product, use `render_geospatial.py --private-payload <outside-git-file> --output <local-html>` to pin its actual bytes after reviewing reconciliation. The renderer embeds only the fingerprint and byte size.

For browser review: January 12 week → January 16 → hour 16 has 4,333 observations, 427 candidate fragments, 2,833 accepted intervals and 1,456 sequence-supported intervals. Dougall has 17 candidate fragments; both-active narrows it to two while city-window observations become 1,566. February 9 week → February 10 hour 09 has 240 stationary-flagged observations and no accepted movement; **Fit selected activity** reveals the outside-city context. January 24 hour 00 is missing telemetry while reference weather remains available. UTC changes weather, not winter elapsed-time road evidence.

Fresh external acquisition is optional, not part of normal tests: `inspect_v31_sources.py --output <new-outside-git-directory>` reuses the bounded seven date windows, schema pin, count/ID batches and 50-request/6.5MB ledger. A revised source can fail the recorded comparison and must be reviewed, not coerced into equality. `weather_exposure.collect(<new-outside-git-root>)` requests only the two documented public references/four slices. Existing cached snapshots are sufficient; no automatic weather collection is configured.

Optional study-figure rebuild requires matplotlib: `python scripts/plot_road_evidence.py`. CI does not install a plotting dependency merely to recreate an already committed figure.

## Architecture and lessons

A raw record answers what the provider reported; Silver establishes typed validity and lineage; Gold defines business counts at explicit grains. Road intervals and fragments are another analytical product with extra assumptions, not a replacement for Silver. Weather facts are independent grid/time records, while activity-conditioned matches and continuous exposure have different selection processes. A correct many-to-one weather join preserves observation totals; alternative clocks are scenarios, never additive facts.

Nearest-feature matching is a useful control but unstable at intersections. A full routing/HMM solver would add complexity and undocumented assumptions; bounded heading/node checks expose where evidence ends. Materialized analytical tables may help when this grows to repeated multi-season queries, but portable Python plus small public projections are sufficient for seven weeks. Existing Databricks Gold SQL and UnifiedGold remain the source of business count definitions; no JavaScript reimplementation of municipal transformation policy was added. JavaScript filters/presents already computed evidence.

The source comparison illustrates why source version + payload multiplicity and manifest state matter more than OBJECTID. Exact copies can appear in a replacement representation without establishing new events. Reconciliation cannot certify a sensor or resolve identity. The next milestone is a small independently labeled historical event and custodian-confirmed identifier/timestamp/update semantics, then a documented target and availability-safe feature contract. Forecasting, MLflow, optimization and production deployment remain out of scope.
