CREATE OR REPLACE VIEW $hourly_table
COMMENT 'Source-local/naive hourly observation counts; not time worked, coverage or productivity'
AS WITH bucketed AS (
  SELECT source_dataset, source_file_name, source_file_sha256,
         -- Truncate the NTZ wall-clock representation without converting to an instant.
         CAST(substring(CAST(event_time_unzoned AS STRING), 1, 13) || ':00:00' AS TIMESTAMP_NTZ)
           AS source_local_naive_hour,
         truck_id, plow_active, spreader_active, has_repeated_payload
  FROM $valid_table
)
SELECT source_dataset, source_file_name, source_file_sha256, source_local_naive_hour,
       COUNT(*) AS observation_count,
       COUNT_IF(plow_active) AS plow_active_observation_count,
       COUNT_IF(spreader_active) AS spreader_active_observation_count,
       COUNT(DISTINCT truck_id) AS distinct_truck_count,
       COUNT_IF(has_repeated_payload) AS repeated_payload_observation_count
FROM bucketed
GROUP BY source_dataset, source_file_name, source_file_sha256, source_local_naive_hour
