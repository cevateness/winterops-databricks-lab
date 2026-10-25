-- WinterOps Lesson 2 — run after notebook 02; demo/synthetic data ONLY.
-- No timezone has been assigned to event_time_unzoned.

-- 1. Expected: distinct_records=12, source_observations=13,
--    vehicle_count=3, invalid_records=0.
SELECT
  COUNT(*) AS distinct_records,
  SUM(occurrence_count) AS source_observations,
  COUNT(DISTINCT vehicle_id) AS vehicle_count,
  SUM(CASE WHEN quality_status = 'INVALID' THEN 1 ELSE 0 END) AS invalid_records
FROM workspace.default.winterops_silver_demo_snowplow;

-- 2. Expected: three vehicles; SYN-001 = 5 raw observations / 4 unique,
--    SYN-002 = 4 / 4, SYN-003 = 4 / 4.
SELECT
  vehicle_id,
  COUNT(*) AS unique_record_count,
  SUM(occurrence_count) AS source_observations,
  MIN(event_time_unzoned) AS first_timestamp_unzoned,
  MAX(event_time_unzoned) AS last_timestamp_unzoned
FROM workspace.default.winterops_silver_demo_snowplow
GROUP BY vehicle_id
ORDER BY vehicle_id;

-- 3. Try typed arithmetic without JSON extraction. This is intentionally
--    not an operational coverage metric.
SELECT
  vehicle_id,
  ROUND(AVG(latitude), 6) AS mean_latitude,
  ROUND(AVG(longitude), 6) AS mean_longitude
FROM workspace.default.winterops_silver_demo_snowplow
WHERE quality_status = 'VALID'
GROUP BY vehicle_id
ORDER BY vehicle_id;

-- 4. Inspect the schema: latitude/longitude DOUBLE; Boolean flags BOOLEAN;
--    event_time_unzoned TIMESTAMP_NTZ (not automatically converted to UTC).
DESCRIBE TABLE workspace.default.winterops_silver_demo_snowplow;
