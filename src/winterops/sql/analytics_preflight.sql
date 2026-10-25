-- Expected counts are supplied for this exact source, never global thresholds.
WITH selected AS (
  SELECT * FROM $silver_table WHERE $source_filter
), summary AS (
  SELECT COUNT(*) AS silver_rows,
         COUNT_IF(quality_status = 'HEADER') AS header_rows,
         COUNT_IF(quality_status = 'VALID') AS valid_rows,
         COUNT_IF(quality_status = 'INVALID') AS invalid_rows,
         COUNT_IF(quality_status IS NULL OR quality_status NOT IN ('VALID', 'HEADER', 'INVALID')) AS unknown_rows,
         COUNT_IF(record_sha256 IS NULL OR NOT (record_sha256 RLIKE '^[0-9a-f]{64}$$')) AS bad_hash_rows,
         COUNT_IF(payload_occurrences IS NULL OR payload_occurrences < 1
                  OR has_repeated_payload IS NULL
                  OR has_repeated_payload <> (payload_occurrences > 1)) AS bad_frequency_rows,
         COUNT_IF(quality_status = 'VALID' AND (
           event_time_unzoned IS NULL OR NOT ($window_filter)
           OR truck_id IS NULL OR trim(truck_id) = ''
           OR latitude IS NULL OR NOT (latitude BETWEEN -90 AND 90)
           OR longitude IS NULL OR NOT (longitude BETWEEN -180 AND 180)
           OR plow_active IS NULL OR spreader_active IS NULL OR engine_active IS NULL
           OR is_repeated_header IS NULL OR is_repeated_header
           OR quality_issues IS NULL OR quality_issues <> ''
         )) AS bad_valid_rows,
         COUNT_IF(quality_status = 'HEADER' AND (
           is_repeated_header IS NULL OR NOT is_repeated_header
           OR quality_issues IS NULL OR quality_issues <> 'REPEATED_HEADER'
         )) AS bad_header_rows,
         COUNT_IF(quality_status = 'INVALID' AND (
           is_repeated_header IS NULL OR is_repeated_header
           OR quality_issues IS NULL OR quality_issues = ''
         )) AS bad_invalid_rows,
         COUNT(DISTINCT CASE WHEN quality_status = 'VALID' THEN truck_id END) AS valid_trucks,
         COUNT_IF(quality_status = 'VALID' AND plow_active) AS plow_rows,
         COUNT_IF(quality_status = 'VALID' AND spreader_active) AS spreader_rows
  FROM selected
), bronze AS (
  SELECT COUNT(*) AS bronze_rows FROM $bronze_table WHERE $source_filter
), whole_silver AS (
  SELECT COUNT(*) AS all_rows FROM $silver_table
)
SELECT assert_true(b.bronze_rows = $bronze_rows, 'Unexpected selected Bronze count') AS bronze_check,
       assert_true(s.silver_rows = b.bronze_rows AND s.silver_rows = $silver_rows,
                   'Selected Bronze/Silver counts disagree') AS preservation_check,
       assert_true(w.all_rows = s.silver_rows,
                   'Single-week Silver contains another file/path/version') AS version_check,
       assert_true(s.header_rows = $header_rows AND s.valid_rows = $valid_rows
                   AND s.invalid_rows = $other_invalid_rows AND s.unknown_rows = 0,
                   'Silver classifications disagree with approved evidence') AS quality_check,
       assert_true(s.bad_hash_rows = 0 AND s.bad_frequency_rows = 0
                   AND s.bad_valid_rows = 0 AND s.bad_header_rows = 0 AND s.bad_invalid_rows = 0,
                   'Silver fields/window/classification contract failed') AS domain_check,
       assert_true(s.valid_trucks = $distinct_truck_ids AND s.plow_rows = $plow_active_observations
                   AND s.spreader_rows = $spreader_active_observations,
                   'Valid activity summary disagrees with approved evidence') AS evidence_check
FROM summary s CROSS JOIN bronze b CROSS JOIN whole_silver w
