_silver_hours AS (
  SELECT source_local_naive_hour, COUNT(*) AS n,
         COUNT_IF(plow_active) AS plow_n, COUNT_IF(spreader_active) AS spreader_n,
         COUNT(DISTINCT truck_id) AS trucks, COUNT_IF(has_repeated_payload) AS repeats
  FROM _valid GROUP BY source_local_naive_hour
), _hour_mismatches AS (
  SELECT COUNT(*) AS n FROM _silver_hours s FULL OUTER JOIN _gold g
  ON s.source_local_naive_hour = g.source_local_naive_hour
  WHERE s.source_local_naive_hour IS NULL OR g.source_local_naive_hour IS NULL
     OR s.n <> g.observation_count OR s.plow_n <> g.plow_active_observation_count
     OR s.spreader_n <> g.spreader_active_observation_count OR s.trucks <> g.distinct_truck_count
     OR s.repeats <> g.repeated_payload_observation_count
), _payload_frequency_mismatches AS (
  SELECT COUNT(*) AS n FROM (
    SELECT record_sha256, COUNT(*) AS n, MIN(payload_occurrences) AS low,
           MAX(payload_occurrences) AS high FROM _valid GROUP BY record_sha256
  ) p WHERE p.n <> p.low OR p.n <> p.high
), _source_summary AS (
  SELECT COUNT(*) AS n, COUNT(DISTINCT truck_id) AS trucks,
         COUNT_IF(plow_active) AS plow_n, COUNT_IF(spreader_active) AS spreader_n,
         COUNT_IF(truck_id IS NULL OR trim(truck_id) = '' OR record_sha256 IS NULL
           OR NOT (record_sha256 RLIKE '^[0-9a-f]{64}$$') OR plow_active IS NULL
           OR spreader_active IS NULL OR engine_active IS NULL OR has_repeated_payload IS NULL
           OR payload_occurrences IS NULL OR payload_occurrences < 1
           OR has_repeated_payload <> (payload_occurrences > 1)) AS bad_rows
  FROM _valid
), _gold_summary AS (
  SELECT COUNT(*) AS hours, COUNT(DISTINCT source_local_naive_hour) AS unique_hours,
         COALESCE(SUM(observation_count), 0) AS n,
         COUNT_IF(observation_count IS NULL OR observation_count < 1
           OR plow_active_observation_count IS NULL OR plow_active_observation_count < 0
           OR spreader_active_observation_count IS NULL OR spreader_active_observation_count < 0
           OR repeated_payload_observation_count IS NULL OR repeated_payload_observation_count < 0
           OR distinct_truck_count IS NULL OR distinct_truck_count < 1
           OR distinct_truck_count > observation_count
           OR plow_active_observation_count > observation_count
           OR spreader_active_observation_count > observation_count
           OR repeated_payload_observation_count > observation_count) AS bad_rows
  FROM _gold
)
SELECT assert_true(s.n = $valid_rows AND s.trucks = $valid_trucks
         AND s.plow_n = $plow_rows AND s.spreader_n = $spreader_rows AND s.bad_rows = 0
         AND s.n = (SELECT COUNT(*) FROM $valid_table)
         AND (SELECT n FROM _payload_frequency_mismatches) = 0
         AND g.n = s.n AND g.bad_rows = 0 AND g.hours = g.unique_hours
         AND g.hours BETWEEN 1 AND 168 AND g.hours = (SELECT COUNT(*) FROM $gold_table),
         'Published source version, fields or approved evidence do not match') AS source_version_check,
       assert_true(m.n = 0, 'Published Gold does not match Silver per hour') AS gold_hourly_check
FROM _source_summary s CROSS JOIN _gold_summary g CROSS JOIN _hour_mismatches m
