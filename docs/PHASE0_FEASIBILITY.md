# Phase 0 — Source feasibility (2026-10-18)

## Decision

Target a **single historical weekly snowplow activity CSV** in Windsor, Ontario. Proposed initial file: `snowplow-2026-01-12_2026-01-18.csv`. This week is an initial retrieval target, **not confirmed to contain usable snowplow events**. Adjacent weeks are fallback candidates.

## Confirmed from public pages

1. City of Windsor's legacy [Winter Control – Snowplow Activity](https://opendata.citywindsor.ca/details/224) lists weekly CSV downloads for winter 2025–2026 and describes X/Y positions and plow/wing/spreader/engine state during activity at approximately 15-second intervals.
2. The catalogue notes its migration to [a new ArcGIS-based portal](https://open-data-portal-citywindsor.hub.arcgis.com/datasets/b4cf042dbf674d2e8c78990ac627d415_62/about). The replacement dataset is named **Snow Plow Routes** and may not be equivalent to the historic **activity observations**. Verify its **geometry type, fields and timestamps** before substituting.
3. [Windsor Open Government Licence](https://opendata.citywindsor.ca/Documents/OpenDataTermsofUse.pdf) grants lawful reuse including commercial use, subject to acknowledgement, exclusions (notably personal information and official marks), non-endorsement and warranty disclaimer. This confirms general city open data terms; verify any special conditions on the precise downloaded layer/file.
4. Databricks Free Edition restricts notebook outbound access. A manual download to the computer, followed by upload to a Unity Catalog volume, is a supported route: [Databricks documentation](https://docs.databricks.com/aws/en/getting-started/import-visualize-data).
5. A third-party older dataset listing contains possible field names and a small preview, but its download requires acceptance of separate commercial/research terms. **We do not use or redistribute that third-party data; its fields are not verified as the current city CSV schema.**

## Not verified — blocker to declaring Phase 0 complete

- Actual bytes of a weekly city activity file could **not be retrieved in this execution environment** (external connection / retrieval restrictions). The existence of a catalogue entry is **not confirmation of successful download**.
- Original CSV header, delimiter, quoting, sample values, number of rows and city-coordinate precision remain unverified.
- Native event timestamps, vehicle ID meaning, plow/wing/spreader status availability, event-time timezone and null semantics are unverified.
- The current ArcGIS feature layer may contain **routes rather than vehicle pings**. We must not conflate it with historical telemetry.
- Apparent activity does **not** prove a road was fully serviced; not every contracted vehicle is necessarily represented.

## Exit criteria

- [ ] Download one city-published weekly activity CSV through the official link or a confirmed equivalent.
- [ ] Run `scripts/inspect_csv.py` on the **real file** and save its summary (SHA, rows, headers, null counts).
- [ ] Confirm at least latitude/longitude or coordinate pair, a timestamp with timezone interpretation, and one activity status field; otherwise redefine the first analytics objective.
- [ ] Identify vehicle identity semantics where present (do **not** assume an integer code is fleet size).
- [ ] Confirm a field-level data dictionary or record uncertainties explicitly, including coordinates' CRS and whether data are actual pings or inferred routes.
- [ ] Check privacy / publication implications of GPS before releasing maps or row-level datasets.
- [ ] Verify repeatable Bronze import into a Databricks Delta table without duplicate inflation.

## Recommended manual acquisition route

1. Visit https://opendata.citywindsor.ca/details/224 .
2. Locate the legacy weekly CSV link, e.g. `snowplow-2026-01-12_2026-01-18.csv`.
3. Try a browser download, or open the city's replacement portal. **Do not silently substitute a line-route feature layer for event-level telemetry.**
4. Inspect locally: `python scripts/inspect_csv.py path/to/snowplow-*.csv`.
5. Upload to `/Volumes/workspace/default/winterops_raw/` for the first notebook execution.

## Open engineering questions

- Which source timestamp should be interpreted in `America/Toronto`, and what offset / daylight-saving behavior occurs?
- Are records conditional on active plow/spreader rather than regular GPS position pings, causing incomplete trajectories?
- Which data are true observations versus estimated coverage? What missing-device biases exist?
- What is the most natural operational unit later: road segment, route, ward, hex cell, crew shift or storm event?

**Boundary:** No forecasts, optimization savings, or service-completion claims at Phase 0.
