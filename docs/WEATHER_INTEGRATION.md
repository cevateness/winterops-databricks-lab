# Historical weather batch prototype

**Scope correction after PR review:** the 720-hour single-point snapshot and daily example below are reproducibility/temporal fixtures, **not location-matched activity/weather integration**. The new [activity-driven spatial/hourly path](WEATHER_ACTIVITY_REVISION.md) derives coarse demand from private Silver, keys weather by returned grids and emits matched projections. That path is implemented and synthetic-tested; live spatial matching remains **BLOCKED** because private Silver coordinates are unavailable. The existing fixture bytes are preserved.

**Executed locally on 2026-11-03; no Databricks deployment.** The committed public weather snapshot contains 720 hourly rows for January 4–February 2 inclusive, covering the four selected activity weeks with boundary padding. All timestamps and values passed the source contract; there are zero missing values or duplicate hours. [Recorded results](WEATHER_EXAMPLE_RESULTS.json) contain an actually executed, conditional daily join to the five recorded fourth-week activity days. Activity is existing offline Gold evidence, not newly queried native data.

## Source choice and verified interface

Use the [Open-Meteo historical archive](https://open-meteo.com/en/docs/historical-weather-api), explicitly requesting `models=era5`. ERA5 is global, hourly, approximately 0.25° / 25 km, with history from 1940 and a documented five-day update delay. January 2026 coverage was verified by actual HTTP retrieval. Pinning ERA5 avoids silently mixing models through Best Match. This is model-based **reanalysis**, informed by observations; it is not a local weather-station measurement or road-condition sensor.

The implementation requests one chosen Windsor-area reference point, 42.3149° N / 83.0364° W. This is a sampling choice, not an authoritative city centroid or a vehicle location. The actual response returned grid coordinates **42.25 / −83.0**, elevation **189 m**. Preserve both requested and returned coordinates. `cell_selection=land` and provider elevation handling remain explicit/default respectively; the result cannot represent every road or microclimate. The JSON does not return a model identity: provenance records **ERA5 requested**, not independent model attestation.

| Contract field | Choice |
| --- | --- |
| Endpoint | `https://archive-api.open-meteo.com/v1/archive` |
| Dates | Inclusive API dates; this sample `[2026-01-04, 2026-02-03)` UTC |
| Time | `timezone=GMT`, `timeformat=unixtime`, exact ordered hourly epoch grid |
| Variables | `temperature_2m`, `precipitation`, `snowfall` |
| Units | °C; mm precipitation including snow water equivalent; cm snowfall |
| Staging business key | `(snapshot_id, valid_time_utc)` for this single-point/model snapshot |
| Snapshot identity | Hash of canonical request identity plus exact response-byte SHA-256 |
| Bounds | One point; at most 31 days; one GET; 30-second socket timeout; 1 MiB body limit; no retries |
| Missing values | Preserve explicit nulls and per-row missing-variable flags; never impute zero |
| Unexpected time gaps / duplicates | Reject the whole bounded response, never silently deduplicate |

Temperature is an instantaneous value at the labelled hour. Precipitation and snowfall describe the **preceding hour**. Their staging rows preserve `accumulation_start_utc` as well as the ending `valid_time_utc`. Do not add snowfall centimetres to precipitation millimetres, or add snow water equivalent a second time. No snowfall conversion is needed here. Source fields used by the integration must match; unrelated optional metadata is tolerated. Unknown-unit or non-UTC responses are rejected.

## Provenance, storage and reruns

The portable modules are [weather.py](../src/winterops/weather.py) and [weather_analysis.py](../src/winterops/weather_analysis.py). [weather_batch.py](../scripts/weather_batch.py) is a thin CLI. The acquisition snapshot stores the original response bytes and `retrieval.json` together, including request URL/parameters, UTC retrieval times, HTTP status, Date/ETag when supplied, byte count, SHA-256, returned grid and attribution. Epoch values become aware UTC ISO timestamps without using host local time.

Acquisition validates before publishing the local bundle, stages both files in a temporary sibling directory, then renames that complete directory into place. An existing destination is verified and reused with **zero network calls**; corrupt/conflicting bundles block. Use a new destination to deliberately obtain another version. This is local batch repeatability, not a distributed transaction, concurrent-writer lock or indefinite API-availability guarantee. The timeout is a socket timeout, not a hard whole-process deadline.

Reanalysis can be revised. Repeating the URL does not guarantee identical values or response bytes; the saved byte snapshot is the reproducibility anchor. JSON whitespace and provider generation timing also change byte hashes without necessarily changing measurements. A changed byte hash means a different retrieval snapshot, not automatically a weather revision. No raw municipal observations, vehicle identifiers or trajectories are added.

## Conditional temporal join

The [Windsor activity catalogue](https://opendata.citywindsor.ca/details/224) describes activity-triggered collection at a nominal 15-second interval but does **not** establish the historic CSV `Date time` timezone. The migrated Snow Plow Routes link is not evidence of timestamp semantics for those CSVs. Existing `event_time_unzoned` remains untouched as `TIMESTAMP_NTZ`.

The prototype therefore executes **two hypotheses**: interpret activity wall dates in `America/Toronto`, or interpret them in `UTC`. Neither hypothesis is asserted as fact. All output rows carry `CONDITIONAL_UNVERIFIED_ACTIVITY_TIMEZONE` and `retrospective_only=true`. The original naive data is not modified. Ambiguous/nonexistent DST wall times fail; daily windows support 23/25-hour days using `zoneinfo`. Platforms without an IANA timezone database, commonly Windows, need `python -m pip install tzdata` for local execution.

For a hypothesized day `[start,end)` converted to UTC:

- Temperature uses labels `start <= t < end`.
- Precipitation/snowfall use labels `start < t <= end`, matching their preceding-hour intervals. The midnight accumulation at the start belongs to the previous day.
- Missing hours or null measurements yield a null daily mean/total for that variable, alongside present/expected-hour counts. They do not produce a partial daily estimate.

Join grain is one explicitly selected processing version and source-local date. Source version, pipeline, policy and source boundaries must match the existing selection. Duplicate activity keys or duplicate weather keys block the join. The calendar contains seven days, including January 31/February 1 with **null activity**, because no recorded observations is not proven inactivity. Counts remain unchanged across timezone scenarios.

| January 26 example | Assume Toronto | Assume UTC |
| --- | ---: | ---: |
| Observations | 39,748 | 39,748 |
| Weather-window start, UTC | 05:00 | 00:00 |
| Precipitation, mm | 0.0 | 0.1 |
| Snowfall, cm | 0.00 | 0.07 |

Weather data by [Open-Meteo.com](https://open-meteo.com/), ERA5 / Copernicus C3S, [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Values are transformed into assumed daily windows. This difference demonstrates sensitivity; it does not select the correct timezone. The five observed days total **66,824 valid / 64,336 plow-active / 7,793 spreader-active observations** in either scenario. A day may have plow-active observations without current snowfall because weather lags, prior conditions, collection design and other operational causes matter. No causal, productivity or coverage conclusion follows.

## Leakage and licensing boundaries

These reanalysis values were retrieved after the activity period. They are useful for retrospective explanation, **not features known at an earlier dispatch/prediction time**. A future predictive study needs forecast issue time, valid time, model/run identity, availability/latency and an as-of rule. Simply shifting reanalysis by an hour does not make it available historically. Open-Meteo's [historical forecast archive](https://open-meteo.com/en/docs/historical-forecast-api) stitches early portions of runs; do not assume it proves the full forecast available at a chosen decision time. Individual-run availability must be established separately before forecasting work.

The [API data licence](https://open-meteo.com/en/licence) is **CC BY 4.0**: credit, link to the licence and identify modifications; do not suggest endorsement. This sample credits Open-Meteo and ERA5/Copernicus. ERA5 dataset citation: [10.24381/cds.adbb2d47](https://doi.org/10.24381/cds.adbb2d47). The API data licence is distinct from the server software's AGPL licence. [Free API terms](https://open-meteo.com/en/terms) restrict free service use to noncommercial purposes and set request limits; this personal educational batch fits that scope. Reassess service access terms for any future commercial use. Availability and accuracy are not guaranteed.

Official archive, forecast, terms and licence pages were read through Firecrawl on November 3, 2026; cached page observations were not treated as an API execution. The archive endpoint itself was accessed twice directly: one initial interface probe and one persisted snapshot acquisition. No weather network calls occur in tests or CI.

## Reproduce

From repository root, with Python 3.10+ and an available IANA timezone database:

```bash
python -m pip install -e .
python scripts/weather_batch.py validate
python scripts/weather_batch.py validate --staging-output /tmp/weather-hourly.jsonl
python scripts/weather_batch.py example --output /tmp/weather-example.json
```

Output paths are create-only; choose a new path for another run. Compare the example JSON with [WEATHER_EXAMPLE_RESULTS.json](WEATHER_EXAMPLE_RESULTS.json); all values are reproducible offline from the committed snapshot and recorded aggregates. `validate --staging-output` creates portable typed JSONL; no Spark/weather table is created.

For an intentional new retrieval, where the public API is accessible:

```bash
python scripts/weather_batch.py fetch --output /tmp/winterops-weather-new-snapshot
```

Existing bundle reuse performs no request. No scheduler, streaming infrastructure, forecast model or native weather ingestion is included. The next useful milestone is authoritative activity timezone/clock documentation, followed by an explicitly reviewed weather Delta landing if useful.
