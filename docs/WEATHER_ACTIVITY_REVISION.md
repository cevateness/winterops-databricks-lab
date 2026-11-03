# Activity-driven weather revision — PR #17

Addresses [review comment 6598402435](https://github.com/cevateness/winterops-databricks-lab/pull/17#issuecomment-6598402435). The original one-point 720-hour snapshot is an API/provenance and temporal-alignment fixture. It is **not a location-matched weather/activity product**. Its output now explicitly says `NOT_LOCATION_MATCHED_TO_ACTIVITY`.

**Implemented and tested:** private Silver → coarse spatial/hour demand → bounded requests → returned-grid weather facts → conditional matched projection. **Live spatial matching remains BLOCKED:** private selected Silver coordinates and secure workspace access are unavailable. This revision performs zero weather HTTP requests and zero Databricks requests/writes. All new demonstrations use clearly labelled synthetic inputs and simulated provider responses. Municipal ingestion, Gold code/selections and the frozen publication plan are unchanged.

## Input and grains

[weather_demand.py](../src/winterops/weather_demand.py) consumes a local typed Silver projection with `processing_key`, source/version/pipeline/policy identities, source boundaries, `source_record_number`, `quality_status`, `event_time_unzoned`, latitude and longitude. Identical payloads at distinct source-record ordinals remain observations; duplicate input ordinals block. The projection is not a new proof that every selected Silver record was exported or that the native manifest remains COMPLETE. Those premises must come from separately validated source evidence.

Only VALID rows inside the selected policy's broad review envelope contribute demand. Non-VALID and outside-envelope rows are counted separately; Silver classifications/data are not changed. Invalid coordinates or zoned/malformed times in a purported VALID row reject the input. This prototype additionally stays within 42.1–42.5 / −83.3–−82.6. The numeric degree-coordinate interpretation and broad envelope are screening assumptions, not an authoritative city polygon/CRS certification.

| Stage | Unique grain | Interpretation |
| --- | --- | --- |
| Private input | Processing key + source-record ordinal | Municipal observation; not an hourly measurement |
| Coarse activity | Processing key + 0.25° candidate bin + naive source hour | Observation count; no vehicle/record identifier or exact position |
| Weather fact | Weather collection snapshot + returned grid ID + UTC valid time | One model-time measurement row with raw-snapshot/request provenance |
| Matched projection | Processing key + coarse bin + naive hour + timezone hypothesis | Many activity bins can use the same weather fact without multiplying activity rows |

Candidate bins use `floor(latitude * 4)` / `floor(longitude * 4)` and fixed bin centres, never a mean of vehicle coordinates. Negative longitudes must use floor, not truncation. Default suppression excludes bin/hours with fewer than five observations before demand generation. This is data minimization, **not an anonymity guarantee**. Real coarse projections, inputs and caches stay private; no auto-publication is provided. No individual coordinate, truck identifier, source-record ordinal or subhour event time leaves the aggregation boundary.

## Demand and request boundaries

Each retained bin/hour is interpreted independently under both `America/Toronto` and `UTC`. Neither hypothesis establishes the source timezone. Ambiguous/nonexistent DST hours reject rather than guess. Empty activity produces zero requests and zero matched rows; no calendar or no-activity dates are manufactured.

For each hypothetical UTC activity hour `[h,h+1)`:

- Temperature uses the model instant labelled `h`.
- Current precipitation/snowfall use the preceding-hour accumulation labelled `h+1`.
- Default two-hour antecedent sums use labels `h` and `h−1`, covering intervals `[h−2,h)`. Lookback is explicitly bounded to 0–6 hours and remains retrospective.

Union those required labels across activity and both hypotheses, separately by coarse representative. Merge only contiguous required UTC dates; split gaps and windows exceeding 31 days. The archive's date interface necessarily returns complete UTC days: excess daily boundary rows are retained in raw snapshots but excluded from the matched fact projection. There is no arbitrary whole-month calendar fetch. Default execution is bounded to **24 requests / 8,192 hourly location records / 500,000 private input records / 10,000 coarse activity buckets**; excess scope fails before HTTP. Per-request body/socket bounds and zero retries reuse the existing weather client.

Single-point requests are deliberate: they preserve an unambiguous response identity with a small bounded client. Each unique point/window is one request, not one request per ping. Multi-location list responses are unsupported; they cannot be misbound by array order. Every fact records the exact request ID, raw snapshot ID and response location index **0** for its one-location response. A future multi-location adapter must validate the provider's location identity before use.

Demand requests set `cell_selection=nearest` and `elevation=nan`, disabling point-elevation downscaling. The original fixture's default request is unchanged. This avoids treating different requested elevations as identical measurements merely because returned lat/lon agree. Grid identity includes **returned** latitude/longitude/elevation plus the explicit ERA5-requested/grid-only contract; it never assumes bin centres equal model grid cells. Model identity remains requested, not independently attested by the JSON.

Exact request IDs reuse byte-verified snapshot bundles without another GET. Initially different unmapped representatives may resolve to the same returned grid; that is learned from responses, not guessed in advance. Required overlapping grid/hour facts then collapse into one collection fact with all source-response provenance. Overlapping values must agree, including nulls; a conflict or a changed returned grid for the same representative blocks instead of choosing a revision silently. An arbitrary overlapping cache from another request is not silently substituted. No call is made per observation.

## Matched projection and coverage

The result retains processing/source/policy provenance, coarse bin, naive source hour, observation count, timezone hypothesis, returned grid ID, weather snapshot, separate instantaneous/accumulation timestamps and variables, current/antecedent coverage, and retrospective/conditional labels. The fact catalogue retains only demanded times; `matched_weather_keys` deduplicates all facts actually referenced. Missing response/grid/hour leaves the activity row and null measurements. Null weather remains null; antecedent sums are null unless every requested antecedent measurement exists. No interpolation or zero filling is used.

ERA5's roughly 25-km grid cannot resolve individual roads. Multiple bins resolving to one grid means shared weather information, not newly discovered spatial detail. Counts remain observations, not service duration, coverage, fleet availability or productivity. Antecedent reanalysis is still unavailable at historical dispatch time; it is not forecast-as-of input.

## Evidence and reproduce

[Synthetic results](WEATHER_DEMAND_SYNTHETIC_RESULTS.json): **15 fictitious observations → 3 retained bin/hours across 2 candidate bins → 3 planned point/date requests (120 API hours; 18 required bin/hours) → 1 simulated returned grid / 12 unique required facts → 6 matched rows**, three under each timezone hypothesis. Counts remain 15 per hypothesis; do not sum hypotheses. These numbers demonstrate the contract, not Windsor spatial distribution or a measured API-saving result. All synthetic provider values are invented and labelled as such.

**268 offline tests pass**, including 26 new demand/matching tests. Coverage includes source/policy identity, observation preservation, spatial/time deduplication, sparse suppression, demand-derived windows and gaps, request caps, returned grid/provenance, conflicting revisions, exact match cardinality, five-hour January sensitivity, precipitation endpoints, antecedent boundaries, null/missing data, DST rejection, raw-position minimization, and actual byte-verified cache reuse with a mocked transport. CI also executes the synthetic demo without network access.

```bash
python -m unittest discover -s tests -v
python scripts/weather_activity.py demo --output /tmp/spatial-weather-proof.json
python scripts/audit_gold_candidate.py
```

For a later user-supplied **private** validated Silver JSONL projection, all real-data input/output/cache paths must stay outside this repository:

```bash
python scripts/weather_activity.py plan --private-silver /private/silver.jsonl --output /private/demand.json
python scripts/weather_activity.py fetch --private-silver /private/silver.jsonl --snapshots /private/weather-cache --output /private/matched.json
python scripts/weather_activity.py match --private-silver /private/silver.jsonl --snapshots /private/weather-cache --output /private/matched-offline.json
```

`plan` and `match` are offline. `fetch` is the only network command and contacts only the public archive at coarse representatives, using demand windows. These private commands were **not run on live Silver** in this revision. Outputs are create-only; partial successful cache bundles are retained on failure, with no automatic retry/cleanup. Commands use the existing explicit selection by default; no native acquisition, Job execution or publication is implied. On Windows use equivalent private paths and install `tzdata` if needed.

Next: obtain an authorized private projection of the selected validated Silver scopes, verify clock/coordinate premises, inspect coarse demand privately and then run the bounded weather acquisition/matching. Until then, live location-matched results remain blocked. The original native Gold prerequisites and authorization limits remain separate.

## Region discovery and convex hull

The follow-up footprint extension is implemented in [weather_footprint.py](../src/winterops/weather_footprint.py). Use **validated Silver**, not unchecked Bronze latitude/longitude: repeated headers, malformed records and geographic outliers can stretch a raw hull into an unrelated region. Bronze remains the provenance/audit source. The existing screen preserves exclusions in the audit and never modifies Bronze/Silver.

The same local pass now derives an **eligible footprint before sparse suppression**; the request plan separately reports its **retained footprint after suppression**. Each footprint includes occupied coarse bins, a bounding box, and a GeoJSON convex hull of the occupied **0.25° cell corners**. It is a conservative coarse-cell envelope, not the convex hull of raw GPS locations, a municipal boundary, road coverage, or a certified anonymized geometry. No raw positions or vehicle IDs are exported. Real footprints remain in the private CLI output.

Hull construction runs after cell deduplication: **O(K log K)** for K coarse cells, with an explicit cap of 64 bounding-box candidates. Integer quarter-degree geometry avoids floating-point edge ambiguity; empty/one-cell/collinear cases are covered. No GIS dependency, area calculation in square kilometres, or per-ping network request is introduced.

The planner reports three collection sizes using the current required UTC dates:

| Collection choice | Purpose |
| --- | --- |
| Occupied bins and their own required hours/dates | Default: weather attached to observed activity, with existing antecedent/boundary handling |
| All candidate centres within the coarse hull, on all required dates | Preview of broader regional coverage; may include locations/times without activity |
| All bounding-box candidate centres, on all required dates | Simplest regional preview, usually at least as broad as the hull |

The hull guides scope review; it does **not** automatically add regional API calls. Activity-driven collection remains the efficient default for this analytical join. A separate regional weather map could justify interior coverage, but those extra weather facts must not create invented activity observations. Candidate points still have to be resolved to **returned** provider grids. Multiple requested points can map to the same ERA5 cell, so footprint vertex/candidate counts are not counts of independent weather information or station observations.

In the current synthetic proof, occupied demand requests **120 API hours**, while covering both hull/bounding-box candidates on every required date would request **144**. These are planned returned-hour counts, not measured API savings, billed compute or a real Windsor result. A separate triangular-cell regression demonstrates hull candidate reduction from 9 bounding-box candidates to 8; three cells are actually occupied.

The aggregation loop now caches source dimensions once per selected scope instead of recomputing them for each field of each observation. A single local synthetic 20,000-row comparison measured **4.8844 s before / 0.4869 s after**, with identical coarse counts. This is a local Python measurement, not a native performance forecast. The full suite now contains **278 passing offline tests**, including 10 new footprint/collection regressions. No additional weather HTTP or Databricks requests were made for this extension.

Existing `plan` and `demo` commands automatically include these footprint/cost diagnostics; no new execution mode is necessary. The live Windsor footprint and its actual unique weather-grid count remain blocked until the private selected coordinates are supplied.

Interface/units/licensing references and attribution: [weather source documentation](WEATHER_INTEGRATION.md). The synthetic provider response is not actual Open-Meteo weather. Actual fixture weather remains attributed to [Open-Meteo.com](https://open-meteo.com/), ERA5/Copernicus C3S, [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

## Collection units and boundary coverage

**120 hourly location records is a data volume, not 120 hours of runtime.** In the synthetic example, three single-location requests cover 48 + 48 + 24 hourly timestamps, returning 120 rows with three measurements each (360 temperature/precipitation/snowfall values before missingness). Exact weather-grid/time deduplication later leaves 12 demanded facts. HTTP request count, returned-row count, measured elapsed time and provider billing are separate quantities; no runtime or billing estimate is inferred from “120”. This is a small planned batch, but real latency has not been measured for the spatial path.

The plan and CLI now use `requested_hourly_location_records` / `hourly_location_records` and explicit unit labels. Older `*_api_hours` fields remain compatibility aliases for the same row counts, not execution time. `estimated_runtime_seconds` remains null until actual execution evidence exists.

**The hull/bounding box does not clip activity.** Each eligible point is assigned to exactly one half-open coarse cell; a point exactly on an internal cell boundary goes into the adjacent cell. The source geographic review envelope uses inclusive edges. Recomputing demand from a new valid point outside the previous footprint expands that footprint and the request set; no frozen hull excludes the new point. Returned provider grid coordinates are not clipped to the activity geometry either.

Intentional exclusions remain explicit: non-VALID rows, coordinates outside the selected review envelope, and sparse buckets below the existing threshold. The audit now reconciles `input = non-VALID + outside-envelope + eligible` and `eligible = sparse-suppressed + retained`, with zero hull/bounding-box clipping. It separately counts outside-envelope points within a **0.01-degree angular diagnostic band**. This is not a kilometre distance or an instruction to discard more data, and it does not silently enlarge the quality policy. Excluded coordinates need private inspection before deciding whether they are legitimate nearby activity or source errors; sparse suppression remains data minimization, not evidence of no activity.

Six new regressions cover unit interpretation, both sides of internal edges, exact/just-outside review bounds, expansion beyond the previous footprint, full exclusion accounting, and returned grids outside the hull. **284 offline tests pass.** Neither this audit nor the synthetic proof certifies completeness of an unavailable private Silver export. Actual Windsor coverage is still unverified until that input is supplied. Original municipal records and Gold definitions remain unchanged; this extension performs no native or weather HTTP requests.

## Real source recovery and complete local coverage plan

The four original municipal CSVs were recovered from the official public URLs and all SHA-256/source-version pins matched: **23,467,248 bytes**. Portable local Bronze/Silver reconstruction reproduces **298,156 parsed records = 298,051 VALID + 105 HEADER + 0 INVALID**, with 239,344 plow-active / 127,232 spreader-active observations. This is actual public-source execution, **not a fresh Databricks read or native manifest verification**. Raw CSVs and the coordinate-bearing projection remain outside Git. [Aggregate execution/plan evidence](WEATHER_ACTIVITY_LOCAL_PLAN_RESULTS.json) contains no record-level positions/IDs.

The initial default weather plan exceeded the self-imposed 16-request limit. Static inspection found the full data was small, so the weather-specific ceiling is now **24 requests**, still at most **8,192 hourly location records**. The native Gold plan/29 SQL/33 metadata/900-second limits are unchanged. No weather requests are automatically added when the budget is exceeded.

The complete private plan explicitly uses `--minimum-observations 1 --geographic-margin-degrees 1.0`. This retains **all 298,051 VALID source observations**, including the 114 observations previously sparse-suppressed and all 863 outside the original geographic review envelope. Twelve of the latter are within the 0.01-degree diagnostic band. The weather-only context is bounded to one angular degree and requests are restricted to actual occupied cells/hours, not an entire one-degree regional rectangle. Default screening/suppression remains unchanged for other callers. Source quality policies/classifications are never rewritten; matched rows retain the outside-source-review observation count separately. Wider-context data is not evidence of municipal jurisdiction or correct coordinates.

Actual plan: **842 activity cell/hours / 9 coarse representatives / 24 HTTP requests / 2,088 hourly location records / 6,264 variable values**, covering demanded dates from January 5 to January 30. Zero valid observations are lost through hull clipping, the final weather context, or sparse suppression in this plan. This proves coverage of these four recovered files, not completeness of the municipal feed or of a live native table.

**Spatial weather retrieval awaits explicit transfer approval.** Automatic approval review rejected sending the activity-derived coarse representatives/date windows to Open-Meteo because destination disclosure was not explicitly authorized. The operation was not retried or replaced with another route. No spatial weather bundle/response has been verified and no real matched-weather output exists. Delivery of an initial request before the rejection is not established; it is not reported as a successful or confirmed-zero network execution. Native requests remain zero. The original 720-hour public weather fixture is not substituted for these spatial results.

Reconstruction is now reproducible without the Windows checkout or Databricks:

```bash
python scripts/reconstruct_weather_projection.py --private-root /tmp/winterops-local-source
python scripts/weather_activity.py plan --private-silver /tmp/winterops-local-source/silver_projection.jsonl --minimum-observations 1 --geographic-margin-degrees 1.0 --output /tmp/winterops-local-source/complete-demand.json
```

Use a new private directory. Reconstruction verifies exact source hashes/versions, reuses existing verified source bytes, preserves record multiplicity, omits vehicle IDs from its typed projection, and writes a success receipt only after all scopes reconcile. An incomplete projection must not be used as a complete source. It invokes **neither weather nor Databricks**. Running the prepared `fetch` command for the actual derived locations is pending explicit user approval of Open-Meteo as the recipient. The transfer would contain only coarse representative coordinates, date windows, model/variable/unit parameters; no municipal rows, IDs or trajectories.

**289 offline tests pass**, including boundary/context and synthetic reconstruction regressions. Actual local file/coverage checks above also passed. The new real-data evidence supersedes the earlier blanket statement that source coordinates were inaccessible; secure native access and the exact private Gold matrices remain unavailable.
