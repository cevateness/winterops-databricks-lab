# Databricks notebook source
# MAGIC %md
# MAGIC # WinterOps — 01. Raw snowplow telemetry to Bronze Delta
# MAGIC **Scope:** one uploaded CSV at a time. This notebook intentionally assumes **no real source-specific column names**.
# MAGIC
# MAGIC Original file: Unity Catalog managed volume. Bronze Delta rows: JSON of all parsed fields, file SHA-256, record SHA-256, occurrence count, and ingest metadata.
# MAGIC
# MAGIC Start with the **synthetic demo**; switch to an inspected official Windsor CSV when available. A successful synthetic test does not validate the real-city source schema.

# COMMAND ----------
from pathlib import Path
import hashlib

from pyspark.sql import functions as F

# Edit these four constants if your Databricks workspace differs.
CATALOG = "workspace"
SCHEMA = "default"
VOLUME = "winterops_raw"
SOURCE_FILENAME = "snowplow_demo_synthetic.csv"
SOURCE_DATASET = "winterops_demo_synthetic"  # change to "windsor_snowplow_activity" for real official source

TABLE_NAME = f"{CATALOG}.{SCHEMA}.winterops_bronze_snowplow"
FILE_PATH = f"/Volumes/{CATALOG}/{SCHEMA}/{VOLUME}/{SOURCE_FILENAME}"
spark.conf.set("spark.sql.session.timeZone", "UTC")

# The file must be uploaded into a Unity Catalog volume first.
source_path = Path(FILE_PATH)
if not source_path.is_file():
    raise FileNotFoundError(
        f"Upload your CSV file to {FILE_PATH} from Catalog Explorer before running this notebook."
    )

# COMMAND ----------
# Read the SOURCE BYTES in chunks for a stable fingerprint.
# This is intentionally not an inference about fields or business identifiers.
digest = hashlib.sha256()
with source_path.open("rb") as handle:
    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
        digest.update(chunk)
source_file_sha256 = digest.hexdigest()
print("Input path:", FILE_PATH)
print("SHA-256:", source_file_sha256)

# COMMAND ----------
raw = (
    spark.read.format("csv")
    .option("header", "true")
    .option("inferSchema", "false")  # preserve leading zeroes and raw textual values
    .option("mode", "FAILFAST")
    .load(FILE_PATH)
)
if not raw.columns or raw.limit(1).count() == 0:
    raise ValueError("Input CSV has no header or no data rows; inspect the source first.")
if len(raw.columns) != len(set(raw.columns)):
    raise ValueError("Duplicate CSV column names need explicit treatment before import.")

print("Raw source columns:", raw.columns)
print("Input row count:", raw.count())

# COMMAND ----------
# Preserve arbitrary raw fields in JSON without applying an unverified business schema.
# Quoting handles whitespace and special characters in CSV headers.
quoted_cols = [F.col("`" + name.replace("`", "``") + "`").alias(name) for name in raw.columns]
records = raw.select(
    F.to_json(F.struct(*quoted_cols), options={"ignoreNullFields": "false"})
    .alias("raw_record_json")
)

# Group identical parsed records, rather than silently removing duplicates.
# If 2 physically identical rows occur in a single source file, occurrence_count=2.
batch = (
    records.groupBy("raw_record_json").count()
    .withColumnRenamed("count", "occurrence_count")
    .withColumn("record_sha256", F.sha2("raw_record_json", 256))
    .withColumn("source_dataset", F.lit(SOURCE_DATASET))
    .withColumn("source_file_name", F.lit(source_path.name))
    .withColumn("source_file_path", F.lit(FILE_PATH))
    .withColumn("source_file_sha256", F.lit(source_file_sha256))
    .withColumn("ingested_at_utc", F.current_timestamp())
    .select(
        "source_dataset", "source_file_name", "source_file_path",
        "source_file_sha256", "record_sha256", "raw_record_json",
        "occurrence_count", "ingested_at_utc"
    )
)

# COMMAND ----------
# Create one managed Delta table with a stable ingestion contract.
# Raw columns are intentionally NOT modeled as typed fields until Silver.
spark.sql(f"""
CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
  source_dataset STRING,
  source_file_name STRING,
  source_file_path STRING,
  source_file_sha256 STRING,
  record_sha256 STRING,
  raw_record_json STRING,
  occurrence_count BIGINT,
  ingested_at_utc TIMESTAMP
) USING DELTA
""")

batch.createOrReplaceTempView("winterops_bronze_batch")
before = spark.table(TABLE_NAME).count()

# Same path + same file content + same parsed record -> insert once.
# Different SHA under same path -> a new version, not an accidental overwrite.
spark.sql(f"""
MERGE INTO {TABLE_NAME} target
USING winterops_bronze_batch source
ON target.source_file_path = source.source_file_path
   AND target.source_file_sha256 = source.source_file_sha256
   AND target.record_sha256 = source.record_sha256
WHEN NOT MATCHED THEN INSERT (
  source_dataset, source_file_name, source_file_path,
  source_file_sha256, record_sha256, raw_record_json,
  occurrence_count, ingested_at_utc
) VALUES (
  source.source_dataset, source.source_file_name, source.source_file_path,
  source.source_file_sha256, source.record_sha256, source.raw_record_json,
  source.occurrence_count, source.ingested_at_utc
)
""")

after = spark.table(TABLE_NAME).count()
print("Bronze unique-record rows before:", before)
print("Bronze unique-record rows after:", after)
print("New unique-record rows inserted:", after - before)

# COMMAND ----------
# Acceptance checks — verify this particular file version's row multiplicity.
file_version = spark.table(TABLE_NAME).filter(
    (F.col("source_file_path") == FILE_PATH)
    & (F.col("source_file_sha256") == source_file_sha256)
)
stats = file_version.agg(
    F.count("*").alias("distinct_record_count"),
    F.sum("occurrence_count").alias("source_row_count")
).first()
source_row_count = raw.count()
assert stats["source_row_count"] == source_row_count, (
    "Row counts mismatch — investigate incomplete import or changed file! "
    f"Source={source_row_count}, Bronze={stats['source_row_count']}"
)
assert file_version.groupBy("record_sha256").count().filter("count > 1").count() == 0
print("PASS: source row multiplicity preserved for this file version")
print("PASS: SHA-keyed Bronze entries are unique for this file version")
print("Re-run unchanged input: expected newly inserted unique rows = 0")
display(file_version.select(
    "source_file_name", "record_sha256", "occurrence_count", "raw_record_json"
).limit(10))
