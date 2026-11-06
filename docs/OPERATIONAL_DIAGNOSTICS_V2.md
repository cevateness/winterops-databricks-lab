# Operational diagnostics V2 — definitions, architecture and review

V2 continues **PR #19**, preserving commits `98a9754` and `f194bac` and its stacked dependency on PR #18. No owner PR was merged or force-pushed. [Actual findings](OPERATIONAL_DIAGNOSTICS_V2_FINDINGS.md) · [public diagnostics](../dashboard/diagnostics.html) · [machine-readable results](../dashboard/diagnostics.json).

## Data products

| Product | Key / grain | Interpretation |
| --- | --- | --- |
| Reporting window (private detail) | Processing key + source-local bucket + width | Distinct IDs in 1/5/15-minute windows; observations counted separately. Plow/spreader sets overlap; both flags anywhere in a window differs from both on the same observation |
| Timestamp group (internal) | Processing key + truck ID + normalized naive timestamp | All source observations retained. Different states at one timestamp produce an unknown state. Different first cells make the onset cell unknown |
| Observed episode (private) | Processing key + truck ID + first timestamp/ordinal + gap threshold | Stable timestamp/ordinal ordering; gap **greater than** 15/30/60 minutes starts another episode. Each source/truck starts independently; no joining across weekly scopes |
| Transition summary (public) | Processing key + local hour of day + continuity threshold + status + before/after | Known pairs only inside 15/60/300-second continuity limits; source starts, gaps and conflicting ties are unknown. Same-state persistence is retained |
| Public reporting summaries | Processing key + width + week/day/hour-of-day/weekday | Occupied-window distributions, percentiles, equipment distributions and peaks. Missing buckets are not zeros; distinct IDs are never summed across buckets |
| Weather relationship cohort | Processing key + hypothesis + variable/category | Cell/hour, onset or source-hour reporting analysis, with explicit denominators and distinct fact support. No raw ID or spatial/time cross-tabulation |
| Private playback | Cell/hour + hypothesis, selected window | Exact coarse geographic bounds and actual returned weather centres; individual GPS points and movement histories are absent |

`operational_diagnostics.py` contains reusable pure calculations. The builder reuses `read_bronze`, `silver_rows`, `LocalGold`/`UnifiedGold` and the existing cached weather matcher. Full builds reverify the same four source byte hashes, lineage, ordinals, all Gold metrics, and the complete existing matched projection. No ingestion, manifest, Gold definition, quality policy, weather snapshot or native publication plan changed.

## Temporal and equipment semantics

All episodes operate on **source-local naive clocks**, not instants or verified work spans. Original timestamps and record ordinals are retained in private episode records; repeated payloads are not removed. Tied timestamp groups are normalized as datetimes before state comparison. Contradictory ties are not ordered arbitrarily into transitions. Episode state composition remains observation-based, including the original conflicting observations.

All actual operational starts/ends are censored: the first observation does not establish dispatch, and the last does not establish completion. Source-first versus after-gap and proximity to source edges are explicit. Single-timestamp episodes have an apparent span of zero; they do not prove zero work. Episode-level known state changes use the same 60-second rule as the reference transition summary.

The episode gap (reference 1,800 seconds) and transition continuity limit (reference 60 seconds, four nominal 15-second intervals) answer different questions. Larger transition limits are sensitivities, not assertions of state persistence. Activation means a flag was observed off and later on in a known continuous pair. No activation is attributed to unknown entry states. Exactly-on-threshold gaps remain continuous.

Weather remains **conditional Toronto/UTC** and retrospective ERA5-requested reanalysis. Episodes use the containing hour's start-temperature and preceding two-hour accumulation ending at that hour start. Partial onset-hour weather is not called antecedent. Current-hour accumulation can include weather after onset and is descriptive only. The existing matcher rejects ambiguous/nonexistent DST instants; January episode clocks are not a general solution to unconfirmed future DST exports.

Categories: temperature **T < −10°C**, **−10 ≤ T < 0°C**, **T ≥ 0°C**; snowfall/precipitation **zero**, **positive**, or **missing**. These are exploratory partitions, not validated policy thresholds. Cell/hour summaries count each validated cell/hour once; returned grid/time fact keys are deduplicated for support. Two-hour antecedent support includes its two distinct endpoint facts. Several episodes share a weather window, so episode count is not independent weather sample size.

Reporting/weather plots use one source hour: weather is an unweighted mean over distinct sampled grids; reporting is the mean distinct-ID count over occupied buckets in that source hour. They do not multiply a city reporting count by the number of cells. Pearson correlations are descriptive; temporal dependence, week mix and selection bias preclude unsupported significance or causal inference. Changing hypotheses may change category membership and even correlation signs.

## Private geographic playback and public disclosure

