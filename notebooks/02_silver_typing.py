# Databricks notebook source
# MAGIC %md
# MAGIC # WinterOps — 02. Typed Silver telemetry (synthetic learning exercise)
# MAGIC
# MAGIC **Goal:** read the Bronze Delta table created by notebook 01, parse the raw JSON into typed columns, check data quality, and publish a **demo-only** Silver Delta table.
# MAGIC
# MAGIC **Scope:** the synthetic CSV fixture ONLY. This notebook deliberately refuses to process the unverified real Windsor schema.
# MAGIC **Do not interpret** `event_time_unzoned` as UTC or Toronto local time. The demo timestamps do not encode a timezone.
# MAGIC
# MAGIC **Important:** the original Bronze design groups identical source rows. Silver retains the `occurrence_count`; it does not restore their original physical row ordering. We will revisit that design before working with actual GPS telemetry.

# COMMAND ----------
from pyspark.sql import functions as F
from pyspark.sql.types import StructType, StructField, StringType

CATALOG = "workspace"
SCHEMA = "default"
SOURCE_DATASET = "winterops_demo_synthetic"

BRONZE_TABLE = f"{CATALOG}.{SCHEMA}.winterops_bronze_snowplow"
# A *separate*, demo-only output table so we do not overwrite future real data.
SILVER_TABLE = f"{CATALOG}.{SCHEMA}.winterops_silver_demo_snowplow"

bronze = spark.table(BRONZE_TABLE).filter(F.col("source_dataset") == SOURCE_DATASET)
if bronze.limit(1).count() == 0:
    raise ValueError(
        "No synthetic Bronze records found. Run notebook 01 against "
        "snowplow_demo_synthetic.csv first."
    )

# Fail rather than double-count multiple source file versions.
file_versions = bronze.select("source_file_path", "source_file_sha256").distinct().collect()
if len(file_versions) != 1:
    raise ValueError(
        f"Expected exactly one synthetic file version; found {len(file_versions)}. "
        "Inspect Bronze provenance and choose a version explicitly before producing Silver."
    )

print("Reading Bronze table:", BRONZE_TABLE)
print("Source file version SHA-256:", file_versions[0]["source_file_sha256"])

# COMMAND ----------
# Explicitly declare the JSON schema of *our synthetic sample*.
# Do not assume this is the real Windsor telemetry schema.
raw_payload_schema = StructType([
    StructField("Latitude", StringType(), True),
    StructField("Longitude", StringType(), True),
    StructField("Date_Time", StringType(), True),
    StructField("Is_Plow_Status", StringType(), True),
    StructField("Is_Spreader_Status", StringType(), True),
    StructField("Is_Engine_Status", StringType(), True),
    StructField("Vehicle_ID", StringType(), True),
])

parsed = bronze.withColumn(
    "payload", F.from_json(F.col("raw_record_json"), raw_payload_schema)
)

# In the source, Boolean states are text. Interpret only TRUE and FALSE.
# Missing or unexpected values become NULL and are flagged later.
def strict_boolean(column):
    normalized = F.upper(F.trim(column))
    return (
        F.when(normalized == "TRUE", F.lit(True))
         .when(normalized == "FALSE", F.lit(False))
         .otherwise(F.lit(None).cast("boolean"))
    )

# try_cast converts malformed values to NULL instead of failing the whole job.
# TIMESTAMP_NTZ deliberately does *not* assign a timezone.
typed = parsed.select(
    "source_dataset", "source_file_name", "source_file_path",
    "source_file_sha256", "record_sha256", "occurrence_count", "ingested_at_utc",
    F.trim(F.col("payload.Vehicle_ID")).alias("vehicle_id"),
    F.expr("try_cast(payload.Latitude AS DOUBLE)").alias("latitude"),
    F.expr("try_cast(payload.Longitude AS DOUBLE)").alias("longitude"),
    F.expr("try_cast(payload.Date_Time AS TIMESTAMP_NTZ)").alias("event_time_unzoned"),
    strict_boolean(F.col("payload.Is_Plow_Status")).alias("plow_active"),
    strict_boolean(F.col("payload.Is_Spreader_Status")).alias("spreader_active"),
    strict_boolean(F.col("payload.Is_Engine_Status")).alias("engine_active"),
)

# COMMAND ----------
# Simple record-level quality checks (world-coordinate ranges only).
# Geofencing to Windsor's actual boundaries is NOT established here.
quality = typed.withColumn(
    "quality_issues",
    F.concat_ws(
        ";",
        F.when(F.col("vehicle_id").isNull() | (F.length("vehicle_id") == 0), "MISSING_VEHICLE_ID"),
        F.when(F.col("latitude").isNull() | ~F.col("latitude").between(-90, 90), "INVALID_LATITUDE"),
        F.when(F.col("longitude").isNull() | ~F.col("longitude").between(-180, 180), "INVALID_LONGITUDE"),
        F.when(F.col("event_time_unzoned").isNull(), "INVALID_TIMESTAMP"),
        F.when(F.col("plow_active").isNull(), "INVALID_PLOW_STATUS"),
        F.when(F.col("spreader_active").isNull(), "INVALID_SPREADER_STATUS"),
        F.when(F.col("engine_active").isNull(), "INVALID_ENGINE_STATUS"),
    ),
).withColumn(
    "quality_status",
    F.when(F.col("quality_issues") == "", "VALID").otherwise("INVALID")
)

# Retain INVALID records in Silver with explicit quality status, rather than
# silently filtering them out. Business metrics can choose VALID rows later.

# COMMAND ----------
# Inspect and assert the sample contract *before* writing.
summary = quality.agg(
    F.count("*").alias("distinct_records"),
    F.sum("occurrence_count").alias("source_observations"),
    F.countDistinct("vehicle_id").alias("vehicle_count"),
    F.sum(F.when(F.col("quality_status") == "INVALID", 1).otherwise(0)).alias("invalid_records"),
).first()

print("Silver preview summary:", summary.asDict())
assert summary["distinct_records"] == 12, "Expected 12 distinct JSON records in the synthetic fixture"
assert summary["source_observations"] == 13, "Expected 13 original observations, including repeat"
assert summary["vehicle_count"] == 3, "Expected three synthetic vehicles"
assert summary["invalid_records"] == 0, "Expected no malformed synthetic records"

# Full refresh is intentional only for a small, isolated synthetic demo table.
# In a real historical pipeline use incremental processing and explicit version selection.
(
    quality.write.format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(SILVER_TABLE)
)

print("Published demo Silver Delta table:", SILVER_TABLE)

# COMMAND ----------
# Query the materialized table: the rows survive notebook/session restarts.
silver = spark.table(SILVER_TABLE)
assert silver.count() == 12
assert silver.agg(F.sum("occurrence_count")).first()[0] == 13

silver.printSchema()
display(silver.select(
    "vehicle_id", "event_time_unzoned", "latitude", "longitude",
    "plow_active", "spreader_active", "engine_active",
    "occurrence_count", "quality_status", "quality_issues"
).orderBy("vehicle_id", "event_time_unzoned"))

print("PASS: 12 distinct records, 13 observations, 3 vehicles, 0 invalid sample records")
print("Next learning step: compare Bronze JSON versus Silver typed SQL columns.")
