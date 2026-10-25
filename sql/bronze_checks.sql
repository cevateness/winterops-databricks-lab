-- WinterOps Bronze QA. These queries do not imply a typed Silver schema.
-- Table name assumes the default setup in notebooks/01_bronze_ingestion.py.

-- 1. Files / file versions, total source rows, and duplicate multiplicity.
SELECT
  source_dataset,
  source_file_name,
  source_file_sha256,
  COUNT(*) AS distinct_parsed_records,
  SUM(occurrence_count) AS original_row_occurrences,
  SUM(occurrence_count - 1) AS repeated_record_occurrences
FROM workspace.default.winterops_bronze_snowplow
GROUP BY source_dataset, source_file_name, source_file_sha256
ORDER BY source_file_name, source_file_sha256;

-- 2. Idempotency key should be unique within a given file-version/path.
SELECT
  source_file_path,
  source_file_sha256,
  record_sha256,
  COUNT(*) AS duplicate_key_count
FROM workspace.default.winterops_bronze_snowplow
GROUP BY source_file_path, source_file_sha256, record_sha256
HAVING COUNT(*) > 1;

-- 3. Inspect without assuming source-specific business column names.
SELECT source_dataset, source_file_name, raw_record_json, occurrence_count
FROM workspace.default.winterops_bronze_snowplow
LIMIT 20;
