# Lesson 5 — Real Windsor Silver typing and quality classification

## Prerequisites and evidence

From Lesson 4 and the user's SQL profiling of `snowplow-2026-01-12_2026-01-18.csv`:

- Bronze rows: **110,337**
- Repeated in-body CSV header rows: **26**
- Non-header candidate observations: **110,311**
- Null/out-of-world-range coordinates among candidate observations: **0**
- Confirmed JSON keys: `Truck`, `Date time`, `Latitude`, `Longitude`, `Plow status`, `Spreader status`, `Engine status`

Do not assume 110,311 records are fully valid. Timestamp, status, geographic, and duplicate policies have not been verified.

## Run

1. Import `notebooks/05_silver_real_windsor.py` as a Databricks Python notebook.
2. Set `CATALOG`, `SCHEMA`, `VOLUME`, and `SOURCE_FILENAME` to the Bronze source as used in Lesson 4.
3. If Bronze contains multiple `source_file_sha256` versions for the path, review the Bronze inventory and explicitly supply `SOURCE_FILE_SHA256`. The notebook refuses to choose arbitrarily.
4. **Run all**. It creates `workspace.default.winterops_silver_windsor_week_sample`, a one-week **learning** snapshot. It never overwrites Bronze or the synthetic tables.
5. Run `sql/real_silver_checks.sql`. Check Bronze/Silver row parity, repeated headers, valid/invalid distributions, and repeated-payload patterns.
6. Rerun to compare. Expected logical counts stay the same; a full-refresh creates a new Delta table version.

## Data contract and design

- `event_time_unzoned` is `TIMESTAMP_NTZ`. Timezone remains **unverified**; no UTC conversion.
- `truck_id` is a trimmed string (leading zeroes preserved).
- GPS coordinates are doubles; only worldwide latitude/longitude ranges are checked, not road location or city limits.
- Status values are strictly interpreted as case-insensitive `True`/`False`. Other encodings are flagged as invalid for review, not guessed.
- `HEADER` observations are retained in the Silver quality-classification table but must be excluded from activity metrics.
- Other parsing issues receive `quality_status='INVALID'` and explicit `quality_issues` strings.
- Exact repeated payloads receive `has_repeated_payload=True` and `payload_occurrences>1`; they are **not** automatically treated as invalid.
- Source file identity, version hash, record hash and Bronze ingestion timestamp carry through.
- `quality_status='VALID'` only means that the current checks passed; it is **not** evidence of correct road-service completion.

## Non-goals

- No Gold operational metrics or capacity decisions yet.
- No actual Windsor service-area geofencing or map matching.
- No assumptions about vehicle work rates, human schedules, or route completion.
- No future-data leakage or operational-time forecasts.
- Not a multi-week incremental production Silver architecture.

## Acceptance checks

1. The Silver row count matches the selected Bronze file version exactly.
2. All 26 identified repeated headers are classified `HEADER` (assuming the unchanged source version).
3. All other invalid observations (if any) are visible via explicit quality codes.
4. Exact payload repetitions remain countable in Silver.
5. The rerun has unchanged logical metrics.
6. The synthetic Bronze/Silver tables remain untouched.
