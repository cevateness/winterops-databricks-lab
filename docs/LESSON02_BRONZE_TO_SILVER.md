# Lesson 2 — Bronze JSON → Silver typed telemetry

**Status:** local starter prepared, Databricks execution not independently verified.
**Scope:** synthetic training CSV only; do not generalize these column names to City of Windsor activity files.

## Before starting

- Existing `workspace.default.winterops_bronze_snowplow` from notebook 01.
- The synthetic fixture is ingested once (reruns of the unchanged input are safe).
- Exactly one source-file version is registered in Bronze for `winterops_demo_synthetic`.

## Steps in the Databricks website

1. Import `notebooks/02_silver_typing.py` as a **Python notebook**.
2. Review `CATALOG`, `SCHEMA` and the input/output table names in its first code cell. Only change them if your workspace differs.
3. Run all cells. Expected: a new table `workspace.default.winterops_silver_demo_snowplow` and a confirmation `12 distinct records, 13 observations, 3 vehicles, 0 invalid`.
4. Run `sql/silver_checks.sql` in Databricks SQL or as SQL notebook cells. Confirm the first query's values; the output from the second query should show 5, 4, 4 original row occurrences for SYN-001, SYN-002, SYN-003 respectively.
5. Run the notebook again: same table contents, not 24 rows. This is a **demo full refresh**, not a production incremental pipeline.

## What to learn

| Concept | In the notebook | Meaning |
|---|---|---|
| Source contract | `raw_payload_schema` | We consciously specify the **synthetic** record fields rather than infer a business schema. |
| Transformation | `from_json`, `select`, `withColumn` | Spark defines a typed transformation plan; it does not immediately materialize each intermediate DataFrame. |
| Safe conversion | `try_cast` | Invalid numeric/date values become NULL instead of throwing errors; quality tests can flag them. |
| Timestamp semantics | `TIMESTAMP_NTZ` | Represents a time without a known timezone. It is **not** an instant in UTC and is **not** proof the source used Windsor local time. |
| Validation | `quality_issues`, `quality_status` | Data-quality status is explicit; invalid records remain available for inspection. |
| Provenance | Source path/hash, record hash, occurrence count | Connect each Silver row to its Bronze source and preserve original row multiplicity. |
| Persistence | `.saveAsTable()` | Write a persistent Delta table separate from the intermediate DataFrames. |
| Action | `.count()`, `.first()` | Triggers Spark to compute results. |

## Why Bronze has 12 records but the CSV has 13 rows

Notebook 01 grouped two identical sample rows into one Bronze row with `occurrence_count=2`. Notebook 02 **preserves** this count; it does not restore original line order or independently validate that both GPS observations should be treated as service events.

## Architectural limitations worth noting

- Bronze currently aggregates repeated parsed rows, and source-file versions would need explicit selection. The notebook detects multiple synthetic file versions and fails before producing misleading totals.
- These are demo-only coordinate checks (global latitude/longitude ranges), **not Windsor city boundaries**, nor road coverage calculations.
- The synthetic source has timezone-naive strings. Silver stores `event_time_unzoned` as `TIMESTAMP_NTZ`. Before real telemetry analysis, verify source timezone and explicitly convert historical event time to UTC where supported.
- `.mode("overwrite")` is restricted to the separate synthetic Silver table for an easy first lesson. Do not use this as the ingestion policy for historical real-city data.
- This notebook has been syntax-checked locally, but an end-to-end Spark/Delta execution must be tested inside Databricks.

## Completion gate

- [ ] Silver Delta table exists and has 12 distinct records, representing 13 source occurrences.
- [ ] All 3 simulated vehicles are present, no invalid rows.
- [ ] Rerunning notebook 02 does not change record counts.
- [ ] Explain the difference between STRING source fields in JSON and typed DOUBLE/BOOLEAN/TIMESTAMP_NTZ Silver columns.
- [ ] Explain why the demo timestamp is not labeled UTC.

## Real-source gate remains open

Next, obtain and profile a genuine weekly Windsor activity CSV. City portal metadata are insufficient to establish real column names, coordinate type, timezone, or record quality.
