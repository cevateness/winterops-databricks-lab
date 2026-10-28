_identifier_counts AS (
  SELECT truck_id, COUNT(*) AS observation_count,
         COUNT(DISTINCT source_local_naive_day) AS reporting_days,
         COUNT(DISTINCT event_time_unzoned) AS distinct_timestamps
  FROM _valid GROUP BY truck_id
), _payloads AS (
  SELECT record_sha256, COUNT(*) AS n, COUNT(DISTINCT truck_id) AS identifier_count,
         COUNT(DISTINCT event_time_unzoned) AS timestamp_count
  FROM _valid GROUP BY record_sha256
), _timestamp_sets AS (
  SELECT truck_id, event_time_unzoned, COUNT(DISTINCT record_sha256) AS payload_count
  FROM _valid GROUP BY truck_id, event_time_unzoned
), _conflicts AS (
  SELECT truck_id, COUNT(*) AS conflict_timestamps FROM _timestamp_sets
  WHERE payload_count > 1 GROUP BY truck_id
), _identifier_hours AS (
  SELECT truck_id, source_local_naive_hour, COUNT(*) AS n
  FROM _valid GROUP BY truck_id, source_local_naive_hour
), _density AS (
  SELECT truck_id, COUNT_IF(n > $dense_hour_observations) AS dense_hours,
         MAX(n) AS peak_hour_observations FROM _identifier_hours GROUP BY truck_id
), _ordered AS (
  SELECT truck_id, source_clock_index_microseconds,
         LAG(source_clock_index_microseconds) OVER (
           PARTITION BY truck_id ORDER BY event_time_unzoned, record_sha256
         ) AS previous_clock_index_microseconds
  FROM _valid
), _gaps AS (
  SELECT truck_id,
         (source_clock_index_microseconds - previous_clock_index_microseconds) / 1000000.0
           AS source_clock_gap_seconds
  FROM _ordered WHERE previous_clock_index_microseconds IS NOT NULL
), _gap_metrics AS (
  SELECT truck_id, COUNT(*) AS gap_pairs,
         COUNT_IF(source_clock_gap_seconds = 0) AS zero_gap_pairs,
         COUNT_IF(source_clock_gap_seconds > $long_gap_seconds) AS long_gap_pairs,
         MIN(CASE WHEN source_clock_gap_seconds > 0 THEN source_clock_gap_seconds END)
           AS minimum_positive_gap_seconds,
         MAX(source_clock_gap_seconds) AS maximum_gap_seconds
  FROM _gaps GROUP BY truck_id
), _identifiers AS (
  SELECT i.*, COALESCE(c.conflict_timestamps, 0) AS conflict_timestamps,
         d.dense_hours, d.peak_hour_observations,
         COALESCE(g.gap_pairs, 0) AS gap_pairs, COALESCE(g.zero_gap_pairs, 0) AS zero_gap_pairs,
         COALESCE(g.long_gap_pairs, 0) AS long_gap_pairs,
         g.minimum_positive_gap_seconds, g.maximum_gap_seconds
  FROM _identifier_counts i LEFT JOIN _conflicts c ON i.truck_id = c.truck_id
  LEFT JOIN _density d ON i.truck_id = d.truck_id
  LEFT JOIN _gap_metrics g ON i.truck_id = g.truck_id
)
