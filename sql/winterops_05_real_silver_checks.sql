-- WinterOps Lesson 5 — SQL checks for the real Windsor single-week Silver snapshot.
-- Run after 05_silver_real_windsor.py. These queries do NOT modify data.

-- 1. Quality report: HEADER records remain visible, not counted as valid activity.
SELECT quality_status, quality_issues, COUNT(*) AS observations
FROM workspace.default.winterops_silver_windsor_week_sample
GROUP BY quality_status, quality_issues
ORDER BY observations DESC;

-- 2. Reconcile record counts between the exact file version in Bronze and Silver.
WITH silver_version AS (
  SELECT DISTINCT source_file_path, source_file_sha256
  FROM workspace.default.winterops_silver_windsor_week_sample
),
bronze_counts AS (
  SELECT COUNT(*) AS bronze_rows
  FROM workspace.default.winterops_bronze_windsor_activity b
  INNER JOIN silver_version v
    ON b.source_file_path = v.source_file_path
   AND b.source_file_sha256 = v.source_file_sha256
)
SELECT b.bronze_rows,
       COUNT(*) AS silver_rows,
       COUNT_IF(s.quality_status = 'HEADER') AS header_rows,
       COUNT_IF(s.quality_status = 'VALID') AS valid_rows,
       COUNT_IF(s.quality_status = 'INVALID') AS other_invalid_rows
FROM workspace.default.winterops_silver_windsor_week_sample s
CROSS JOIN bronze_counts b
GROUP BY b.bronze_rows;

-- 3. Potential repetitions among non-header observations, without deleting them.
SELECT record_sha256, COUNT(*) AS occurrences,
       MIN(truck_id) AS truck_id,
       MIN(event_time_unzoned) AS earliest_unzoned_time
FROM workspace.default.winterops_silver_windsor_week_sample
WHERE quality_status <> 'HEADER'
GROUP BY record_sha256
HAVING COUNT(*) > 1
ORDER BY occurrences DESC
LIMIT 25;

-- 4. Type inspection and basic activity summary: valid rows only.
SELECT COUNT(*) AS valid_observations,
       COUNT(DISTINCT truck_id) AS truck_count,
       MIN(event_time_unzoned) AS earliest_unzoned_time,
       MAX(event_time_unzoned) AS latest_unzoned_time,
       MIN(latitude) AS min_latitude, MAX(latitude) AS max_latitude,
       MIN(longitude) AS min_longitude, MAX(longitude) AS max_longitude,
       COUNT_IF(plow_active) AS plow_active_observations,
       COUNT_IF(spreader_active) AS spreader_active_observations
FROM workspace.default.winterops_silver_windsor_week_sample
WHERE quality_status = 'VALID';

-- 5. Inspect the 26 repeated headers and their classification (expected from prior profiling).
SELECT source_file_name, quality_status, quality_issues, COUNT(*) AS n
FROM workspace.default.winterops_silver_windsor_week_sample
WHERE is_repeated_header
GROUP BY source_file_name, quality_status, quality_issues;

-- 6. Verify typed table structure.
DESCRIBE TABLE workspace.default.winterops_silver_windsor_week_sample;
