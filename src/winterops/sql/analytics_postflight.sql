WITH valid AS (
  SELECT COUNT(*) AS n, COUNT_IF(plow_active) AS plow_rows,
         COUNT_IF(spreader_active) AS spreader_rows,
         COUNT_IF(has_repeated_payload) AS repeated_rows FROM $valid_table
), quarantine AS (
  SELECT COUNT(*) AS n FROM $quarantine_table
), hourly AS (
  SELECT COUNT(*) AS buckets, COALESCE(SUM(observation_count), 0) AS n,
         COALESCE(SUM(plow_active_observation_count), 0) AS plow_rows,
         COALESCE(SUM(spreader_active_observation_count), 0) AS spreader_rows,
         COALESCE(SUM(repeated_payload_observation_count), 0) AS repeated_rows,
         COUNT_IF(distinct_truck_count < 1 OR distinct_truck_count > observation_count
                   OR repeated_payload_observation_count > observation_count) AS bad_buckets
  FROM $hourly_table
)
SELECT assert_true(v.n = $valid_rows AND q.n = $header_rows + $other_invalid_rows
                   AND v.n + q.n = $silver_rows,
                   'Silver consumer views do not reconcile') AS consumer_check,
       assert_true(h.n = v.n AND h.plow_rows = v.plow_rows AND h.spreader_rows = v.spreader_rows
                   AND h.repeated_rows = v.repeated_rows AND h.bad_buckets = 0
                   AND h.buckets BETWEEN 1 AND 168,
                   'Hourly observations/status/repetition counts do not reconcile') AS hourly_check
FROM valid v CROSS JOIN quarantine q CROSS JOIN hourly h
