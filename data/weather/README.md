# Public historical weather sample

This fixed-point sample is an API/provenance and temporal-alignment fixture. It is **not location-matched to municipal activity**. See the [activity-driven revision and live spatial blocker](../../docs/WEATHER_ACTIVITY_REVISION.md).

`windsor_era5_20260104_20260202/response.json` is an unmodified API response acquired on November 3, 2026. `retrieval.json` binds the exact bytes to request, retrieval times and source metadata. This is public weather at one chosen Windsor-area point, not municipal vehicle telemetry. The 720 UTC hours include calendar-boundary padding.

Weather data by [Open-Meteo.com](https://open-meteo.com/), ERA5 / Copernicus C3S, under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). ERA5 citation: [10.24381/cds.adbb2d47](https://doi.org/10.24381/cds.adbb2d47). The raw response is unchanged; staging and daily examples transform times/units into explicitly named fields and conditional calendar aggregates. No provider endorsement is implied.

See [source contract, licence, limitations and reproduction](../../docs/WEATHER_INTEGRATION.md). Run `python scripts/weather_batch.py validate` to check hashes, types, time grid, units and metadata offline. Repeating the URL may produce different bytes; retain this snapshot for exact reproduction.
