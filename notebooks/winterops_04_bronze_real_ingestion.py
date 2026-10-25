# Databricks notebook source
# MAGIC %md
# MAGIC # WinterOps — Lesson 4: Ingest real Windsor observations into Bronze
# MAGIC
# MAGIC **Purpose:** ingest ONE already-profiled, genuine Windsor activity CSV from the Unity Catalog Volume
# MAGIC into a separate, persistent Delta Bronze table. Each parsed CSV observation becomes a separate
# MAGIC Delta row; identical GPS observations are **not deduplicated** at Bronze.
# MAGIC
# MAGIC **Prerequisite:** successfully completed Lesson 3 and inspected the chosen real source file.
# MAGIC No source-specific timestamp, coordinate or equipment-status meanings are assumed here.
# MAGIC
# MAGIC **Scope:** serialized, one-file-at-a-time learning pipeline; NOT a production ingestion service.
# MAGIC This notebook does not change any synthetic Bronze or Silver tables.

# COMMAND ----------
from pathlib import Path
import hashlib

from pyspark.sql import functions as F

# Change these if your workspace/path differs from Lesson 3.
CATALOG = "workspace"
SCHEMA = "default"
VOLUME = "winterops_raw"
SOURCE_FILENAME = "snowplow-2026-01-12_2026-01-18.csv"
SOURCE_DATASET = "windsor_snowplow_activity"

# Keep real and synthetic data separate.
BRONZE_TABLE = f"{CATALOG}.{SCHEMA}.winterops_bronze_windsor_activity"
FILE_PATH = f"/Volumes/{CATALOG}/{SCHEMA}/{VOLUME}/{SOURCE_FILENAME}"

spark.conf.set("spark.sql.session.timeZone", "UTC")
source_path = Path(FILE_PATH)
if not source_path.is_file():
    raise FileNotFoundError(
        f"Expected the real Windsor CSV at {FILE_PATH}. "
        "Upload it to the Volume first or update SOURCE_FILENAME."
    )
if source_path.suffix.lower() != ".csv":
    raise ValueError("Lesson 4 expects an inspected CSV, not a route shapefile or JSON download.")

# Byte-level provenance: fingerprint the uploaded source file, not Spark's parsed content.
digest = hashlib.sha256()
file_bytes = 0
with source_path.open("rb") as handle:
    for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
        file_bytes += len(chunk)
        digest.update(chunk)
file_sha256 = digest.hexdigest()
print("Source file:", FILE_PATH)
print("Source size (bytes):", file_bytes)
print("Original bytes SHA-256:", file_sha256)

# COMMAND ----------
# Keep the same read contract used in Lesson 3, with all source columns STRING.
raw = (
    spark.read.format("csv")
    .option("header", "true")
    .option("inferSchema", "false")
    .option("encoding", "UTF-8")
    .option("mode", "FAILFAST")
    .load(FILE_PATH)
)

if not raw.columns or any(not c.strip() for c in raw.columns):
    raise ValueError("Missing or empty CSV header; inspect the real source file before ingestion.")
if len(raw.columns) != len(set(raw.columns)):
    raise ValueError("Duplicate source column names must be handled before ingestion.")

source_rows = raw.count()  # Action: triggers Spark to scan the source records.
if source_rows == 0:
    raise ValueError("No observations to ingest. Refuse an empty selective overwrite.")
print("Source CSV observations:", source_rows)
print("Source field names:", raw.columns)

# COMMAND ----------
# Keep one row for EVERY parsed observation. In particular, do NOT group by JSON/hash.
# This retains repeated observations with identical field values.
def quoted(name):
    return F.col("`" + name.replace("`", "``") + "`").alias(name)

payload = F.to_json(
    F.struct(*[quoted(c) for c in raw.columns]),
    options={"ignoreNullFields": "false"},
)

