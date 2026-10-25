-- WinterOps Lesson 4 — Run these in the Databricks SQL editor.
-- Real Windsor source ONLY; does not touch synthetic tables.

-- 1. Which source files and versions were ingested?
SELECT source_dataset, source_file_name, source_file_sha256,
       COUNT(*) AS observations, COUNT(DISTINCT record_sha256) AS distinct_payloads
FROM workspace.default.winterops_bronze_windsor_activity
GROUP BY source_dataset, source_file_name, source_file_sha256
ORDER BY source_file_name, source_file_sha256;

-- 2. Show identical observations retained as separate Bronze records.
SELECT source_file_name, source_file_sha256, record_sha256,
       COUNT(*) AS occurrences
FROM workspace.default.winterops_bronze_windsor_activity
GROUP BY source_file_name, source_file_sha256, record_sha256
HAVING COUNT(*) > 1
ORDER BY occurrences DESC
LIMIT 10;

-- 3. Examine two source JSON records and their provenance.
SELECT source_file_name, raw_record_json, record_sha256, ingested_at_utc
FROM workspace.default.winterops_bronze_windsor_activity
LIMIT 2;

-- 4. A useful schema check; no source-specific column names assumed.
DESCRIBE TABLE workspace.default.winterops_bronze_windsor_activity;
