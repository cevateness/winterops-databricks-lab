# Lesson 4 — Real Windsor CSV to persistent Bronze

**Status: prepared, not independently executed in Databricks.** User reported successfully running Lesson 3, but the actual source-profile results are not available in this repository. No real data is bundled.

## What changes from Lesson 3?

- Lesson 3: uploaded file in Unity Catalog Volume → read into a transient Spark DataFrame → profiling, **no Delta write**.
- Lesson 4: read the SAME uploaded CSV → preserve source record as JSON → add file- and record-level hashes → persist to a managed Delta table, **one Bronze row per CSV observation**.
- No Silver conversion yet; actual field semantics remain unverified.

## How to run

1. Confirm you have already uploaded and profiled a genuine Windsor *activity* CSV using Lesson 3. Do not confuse the route geometry layer with vehicle activity.
2. Import `notebooks/04_bronze_real_ingestion.py` into your existing Databricks workspace.
3. Change `SOURCE_FILENAME` at the top to the **exact uploaded filename** if necessary. Keep `SOURCE_DATASET = "windsor_snowplow_activity"` and the separate real Bronze table name.
4. Run all cells. It should report `Source CSV observations = Persisted observations`.
5. Run the notebook **a second time**. It should display `SKIP`, with the same observation count.
6. Execute the SQL in `sql/real_bronze_checks.sql`. Record file hash, counts, actual column names from Lesson 3 and any source anomalies in the data register.

## Why not reuse the original synthetic `01_bronze_ingestion.py` unchanged?

Notebook 01 groups identical parsed records, retaining their count. This is an educational shortcut. For real GPS/activity data we instead retain every observation as its own Bronze row. We cannot safely call two identical records duplicates without understanding source acquisition. The two Bronze tables are separate to avoid mixing these schemas or deleting previously tested synthetic records.

## Idempotency mechanics

- A file version is identified by `(source_dataset, source_file_path, source_file_sha256)`.
- If exactly that file version has already been ingested with the expected row count, the notebook skips the write.
- If the version is absent or incomplete, Delta `replaceWhere` atomically replaces **only rows matching that file version**. Other weeks/versions remain in the table.
- No unordered DataFrame row index is used as a key; repeated GPS observations are kept as separate rows even if they share `record_sha256`.
- The current pilot assumes **serialized execution** and one uploaded file per run. It does not provide a concurrency-safe ingestion manifest or a production streaming guarantee.

Delta selective overwrite reference: <https://docs.databricks.com/aws/en/delta/selective-overwrite>

## Validation and limitations

- `source_rows` must equal persistent `loaded_rows`, including all repeated identical payloads.
- Delta table content survives notebook/session restarts; DataFrames and temporary views do not.
- Original source file persists independently in the Volume.
- Repeated identical payloads are not automatically invalid, and their file row order is not preserved.
- A source file re-uploaded with different bytes under the same path generates a **new file version**. Silver must decide the active version explicitly.
- The `SKIP` condition validates file identity and row count, not a complete per-row audit of a manually altered Delta table.
- An ingest timestamp describes processing time, not vehicle event time; temporal interpretation awaits field profiling.

## Next step (only after source profile is reviewed)

Define a source-specific **Silver contract**: timestamp parsing/timezone, latitude/longitude or projected coordinate system, status boolean semantics, vehicle identifier meaning, and explicitly documented quality flags. Do not copy the synthetic schema blindly.