`private_map.html` is generated **outside every Git checkout** from private cell/hour and matched-weather products. Controls include week, day, source-hour slider, previous/next/play/pause, equipment category, one-hour or explicit up-to-six-hour accumulation, weather measure and clock hypothesis. Rectangles use actual 0.25° WGS84 cell bounds projected to Web Mercator; circles use returned grid coordinates. Circle values average distinct grid/hour windows; no spatial precipitation totals or asserted ERA5 grid boundaries. No basemap, external tiles or extra licence is required. Missing activity periods show unknown telemetry and no imputed matched weather.

The private page is a distinct local view with **no exports**, truck IDs, exact original GPS positions or per-vehicle episode timelines. The fuller private episode JSON retains the identifiers/ordinals needed for local audit and must remain outside Git. The user-facing private map has been retained separately for review; it is not an asset of the public dashboard.

The public page contains only pooled city/source summaries and city-hour relationships. Its field guard rejects IDs, coordinates, cell keys and episode timelines. It cannot access the private map through any filter or export. The existing V1 cell/week map and its 20-observation display rule remain fixed: V2 does not introduce day/hour/equipment intersections or complementary spatial exports. Repeated filtering cannot reveal detail that is absent from the public data. Previously published V1 aggregates cannot be made secret retroactively, and suppression is data minimization rather than a formal anonymity guarantee.

The committed `private_playback_demo.html` contains **synthetic records only** for CI/manual interaction review. Desktop browser QA tested actual public diagnostics and the synthetic private-view controls. The real private page was generated from actual data and checked by projection/cardinality tests, but **was not browser-tested with its private payload**: the preview serves the public repository, while real detail remains outside it. Do not describe the synthetic map as measured Windsor output. Direct file launches were not tested in the cloud browser; use a local HTTP server if your browser restricts them.

## Reproduce on Windows

For public exploration, update the existing feature branch and open the new page:

```powershell
git fetch origin
git switch feat/operational-analytics-v1
git pull --ff-only
Start-Process .\dashboard\diagnostics.html
```

Public replay and tests require no private files or API requests:

```powershell
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/build_operational_diagnostics.py --output-root "$env:TEMP\winterops-diagnostics-review"
```

Use a fresh directory on reruns. The existing Windows-only `tzdata` dependency supplies IANA timezone data. For full actual reconstruction, use the same pinned source cache and original weather ZIP from V1:

```powershell
.\.venv\Scripts\python.exe scripts/build_operational_diagnostics.py `
  --source-cache "$env:TEMP\winterops-pinned-source-cache\sources" `
  --archive "$env:TEMP\WinterOps_weather_integration_20261103.zip" `
  --output-root "$env:TEMP\winterops-diagnostics-private"
Start-Process "$env:TEMP\winterops-diagnostics-private\private_map.html"
# Optional local-only serving if file launches are restricted:
.\.venv\Scripts\python.exe -m http.server 8001 --bind 127.0.0.1 --directory "$env:TEMP\winterops-diagnostics-private"
```

Then open `http://localhost:8001/private_map.html` locally. The builder does not acquire missing inputs or substitute versions. Its directory includes private reporting windows, episode audit records, matched cells, the private map, a shareable aggregate summary and receipts. Keep the whole private output directory outside public Git and do not serve it on an externally accessible interface. Public replay labels private detail **NOT_RERUN**; actual execution receipts are preserved independently.

## Additional data feasibility — researched, not integrated

| Source / access evidence | Analytical purpose | Reuse and limitations |
| --- | --- | --- |
| [Official snow-plowing/salting 311 catalogue](https://opendata.citywindsor.ca/Details/115); direct YTD and 2017–2025 archive CSV links are documented | Independently generated complaint/request timing, department, channel, block/street and ward | [Windsor Open Government Licence](https://opendata.citywindsor.ca/Documents/OpenDataTermsofUse.pdf) permits reuse with attribution, subject to exclusions including personal information and third-party rights. Catalogue warns about duplicate reports, customer-perspective errors and incomplete service representation. Listed attributes contain Created Date, not verified completion. YTD is mutable; January coverage, timestamp timezone, schema and revisions need checking before integration. No records downloaded |
| [Official snow-removal page](https://www.citywindsor.ca/residents/roads-sewers-sidewalks/snow-removal), with route/sidewalk map links | Priority/road-reference context, contractor-capture caveat | Current linked maps describe **2026–27**, not necessarily January 2026. Obtain the applicable archived version and map-specific reuse terms before adding geometry. A priority route is not a clearance observation; contracted equipment is explicitly absent from tracking |
| Existing cached weather, plus a proposed bounded weather-only calendar | Exposure outside observed activity hours | A complete weather calendar would address selection in weather exposure, but cannot supply dispatch/outcome labels. Document requested grids/dates, rights, revised-data provenance and missingness before any separately scoped acquisition |

The catalogue migration is explicit; current links were read November 4, 2026. No new provider was integrated. Neither complaints nor priority maps establish cleared roads, SLA attainment, actual fleet availability or costs. Those require independent operational labels and denominators. No forecasting, model training, MLflow or optimization is started.
