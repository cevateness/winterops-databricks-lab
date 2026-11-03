# Activity-driven historical weather — current implementation and results

**Executed and independently verified on November 3, 2026.** After explicit user approval, all **24 Open-Meteo requests succeeded**, returning **2,088 hourly location records / 6,264 variable values / 62,218 response bytes** in **112.34 client seconds**, with zero retries. The actual local match contains **1,684 rows**: 842 coarse activity cell/hours under each of two timezone hypotheses. Current-hour and two-hour antecedent coverage are complete in every matched row.

This addresses [review comment 6598402435](https://github.com/cevateness/winterops-databricks-lab/pull/17#issuecomment-6598402435). The original 720-hour fixed-point sample remains an API/provenance/temporal fixture; it is not substituted for the actual spatial results. [Actual execution evidence](WEATHER_ACTIVITY_EXECUTION_RESULTS.json) and [source/plan evidence](WEATHER_ACTIVITY_LOCAL_PLAN_RESULTS.json) distinguish local execution from native Databricks status.

## Source recovery and coverage

The four official public CSVs were recovered and all original SHA-256/source-version pins matched (**23,467,248 bytes**). Portable local Bronze/Silver reconstruction reproduces **298,156 parsed records = 298,051 VALID + 105 HEADER + 0 INVALID**, with **239,344 plow-active / 127,232 spreader-active observations**. This is actual public-source processing, not a fresh native Silver/manifest read. Raw municipal CSVs, record-level coordinates and vehicle IDs stay outside Git.

The complete private weather plan uses `minimum_observations=1` and an explicit weather-only regional context margin of one angular degree. It retains **every one of the 298,051 VALID observations**, including all **863 outside the original source review envelope**; 12 of those lie within the 0.01-degree near-boundary diagnostic. Nothing is lost through sparse suppression or hull clipping. Context observations retain separate counts in each matched row; source quality classifications and hashes are unchanged. Including a record for weather does not prove its location accuracy or municipal jurisdiction.

Defaults remain conservative: minimum count five and zero extra geographic margin. Default exclusions are fully audited rather than described as inactivity. The broad source review envelope is a screening policy, not an authoritative city polygon. Reconstruction does not certify the completeness of the municipal feed or current native tables.

## Data flow and grains

| Stage | Unique grain | Meaning |
| --- | --- | --- |
| Private local Silver projection | Processing key + source-record ordinal | Observation; repeated payloads at distinct ordinals remain records |
| Coarse activity | Processing key + 0.25° candidate bin + naive source hour | Private observation count and source/policy provenance |
| Weather fact | Weather collection snapshot + returned grid ID + UTC valid time | One demanded model-time record, with raw-response provenance |
| Matched projection | Processing key + coarse bin + naive hour + timezone hypothesis | Many-to-one weather match; no calendar Cartesian expansion |

[weather_demand.py](../src/winterops/weather_demand.py) screens selected typed rows and checks source identity, policy, ordinals, bounds and timestamp types. Exact repeated input ordinals block; repeated payload observations are preserved. Candidate cells use floor(latitude × 4) / floor(longitude × 4), including correct negative-longitude handling. Requests use fixed cell centres, never individual/mean vehicle positions.

The private input/projection/cache paths remain outside the repository. Real coarse activity projections are not published to Git. Default sparse suppression is data minimization, not an anonymity guarantee; complete private acquisition deliberately uses threshold one. No per-vehicle ID, exact position or subhour event time is sent to the weather provider.

## Collection size, footprint and boundaries

“API hours” in older fields means **hourly location records, not elapsed hours**. The original synthetic example has 3 requests returning 48 + 48 + 24 = 120 rows, with 360 variable values. Its comparison against 144 regional rows is a planned data-volume comparison, not billed compute or measured savings. New output fields use `requested_hourly_location_records`, `requested_measurement_values` and explicit unit labels; older fields remain compatibility aliases.

The actual plan has **842 activity cell/hours / 9 coarse representatives / 24 requests / 2,088 returned rows**. The weather-specific ceiling is **24 requests / 8,192 hourly location records**; each response has a 1 MiB body cap and 30-second socket timeout, with no retry. The earlier 16-request planning guard stopped before collection; the ceiling was revised after inspecting the small real workload. Native Gold execution limits were never changed.

[weather_footprint.py](../src/winterops/weather_footprint.py) derives separate eligible and retained footprints: occupied coarse bins, bounding box and GeoJSON convex hull over **cell corners**. It is a conservative coarse-cell envelope, not a raw-GPS trajectory hull or municipal boundary. The O(K log K) hull works after cell deduplication, with at most 64 bounding-box candidates and exact integer edge handling. Empty, single-cell and collinear cases are supported. No GIS dependency or square-kilometre area claim is introduced.

The hull previews broader regional collection; it does not clip source observations or returned provider grids. Each eligible point is assigned to one half-open cell. Exact internal edges go into the adjacent cell; geographic review edges are inclusive. New valid points outside a previous footprint expand the plan. Missing/non-VALID/outside-context/sparse categories reconcile to input totals, and outside-near-review counts remain visible. Regional hull/bounding-box collection is not automatically executed.

Source dimensions are cached once per selected scope. One local synthetic 20,000-row comparison measured **4.8844 seconds before / 0.4869 after**, with identical coarse counts; this is not a Databricks performance forecast.

## Requests, returned grids and temporal integrity

Required labels are unioned across both `America/Toronto` and `UTC` hypotheses, separately by representative. Contiguous required UTC dates are grouped, gaps are not filled, and windows split at 31 days. The archive returns complete days; extra boundary/day rows remain in raw snapshots but are excluded from demanded facts. Single-location requests preserve unambiguous response identity (request ID + response location index zero). There is no request per municipal ping, no unsupported multi-location array binding and no automatic alternate execution route.

Requests explicitly use ERA5, nearest grid and `elevation=nan` to disable point-elevation downscaling. Grid identity uses returned latitude/longitude/elevation plus the extraction contract; requested coordinates are not assumed to equal model cells. Model identity is requested, not independently attested by the JSON. Exact request snapshots are byte/hash verified on reuse. Conflicting overlapping grid/hour values or changed grid assignments block rather than choose a revision silently.

For a hypothesized activity hour `[h,h+1)`, temperature uses the instant labelled `h`; precipitation/snowfall use the preceding-hour accumulation labelled `h+1`. Two-hour antecedent sums use labels `h` and `h−1`, covering `[h−2,h)`. Missing hours/measurements remain null; current and antecedent coverage are reported separately. Ambiguous/nonexistent DST wall hours reject rather than guess.

Actual responses resolved to **9 distinct returned grids**. The final catalogue retains **1,459 demanded unique facts** from 2,088 returned rows. Matching produces exactly **842 rows per hypothesis**, preserving **298,051 observations and 863 outside-original-review observations per hypothesis**. Do not sum the hypotheses into a doubled observation total. All 1,684 rows have complete current/antecedent coverage and zero null current measurements.

An independent verifier read exact raw response arrays, checked every staged fact and matched value, independently applied January UTC/Toronto offsets, verified precipitation endpoints and antecedent sums, checked all source/response hashes, and proved grain uniqueness/count preservation. A complete offline cache replay reproduced identical match rows, facts, keys, audit and demand with **zero additional HTTP**.

## What remains uncertain

The source activity timezone is still unverified. Toronto versus UTC changes temperature in **822/842 paired cell/hours** (mean absolute difference about **1.98°C**, maximum **7.7°C**), precipitation in 426 and snowfall in 398. These are alignment-sensitivity results, not evidence selecting the correct clock interpretation.

ERA5's roughly 25-km resolution and one representative per coarse activity cell do not establish street-level conditions or an exact per-event nearest-grid assignment. Observation counts do not establish service duration, coverage, fleet availability, productivity or causation. Reanalysis is retrospective and cannot serve as historical decision-time forecast information merely by applying a lag.

**No Databricks API/SQL, table/view changes, Jobs, scheduling or native weather deployment occurred.** Native Gold publication still requires the original exact private matrices/metadata/results and secure binding. Recovering public CSVs does not substitute for that plan or verify current native COMPLETE state.

## Reproduce and review

**289 offline tests pass**; the actual 24-response validation and independent raw-data oracle are additional execution evidence. Existing CI checks stay offline. Synthetic demos remain labelled synthetic and are not presented as the real grid distribution.

```bash
python -m unittest discover -s tests -v
python scripts/audit_gold_candidate.py
python scripts/weather_activity.py demo --output /tmp/synthetic-weather-proof.json
```

Recover exact public source bytes into a new private directory, without weather or native access:

```bash
python scripts/reconstruct_weather_projection.py --private-root /tmp/winterops-local-source
python scripts/weather_activity.py plan --private-silver /tmp/winterops-local-source/silver_projection.jsonl --minimum-observations 1 --geographic-margin-degrees 1.0 --output /tmp/winterops-local-source/demand.json
```

The private download archive contains 24 exact weather snapshots/provenance bundles, the coarse matched projection, demand plan, execution receipt, independent validation, source-verification aggregates and member checksums. **No original municipal CSV, record-level GPS, vehicle ID, credential or native workspace config is included.** Keep this detailed archive private. Unpack it outside Git, then replay without a weather request:

```bash
python scripts/weather_activity.py match --private-silver /tmp/winterops-local-source/silver_projection.jsonl --minimum-observations 1 --geographic-margin-degrees 1.0 --snapshots /private/unpacked/weather_cache --output /tmp/winterops-local-source/replayed-match.json
```

Use a new output path for create-only files. On Windows use equivalent private paths and install `tzdata` if needed. The original transfer rejection was resolved by explicit user authorization; the successful approved run used exactly 24 requests with no retries. No additional or recurring collection is scheduled.

Weather data by [Open-Meteo.com](https://open-meteo.com/), ERA5 / Copernicus C3S, [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Raw provider responses are unchanged; staging and matched analyses are transformations. ERA5 citation: [10.24381/cds.adbb2d47](https://doi.org/10.24381/cds.adbb2d47). Contains municipal information under the [City of Windsor Open Government Licence](https://opendata.citywindsor.ca/Documents/OpenDataTermsofUse.pdf). No endorsement is implied. See [original source/interface/licence research](WEATHER_INTEGRATION.md).
