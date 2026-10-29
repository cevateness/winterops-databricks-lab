-- Examples for the NEW views, after separately approved publication only.
-- Sparse activity-triggered observations; missing buckets do not mean inactivity.

-- 1. Three-week comparison: grouped bars; plow/spreader flags overlap.
SELECT source_week_start, source_version_id, processing_key, quality_policy_sha256,
       observation_count, plow_active_observations, spreader_active_observations,
       observed_identifier_count, hours_containing_telemetry
FROM workspace.default.winterops_v2_gold_weekly_quality
ORDER BY source_week_start;

-- 2. Hourly trend: one selected week per bounded result (at most 168 hours).
SELECT source_week_start, source_version_id, processing_key, quality_policy_sha256,
       source_local_naive_hour, observation_count,
       plow_active_observations, spreader_active_observations, observed_identifier_count
FROM workspace.default.winterops_v2_gold_hourly_observations
WHERE processing_key = '5e478fdced5a0ac67865413d68b9359a97fffd980a2a6dee976d6ab984c599be'
ORDER BY source_local_naive_hour
LIMIT 168;

-- 3. Equipment composition: stack these FOUR exclusive categories only.
SELECT source_week_start, source_version_id, processing_key, quality_policy_sha256,
       source_local_naive_day, plow_only_observations, spreader_only_observations,
       both_active_observations, neither_active_observations,
       engine_off_with_equipment_flag_observations
FROM workspace.default.winterops_v2_gold_daily_activity
ORDER BY source_week_start, source_local_naive_day;

-- 4. Quality diagnostics: warnings/repeats/gaps are separate, overlapping panels.
SELECT source_week_start, source_version_id, processing_key, quality_policy_sha256,
       bronze_rows, silver_rows, header_rows, valid_rows, invalid_rows,
       invalid_coordinate_rows, outside_review_envelope_rows,
       repeated_valid_payload_observations, excess_valid_payload_observations,
       zero_gap_pairs, long_gap_pairs
FROM workspace.default.winterops_v2_gold_weekly_quality
ORDER BY source_week_start;

-- Never sum observed_identifier_count across hours/days to estimate fleet size.
-- Counts/gaps are not working hours, availability, coverage or productivity.
