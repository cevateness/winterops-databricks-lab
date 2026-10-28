_valid_rows AS (
  SELECT truck_id, event_time_unzoned, record_sha256, plow_active, spreader_active,
         engine_active, payload_occurrences, has_repeated_payload
  FROM $valid_table
  WHERE $valid_filter AND quality_status = 'VALID'
    AND event_time_unzoned >= TIMESTAMP_NTZ '$start'
    AND event_time_unzoned < TIMESTAMP_NTZ '$end'
), _valid AS (
  SELECT *, CAST(event_time_unzoned AS DATE) AS source_local_naive_day,
         CAST(substring(CAST(event_time_unzoned AS STRING), 1, 13) || ':00:00' AS TIMESTAMP_NTZ)
           AS source_local_naive_hour,
         $clock_index AS source_clock_index_microseconds
  FROM _valid_rows
), _gold AS (
  SELECT source_local_naive_hour, observation_count, plow_active_observation_count,
         spreader_active_observation_count, distinct_truck_count, repeated_payload_observation_count
  FROM $gold_table
  WHERE $gold_filter AND source_local_naive_hour >= TIMESTAMP_NTZ '$start'
    AND source_local_naive_hour < TIMESTAMP_NTZ '$end'
)
