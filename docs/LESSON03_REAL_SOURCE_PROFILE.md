# Lesson 3 — Real-source profiling (read-only)

**Status:** notebook prepared; original Windsor CSV **not acquired or inspected by this project**.

## Why this lesson

Our first two notebooks used a seven-field, fully controlled synthetic dataset. Real engineering begins by identifying an external dataset's actual headers, observation grain, null values, file provenance, timestamp semantics, geographic coordinate reference, and status definitions. We should not reuse the synthetic Silver schema before these are known.

## Source and download

- Official legacy catalogue (weekly snowplow activity CSV listings): <https://opendata.citywindsor.ca/details/224>
- Suggested first file listed by Windsor: `snowplow-2026-01-12_2026-01-18.csv`.
- The catalogue has moved. If the old weekly CSV is inaccessible, check the new portal or contact the City for access. **Do not substitute a road-routes geometry layer and describe it as vehicle GPS telemetry.**
- Do not commit real tracking files to a public repository until their permitted reuse and data-content implications are reviewed.

## Databricks steps

1. Download the selected *real* weekly CSV from the official source in a normal browser (direct-download availability is not independently verified).
2. Upload it to the existing `workspace.default.winterops_raw` Volume.
3. Import `notebooks/03_profile_real_csv.py`; adjust `SOURCE_FILENAME` if the week differs.
4. Run all cells. This **does not create or overwrite any Delta tables**.
5. Record the real column names, file checksum/size, row count, null rates, up to 10 preview rows, and candidate timestamp/coordinate/status fields.
6. Investigate source documentation or sample records for timezone, CRS and vehicle identifier semantics **before** creating a typed real Silver table.

## Exit criteria

- [ ] Actual CSV bytes obtained and SHA-256 recorded.
- [ ] Actual source field names and types inspected.
- [ ] Event timestamp encoding/timezone evaluated (not guessed).
- [ ] Coordinate values and CRS evaluated (X/Y may be projected coordinates, not WGS84 latitude/longitude).
- [ ] Operational status values inspected and meaning verified.
- [ ] File row count, missing-value profile and duplicate/sample limitations recorded.
- [ ] Clear decision made about source record grain and Bronze ingestion approach.

A successful run validates *our ability to inspect the source*, not the City's data quality or any service outcome. Keep the source-data gate open until the evidence is collected.
