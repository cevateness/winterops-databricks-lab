# Databricks notebook source
# MAGIC %md
# MAGIC # WinterOps — Lesson 5: Real Windsor Bronze → Silver
# MAGIC
# MAGIC **Goal:** transform ONE validated Bronze file version into a typed, quality-classified
# MAGIC Delta Silver table. Preserve one row for each Bronze observation. Do **not** silently
# MAGIC delete repeated payloads or repeated CSV headers; classify them.
# MAGIC
# MAGIC **Prerequisites:** Lesson 4 completed and SQL check on this file reported
# MAGIC 110,337 Bronze observations, including 26 repeated header-like records.
# MAGIC
# MAGIC **Learning scope:** one-week Silver **snapshot**, intentionally rebuilt with a full
# MAGIC refresh for predictable notebook exercises. Do not use this overwrite pattern
# MAGIC unmodified for multi-week production ingestion.
# MAGIC
# MAGIC **Timestamp caveat:** `Date time` has no verified source timezone. Store it as
# MAGIC `TIMESTAMP_NTZ` (a wall-clock timestamp). Do **not** infer UTC or convert yet.

# COMMAND ----------
from pyspark.sql import functions as F

CATALOG = "workspace"
SCHEMA = "default"
VOLUME = "winterops_raw"
SOURCE_FILENAME = "snowplow-2026-01-12_2026-01-18.csv"
SOURCE_DATASET = "windsor_snowplow_activity"

# Leave None when only one version of this file path exists in Bronze.
# If multiple versions exist, set this explicitly to the SHA-256 of the desired file.
SOURCE_FILE_SHA256 = None

BRONZE_TABLE = f"{CATALOG}.{SCHEMA}.winterops_bronze_windsor_activity"
SILVER_TABLE = f"{CATALOG}.{SCHEMA}.winterops_silver_windsor_week_sample"
FILE_PATH = f"/Volumes/{CATALOG}/{SCHEMA}/{VOLUME}/{SOURCE_FILENAME}"

if not spark.catalog.tableExists(BRONZE_TABLE):
    raise RuntimeError(f"Missing Bronze table: {BRONZE_TABLE}. Run Lesson 4 first.")

# Require an unambiguous, exact source file version. Do not silently include both
# an older file and a later replacement at the same path.
bronze_scope = (
    (F.col("source_dataset") == SOURCE_DATASET)
    & (F.col("source_file_name") == SOURCE_FILENAME)
    & (F.col("source_file_path") == FILE_PATH)
)
scoped = spark.table(BRONZE_TABLE).filter(bronze_scope)
versions = [r[0] for r in scoped.select("source_file_sha256").distinct().collect()]
if not versions:
    raise ValueError(f"No Bronze rows found for {FILE_PATH}.")
if SOURCE_FILE_SHA256 is None:
    if len(versions) != 1:
        raise ValueError(
            f"Found {len(versions)} versions for {FILE_PATH}. Set SOURCE_FILE_SHA256 "
            "explicitly after reviewing the Bronze version inventory."
        )
    selected_sha = versions[0]
else:
    selected_sha = SOURCE_FILE_SHA256
    if selected_sha not in versions:
        raise ValueError("SOURCE_FILE_SHA256 is not among the ingested versions for this path.")

bronze = scoped.filter(F.col("source_file_sha256") == selected_sha)
bronze_count = bronze.count()
if bronze_count == 0:
    raise ValueError("Refusing to publish an empty Silver table.")
print("Selected Bronze version:", selected_sha)
print("Selected source observations:", f"{bronze_count:,}")

# COMMAND ----------
# The original CSV header names have spaces. Parse the JSON into a map so the
# *real* field names can be accessed safely, without using the synthetic schema.
parsed = bronze.withColumn(
    "payload", F.from_json(F.col("raw_record_json"), "MAP<STRING, STRING>")
)

def source_field(key):
    """Read a source JSON key, safely yielding NULL if that key is absent."""
    return F.try_element_at(F.col("payload"), F.lit(key))

def strict_boolean(column):
    """Interpret only observed True/False spellings, not unknown encodings."""
    normalized = F.upper(F.trim(column))
    return (
        F.when(normalized == "TRUE", F.lit(True))
         .when(normalized == "FALSE", F.lit(False))
         .otherwise(F.lit(None).cast("boolean"))
    )

# Keep source data separate from their typed interpretation.
fields = parsed.select(
    "source_dataset", "source_file_name", "source_file_path",
    "source_file_sha256", "record_sha256", "ingested_at_utc", "payload",
    F.trim(source_field("Truck")).alias("truck_id"),
    F.expr("try_cast(try_element_at(payload, 'Date time') AS TIMESTAMP_NTZ)")
        .alias("event_time_unzoned"),
    F.expr("try_cast(try_element_at(payload, 'Latitude') AS DOUBLE)")
        .alias("latitude"),
    F.expr("try_cast(try_element_at(payload, 'Longitude') AS DOUBLE)")
        .alias("longitude"),
    strict_boolean(source_field("Plow status")).alias("plow_active"),
    strict_boolean(source_field("Spreader status")).alias("spreader_active"),
    strict_boolean(source_field("Engine status")).alias("engine_active"),
)

# A recognizable repeated CSV header INSIDE the source file (not JSON field keys).
# This exactly follows the evidence from Lesson 4's SQL profiling.
def matches_header(key):
    text_value = F.upper(F.trim(F.try_element_at(F.col("payload"), F.lit(key))))
    return F.coalesce(text_value == F.lit(key.upper()), F.lit(False))

header_signature = (
    matches_header("Latitude")
    & matches_header("Longitude")
    & matches_header("Date time")
    & matches_header("Truck")
)
fields = fields.withColumn("is_repeated_header", header_signature)

