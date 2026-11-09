# Continuous public-reference weather, V3.1

Four actual Open-Meteo historical archive responses and their exact retrieval metadata. Windsor centre (42.3149, −83.0364) and a predeclared regional north sensitivity reference (42.5, −83.0) are fixed public locations, not activity-derived requests. The returned centres are (42.25, −83.0) and (42.5, −83.0). They are not meteorological stations or asserted grid polygons.

Each reference requests January 4–February 3 and February 4–23, 2026 inclusive, in UTC, ERA5, nearest grid / elevation disabled. 2,448 unique grid/hour facts; four GETs; 64,961 response bytes; no retries. Source response does not independently name the model: attestation is request-parameter-only. Original January activity-matched weather archives are preserved separately.

Temperature is instantaneous °C. Precipitation is preceding-hour mm (including rain/snow water equivalent); snowfall is preceding-hour cm. A source-local activity hour [h,h+1) uses the accumulation ending h+1, while two-hour antecedent accumulation uses intervals ending h−1 and h. UTC and Toronto are separate clock hypotheses. The continuous calendar is created independently of telemetry, then activity is left joined; absent telemetry is unknown activity.

Source: [Open-Meteo historical API](https://open-meteo.com/en/docs/historical-weather-api), [terms and CC BY 4.0 attribution](https://open-meteo.com/en/terms); historical ERA5 reanalysis via Open-Meteo. Retrospective context, not decision-time forecast data. Reuse with attribution. No re-fetch is needed for normal tests or dashboard review.

Validate and reproduce: `python scripts/replay_weather_exposure.py --output <temporary-output.json>`. Full source/grain and missingness definitions: `docs/ROAD_EVIDENCE_V31.md`.
