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

Union those required labels across activity and both hypotheses, separately by coarse representative. Merge only contiguous required UTC dates; split gaps and windows exceeding 31 days. The archive's date interface necessarily returns complete UTC days: excess daily boundary rows are retained in raw snapshots but excluded from the matched fact projection. There is no arbitrary whole-month calendar fetch. Default execution is bounded to **16 requests / 8,192 returned API hours / 500,000 private input records / 10,000 coarse activity buckets**; excess scope fails before HTTP. Per-request body/socket bounds and zero retries reuse the existing weather client.

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

Interface/units/licensing references and attribution: [weather source documentation](WEATHER_INTEGRATION.md). The synthetic provider response is not actual Open-Meteo weather. Actual fixture weather remains attributed to [Open-Meteo.com](https://open-meteo.com/), ERA5/Copernicus C3S, [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