batch = (
    raw.select(payload.alias("raw_record_json"))
    .withColumn("record_sha256", F.sha2(F.col("raw_record_json"), 256))
    .withColumn("source_dataset", F.lit(SOURCE_DATASET))
    .withColumn("source_file_name", F.lit(source_path.name))
    .withColumn("source_file_path", F.lit(FILE_PATH))
    .withColumn("source_file_sha256", F.lit(file_sha256))
    .withColumn("ingested_at_utc", F.current_timestamp())
    .select(
        "source_dataset", "source_file_name", "source_file_path",
        "source_file_sha256", "record_sha256", "raw_record_json",
        "ingested_at_utc",
    )
)

# COMMAND ----------
# Dedicated managed Delta table for real Windsor observations.
spark.sql(f"""
CREATE TABLE IF NOT EXISTS {BRONZE_TABLE} (
  source_dataset STRING,
  source_file_name STRING,
  source_file_path STRING,
  source_file_sha256 STRING,
  record_sha256 STRING,
  raw_record_json STRING,
  ingested_at_utc TIMESTAMP
) USING DELTA
""")

# Work with one immutable file VERSION, identified by path + exact source bytes hash.
# A changed file at the same path is a separate version; Silver will choose the active one.
file_scope = (
    (F.col("source_dataset") == SOURCE_DATASET)
    & (F.col("source_file_path") == FILE_PATH)
    & (F.col("source_file_sha256") == file_sha256)
)
prior_rows = spark.table(BRONZE_TABLE).filter(file_scope).count()

if prior_rows == source_rows:
    print("SKIP: this exact file version is already ingested with the expected row count.")
else:
    # If a prior attempt was incomplete, replace ONLY this file version atomically.
    # replaceWhere is supported on Databricks for nonpartition predicates.
    # Do not use full-table overwrite: it would erase other weeks or file versions.
    def sql_literal(text):
        return "'" + text.replace("'", "''") + "'"

    predicate = (
        f"source_dataset = {sql_literal(SOURCE_DATASET)} AND "
        f"source_file_path = {sql_literal(FILE_PATH)} AND "
        f"source_file_sha256 = {sql_literal(file_sha256)}"
    )
    (
        batch.write.format("delta")
        .mode("overwrite")
        .option("replaceWhere", predicate)
        .saveAsTable(BRONZE_TABLE)
    )
    print(f"WROTE: {source_rows:,} observations to Bronze (previous version count: {prior_rows:,}).")

# COMMAND ----------
# Verify persistent records using a fresh table read.
file_rows = spark.table(BRONZE_TABLE).filter(file_scope)
loaded_rows = file_rows.count()
assert loaded_rows == source_rows, (
    f"Bronze row count {loaded_rows} differs from source {source_rows}."
)

# Duplicate hashes are fine here: their multiplicity remains in the Bronze table.
counts = file_rows.groupBy("record_sha256").count()
summary = counts.agg(
    F.count("*").alias("distinct_payloads"),
    F.sum("count").alias("total_observations"),
    F.sum(F.when(F.col("count") > 1, F.col("count") - 1).otherwise(0))
      .alias("identical_repeated_observations"),
).first().asDict()

print("Verified Bronze table:", BRONZE_TABLE)
print("Source observations:", source_rows)
print("Persisted observations:", loaded_rows)
print("Distinct serialized payloads:", summary["distinct_payloads"])
print("Repeated identical payloads (not removed):", summary["identical_repeated_observations"] or 0)
print("PASS: real Windsor file ingested into a separate persistent Bronze Delta table.")
print("Re-run unchanged input: expected SKIP and same persisted observation count.")
display(file_rows.select(
    "source_file_name", "record_sha256", "raw_record_json", "ingested_at_utc"
).limit(10))

# MAGIC %md
# MAGIC ### What this does **not** establish
# MAGIC - An observation with a repeated payload is not automatically an error.
# MAGIC - The PySpark CSV parser preserves row multiplicity, but not original file row order/number.
# MAGIC - The source CSV bytes are preserved separately in the Volume; serialized JSON is not byte-identical CSV.
# MAGIC - We have not confirmed the meaning, timezone or CRS of any source fields.
# MAGIC - The table may retain multiple versions of the same source path; Silver must select one.
# MAGIC - This serialized one-file-at-a-time design does not guarantee exactly-once behavior for concurrent writers.