# COMMAND ----------
# Keep exact, identical GPS payloads visible. We cannot distinguish a source
# retransmission from a legitimate repeated measurement without more evidence.
frequency = (
    bronze.groupBy("record_sha256")
    .agg(F.count("*").cast("long").alias("payload_occurrences"))
)
with_frequency = (
    fields.join(frequency, on="record_sha256", how="left")
    .withColumn("has_repeated_payload", F.col("payload_occurrences") > 1)
)

# Record-level quality checks. The coordinate checks are only WORLD bounds, not
# an actual Windsor city/service-area geofence. Do not flag a repeated payload as
# invalid by default. Header-like records get one clear classification.
issues = F.concat_ws(
    ";",
    F.when(F.col("payload").isNull(), "INVALID_JSON"),
    F.when(F.col("truck_id").isNull() | (F.col("truck_id") == ""), "MISSING_TRUCK"),
    F.when(
        F.col("latitude").isNull() | ~F.col("latitude").between(-90, 90),
        "INVALID_LATITUDE",
    ),
    F.when(
        F.col("longitude").isNull() | ~F.col("longitude").between(-180, 180),
        "INVALID_LONGITUDE",
    ),
    F.when(F.col("event_time_unzoned").isNull(), "INVALID_TIMESTAMP"),
    F.when(F.col("plow_active").isNull(), "INVALID_PLOW_STATUS"),
    F.when(F.col("spreader_active").isNull(), "INVALID_SPREADER_STATUS"),
    F.when(F.col("engine_active").isNull(), "INVALID_ENGINE_STATUS"),
)

silver = (
    with_frequency
    .withColumn(
        "quality_issues",
        F.when(F.col("is_repeated_header"), F.lit("REPEATED_HEADER"))
         .otherwise(issues),
    )
    .withColumn(
        "quality_status",
        F.when(F.col("is_repeated_header"), F.lit("HEADER"))
         .when(F.col("quality_issues") != "", F.lit("INVALID"))
         .otherwise(F.lit("VALID")),
    )
    .select(
        "source_dataset", "source_file_name", "source_file_path",
        "source_file_sha256", "record_sha256", "ingested_at_utc",
        "truck_id", "event_time_unzoned", "latitude", "longitude",
        "plow_active", "spreader_active", "engine_active",
        "payload_occurrences", "has_repeated_payload", "is_repeated_header",
        "quality_status", "quality_issues",
    )
)

# COMMAND ----------
# Data quality is measurable: preserve every Bronze observation, including
# invalid/header rows, as a classified Silver row in this lesson.
preview = silver.groupBy("quality_status").count()
print("Quality classification BEFORE publishing:")
display(preview.orderBy("quality_status"))

silver_count = silver.count()
assert silver_count == bronze_count, (
    f"Row preservation failed: {bronze_count} Bronze vs {silver_count} Silver"
)

# The following table is reserved for the single-week learning snapshot.
# Avoid silently overwriting a Silver sample from an entirely different week.
if spark.catalog.tableExists(SILVER_TABLE):
    existing_paths = [r[0] for r in
                      spark.table(SILVER_TABLE).select("source_file_path").distinct().collect()]
    if any(p != FILE_PATH for p in existing_paths):
        raise RuntimeError(
            f"{SILVER_TABLE} contains another source file. "
            "Use a separate table or a proper multi-week incremental pipeline."
        )

(
    silver.write.format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(SILVER_TABLE)
)

# COMMAND ----------
# Compare a fresh persisted read with the selected Bronze file version.
persisted = spark.table(SILVER_TABLE)
assert persisted.count() == bronze_count
assert persisted.filter(F.col("source_file_sha256") != selected_sha).count() == 0
assert persisted.filter(F.col("quality_status").isNull()).count() == 0

summary = persisted.agg(
    F.count("*").alias("total_rows"),
    F.sum(F.when(F.col("quality_status") == "HEADER", 1).otherwise(0))
      .alias("header_rows"),
    F.sum(F.when(F.col("quality_status") == "VALID", 1).otherwise(0))
      .alias("valid_rows"),
    F.sum(F.when(F.col("quality_status") == "INVALID", 1).otherwise(0))
      .alias("other_invalid_rows"),
    F.sum(F.when(
        (F.col("quality_status") != "HEADER") & F.col("has_repeated_payload"), 1
    ).otherwise(0)).alias("nonheader_rows_with_repeated_payload"),
    F.countDistinct(F.when(F.col("quality_status") == "VALID", F.col("truck_id")))
      .alias("valid_trucks"),
).first().asDict()

print("Silver table:", SILVER_TABLE)
print("Quality summary:", summary)
assert summary["total_rows"] == (
    summary["header_rows"] + summary["valid_rows"]
    + summary["other_invalid_rows"]
)
print("PASS: Silver materialized without losing Bronze observations.")
print("Review the SQL quality checks before building Gold analytics.")

# MAGIC %md
# MAGIC ## What this exercise does **not** establish
# MAGIC - `VALID` means the explicitly implemented field checks passed, not that the
# MAGIC   observation was verified against a road network or Windsor boundary.
# MAGIC - Repeated payloads are warnings, not automatically false observations.
# MAGIC - Original CSV line ordering is not recoverable from this Bronze schema.
# MAGIC - We have not independently verified the source timestamp timezone.
# MAGIC - The source may contain a mixture of operational and non-operational statuses.
# MAGIC - Rerunning this notebook rewrites the ONE-WEEK Silver snapshot, creating a new
# MAGIC   Delta version even if its logical contents do not change. This is not an
# MAGIC   optimized incremental production Silver pipeline.
