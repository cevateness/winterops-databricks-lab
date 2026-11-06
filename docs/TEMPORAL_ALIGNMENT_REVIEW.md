# Source clock evidence and first analytical review — 2026-11-04

PR #17 is merged. This follow-up starts from main `1a351c9445c0a7de36e3d028755460046b144d45`. It reuses the completed spatial collection and saved matches; it does not collect weather again, change ingestion/Gold, or deploy anything.

## What the source evidence establishes

**America/Toronto is strongly corroborated for the four pinned January weeks. The original CSV export timezone is still not explicitly documented.** Keep the original `TIMESTAMP_NTZ` and both labelled analytical hypotheses. The working interpretation has stronger evidence now; `activity_timezone_verified` remains false in the existing artifacts.

| Evidence actually retrieved | Finding | Limit |
| --- | --- | --- |
| [Original Windsor catalogue](https://opendata.citywindsor.ca/details/224) | Links its replacement ArcGIS dataset; describes activity-triggered reporting and weekly exports | No explicit CSV timezone. Scraper output's `metadata.timezone` is not a source field definition; the downloaded HTML contains no corresponding clock statement |
| [Replacement dataset](https://open-data-portal-citywindsor.hub.arcgis.com/datasets/b4cf042dbf674d2e8c78990ac627d415_62/about) and [layer metadata](https://mappmycity.ca/arcgis/rest/services/open_data_services/governmentservices/MapServer/62?f=pjson) | Despite its `snowplow_route` name, this is point telemetry with `record_date: esriFieldTypeDate`. `dateFieldsTimeReference` declares Eastern Standard Time with daylight saving; `datesInUnknownTimezone=false` | Current published-layer metadata, not a signed contract for the historical CSV exporter. Generic description placeholders are not lineage proof |
| Public layer grouped by local year/month/day/hour, January 5 through February 1 | All **325 occupied source hours / 298,051 observations** exactly match the selected local reconstruction. Zero differing hourly counts | Aggregate crosswalk, not full record identity or a current native Delta read |
| First/last `record_date` only, each of four weeks | **8/8 published UTC timestamp hours match Toronto; 0/8 match UTC**. January local hour → UTC hour is +5 hours | Eight endpoint samples, not every record. Does not test DST transitions or another export period |

[Recorded evidence fixture](../data/fixtures/source_time_evidence.json) preserves the complete public aggregate response, a labelled metadata projection, eight timestamp-only sample projections, query parameters and original response hashes. It contains no coordinates, geometry or vehicle identifiers. Existing [four-week selection](FOUR_WEEK_SELECTION.json) and the hash-pinned private replay archive establish which source versions the local profile represents. A mutable public layer may differ on a later retrieval; replay uses the recorded snapshot.

### An API representation trap worth retaining

[ArcGIS MapServer query documentation](https://developers.arcgis.com/rest/services-reference/enterprise/query-map-service-layer/#date-time-queries) says date literals should use the field's declared timezone and returned dates use UTC (with an explicit unknown-timezone exception). The scoped direct-feature samples behave accordingly.

However, the first-week `MIN(record_date)` / `MAX(record_date)` response, whose fields are also labelled `esriFieldTypeDate`, returns `1767597961000` / `1768174425000`. These encode the CSV wall clocks as though UTC. Direct feature values are `1767615961000` / `1768192425000`, five hours later. The corresponding CSV boundaries are `2026-01-05 07:26:01` and `2026-01-11 23:33:45`. Count and local-hour grouping still reconcile.

This is an **observed difference between response shapes**; its underlying server cause is unverified. Do not infer the source clock from aggregate date epochs or silently apply one universal date validator. The review uses direct timestamp-field samples plus explicit field metadata. A whole-profile transfer-limit flag rejects an incomplete profile; a flag on an intentionally limited top-one endpoint sample is expected. This distinction is captured in offline regression tests and requires no extra ingestion API calls.

## First analytical result from the saved weather matches

Executed the new CLI against the SHA-256-pinned November 3 replay ZIP. [Exact city-day aggregate output](TEMPORAL_REVIEW_RESULTS.json) contains **50 rows: 25 observed source days × two alternative timezone hypotheses**. Each hypothesis independently retains 298,051 observations, 325 source hours, 842 cell-hours and all 863 observations outside the original source review envelope. Hypotheses must never be added together. There are zero missing current measurements in this archive.

The daily weather columns describe **sampled activity grid/hours**, including the explicitly retained regional context. They are not calendar-day minima/maxima, citywide weather totals, or continuous exposure. Multiple activity bins mapping to one grid/hour contribute weather once; precipitation is never summed across locations. Missing source days are absent, not manufactured zero-activity days. The two-hour antecedent matches remain in the original archive but are not summed in this summary because overlapping windows would double count.

Examples under the corroborated Toronto interpretation:

| Source-local day | Observations | Occupied source hours | Sampled temperature range °C | Snow-positive sampled grid/hours |
| --- | ---: | ---: | ---: | ---: |
| January 14 | 31,222 | 14 | −8.9 to 4.1 | 41 of 56 |
| January 15 | 52,115 | 24 | −14.5 to −7.0 | 35 of 86 |
| January 25 | 50,963 | 23 | −13.1 to −8.4 | 73 of 85 |

These show that the historical join can describe weather around recorded activity. They do not establish a weather response model, causal effect, labor hours, coverage, availability or productivity. Activity-triggered telemetry creates selection bias: weather is sampled where and when activity was recorded. The [City's snow-removal page](https://www.citywindsor.ca/residents/roads-sewers-sidewalks/snow-removal) also cautions that contracted equipment is absent from its map. Neither counts nor an absent day establish total municipal service. Current policy descriptions are not assumed to describe January 2026 practices.

Weather attribution: Open-Meteo, CC BY 4.0; requested ERA5 historical reanalysis. Retain the existing request/retrieval provenance and request-parameter-only model attestation. Reanalysis uses information unavailable at historical decision time; these outputs remain retrospective and are not forecasting features. See [weather contract and limitations](WEATHER_INTEGRATION.md).

## Reproduce and review

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
python scripts/review_temporal_alignment.py --output /tmp/winterops-clock-review.json
```

The default command uses only committed public evidence; it performs zero HTTP/native calls. Outputs are create-only, so choose a new path for a later run. To reproduce the full committed daily result, download the existing private `WinterOps_weather_integration_20261103.zip` outside the checkout, then run:

```bash
python scripts/review_temporal_alignment.py \
  --archive /path/outside/repository/WinterOps_weather_integration_20261103.zip \
  --output /tmp/winterops-temporal-review.json
```

The CLI checks the archive's exact byte count and SHA against [the existing execution receipt](WEATHER_ACTIVITY_EXECUTION_RESULTS.json), reads only the bounded known JSON member without extracting paths, validates paired match grains/counts and shared weather facts, and emits aggregate-only JSON. Compare it with `docs/TEMPORAL_REVIEW_RESULTS.json`; no private archive is required for ordinary CI.

Local verification: **307 tests passed**, including 18 new clock/grain/CLI regressions; syntax checks and all existing CI fixture, SQL/Job render and offline weather checks passed. The native proposal SHA and all 13 public dependency pins remain unchanged. The private-archive execution produced the exact committed aggregate JSON. CI for the review commit is linked in the PR. These checks do not imply Spark/notebook or Databricks execution.

## Engineering lessons and next boundary

- **Business keys and grain:** source-version/policy/bin/hour identifies one activity aggregate; hypothesis adds an alternative temporal interpretation. A returned weather grid/time is a separate key. Their multiplicities must be handled before aggregation.
- **Contracts and evidence:** a field timezone, a direct date value, an aggregate statistic and a browser timezone have different meanings. The regression fixture records actual service behavior instead of adding generic rejection rules.
- **Recovery and incremental loading:** this task consumes immutable saved artifacts. It does not replay successful ingestion, reset manifests or widen transaction boundaries. Hash pins make analysis reproducible without more API traffic.
- **Observability:** report differing hourly counts, endpoint agreement, paired totals and missing measurements. Do not hide disagreement behind a passing grand total. These are analysis/release checks, not additional routine ingestion gates.

The next useful milestone is a compact explanatory view of activity and weather with the sampling limitations visible, or a custodian-confirmed export clock. A precise question for the data owner is: “Does `Date time` in the four January 2026 weekly CSV exports use Eastern local civil time, including DST, and how are ambiguous/nonexistent clock times represented?” No message was sent. Until that contract is established, do not globally promote the CSV clock or remove sensitivity outputs.

Native Gold publication remains blocked by inaccessible pinned private matrices and secure workspace binding. This task issued **zero Databricks calls and zero new weather calls**. Existing views, ingestion tables, Jobs, aliases and the frozen native plan remain unchanged.
