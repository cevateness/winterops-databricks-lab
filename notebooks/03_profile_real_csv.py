# Databricks notebook source
# MAGIC %md
# MAGIC # WinterOps — Lesson 3: Profile a real Windsor source CSV
# MAGIC
# MAGIC **Purpose:** inspect an actual source file *before* designing a schema or loading it into Bronze.
# MAGIC This notebook is read-only: it neither creates nor overwrites Delta tables.
# MAGIC
# MAGIC **Data contract status:** the City of Windsor advertises a weekly snowplow activity CSV,
# MAGIC but we have not verified its real column names, timestamp timezone, coordinate reference system,
# MAGIC vehicle identifier semantics, or row-level quality. Do not apply the synthetic Silver schema.
# MAGIC
# MAGIC Source catalogue: https://opendata.citywindsor.ca/details/224
# MAGIC The old catalogue is being migrated; if a weekly CSV cannot be downloaded, leave the
# MAGIC real-data gate open rather than substituting a routes/road-geometry feature layer.

# COMMAND ----------
from pathlib import Path
import hashlib
import json

from pyspark.sql import functions as F

CATALOG = "workspace"
SCHEMA = "default"
VOLUME = "winterops_raw"

# Download this listed historical weekly file from the official Windsor catalogue,
# then upload it to the Unity Catalog Volume (modify name if you chose another week).
SOURCE_FILENAME = "snowplow-2026-01-12_2026-01-18.csv"
FILE_PATH = f"/Volumes/{CATALOG}/{SCHEMA}/{VOLUME}/{SOURCE_FILENAME}"

source_path = Path(FILE_PATH)
if not source_path.is_file():
    raise FileNotFoundError(
        f"Upload the REAL Windsor CSV to {FILE_PATH} before running this notebook. "
        "Do not use snowplow_demo_synthetic.csv for this lesson."
    )
print(f"Profiling input file: {FILE_PATH}")

# COMMAND ----------
# Inspect file-level provenance. This reads the original file bytes in streaming chunks
# (no driver-side collection of the entire dataset into memory).
file_hasher = hashlib.sha256()
file_size = 0
with source_path.open("rb") as handle:
    for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
        file_size += len(chunk)
        file_hasher.update(chunk)

print("Source file bytes:", file_size)
print("Source file SHA-256:", file_hasher.hexdigest())

# COMMAND ----------
# Load as strings. We deliberately avoid inferSchema because guessing types can erase
# leading zeros and introduce inconsistent typing. Fail fast on CSV parsing errors.
raw = (
    spark.read.format("csv")
    .option("header", "true")
    .option("inferSchema", "false")
    .option("encoding", "UTF-8")
    .option("mode", "FAILFAST")
    .load(FILE_PATH)
)

print("Original source column names:")
for idx, column_name in enumerate(raw.columns, start=1):
    print(f"  {idx:>2}. {column_name!r}")

print("\nPySpark schema (source fields intentionally STRING):")
raw.printSchema()

if not raw.columns:
    raise ValueError("No CSV columns found; inspect the source file/header format.")

# COMMAND ----------
# A single aggregate action performs the full-row count and per-column null/blank audit.
# Prefix aliases with column indices to avoid alias conflicts with source column names.
def quote_column(name):
    return F.col("`" + name.replace("`", "``") + "`")

missing_exprs = [
    F.sum(
        F.when(quote_column(col).isNull() | (F.trim(quote_column(col)) == ""), 1)
        .otherwise(0)
    ).cast("long").alias(f"missing_{i}")
    for i, col in enumerate(raw.columns)
]

metrics = raw.agg(F.count("*").alias("row_count"), *missing_exprs).first().asDict()
row_count = int(metrics["row_count"])

print("\nRow count:", row_count)
print("Column count:", len(raw.columns))
print("\nColumn completeness (nothing is filtered or corrected):")
for i, column_name in enumerate(raw.columns):
    missing = int(metrics[f"missing_{i}"] or 0)
    pct = 0 if row_count == 0 else 100 * missing / row_count
    print(f"  {column_name}: {missing:,} missing/blank ({pct:.2f}%)")

if row_count == 0:
    print("CAUTION: the selected weekly file contains no data rows.")

# COMMAND ----------
# Preview a small number of original source rows without converting to domain types.
# Keep this sample on screen (or share only appropriate, non-sensitive fields).
print("\nSample source rows (at most 10):")
display(raw.limit(10))

# Candidate names for future data contracts only; not confirmed semantics.
terms = ("time", "date", "lat", "lon", "coord", "vehicle", "unit", "truck",
         "plow", "spread", "wing", "engine", "status", "gps", "east", "north")
possible = [c for c in raw.columns
            if any(term in c.lower() for term in terms) or c.strip().lower() in {"x", "y", "id"}]
print("\nCandidate operational fields (names only, not validated):", possible)

# COMMAND ----------
# Optional, bounded duplicate illustration: fingerprint at most 10,000 parsed rows.
# This is NOT a full-file duplicate rate or an exact guarantee of stable sampling.
MAX_SAMPLE = 10_000
payload = F.to_json(
    F.struct(*[quote_column(c).alias(c) for c in raw.columns]),
    options={"ignoreNullFields": "false"},
)
small = raw.limit(MAX_SAMPLE).select(F.sha2(payload, 256).alias("record_fingerprint"))
counts = small.groupBy("record_fingerprint").count()
summary = counts.agg(
    F.count("*").alias("sample_unique_rows"),
    F.sum("count").alias("sample_observations"),
    F.sum(F.when(F.col("count") > 1, F.col("count") - 1).otherwise(0)).alias("sample_repeats"),
).first().asDict()

print("\nSampled duplicate check (max 10,000 parsed source records):", summary)
print("No Bronze/Silver tables were modified.")
print("NEXT: confirm actual field definitions, time zone, coordinate system, and whether sampling exposed malformed values.")
