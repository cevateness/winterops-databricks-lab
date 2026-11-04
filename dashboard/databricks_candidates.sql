-- READ-ONLY CANDIDATE: weekly
WITH _wanted AS (SELECT 'windsor_snowplow_activity' AS source_dataset, 'snowplow-2026-01-05_2026-01-11.csv' AS source_file_name, '271c9339a42043f441b6c17e82dd309609db4b20e9953b9f368a95ec472d763d' AS source_file_sha256, '8ccb2a2dd5ec057361cf6d7cc7193b5acbdd858b84102ba550a92febe9bb4ed1' AS source_version_id, 'f07ba6a0ad499a9baf53d2f7c46df09607523371428791593143a29b56f6b466' AS processing_key, 'windsor-foundation-v2.1' AS pipeline_version, '03829a2ce3b308a45e0205ca12a5288e5cb08b97189cf20b69c0e37d4c546e08' AS quality_policy_sha256, DATE '2026-01-05' AS source_week_start, DATE '2026-01-12' AS source_week_end_exclusive, '/Volumes/workspace/default/winterops_raw/original_csv/snowplow-2026-01-05_2026-01-11.csv/271c9339a42043f441b6c17e82dd309609db4b20e9953b9f368a95ec472d763d/snowplow-2026-01-05_2026-01-11.csv' AS original_csv_volume_path, 2810 AS expected_rows, 1800 AS long_gap_seconds, '{"review_lat_min": 42.1, "review_lat_max": 42.5, "review_lon_min": -83.3, "review_lon_max": -82.6, "nominal_interval_seconds": 15, "long_gap_seconds": 1800, "dense_hour_observations": 1000}' AS policy_json
UNION ALL
SELECT 'windsor_snowplow_activity' AS source_dataset, 'snowplow-2026-01-12_2026-01-18.csv' AS source_file_name, 'f5d7633c910e1ad6be23b4111445bf0bc14fe2071c6ea0f0d4cd456295ea9e94' AS source_file_sha256, '73e9338d8a7e78ba01827806b2172a715a50b90c819959ba1ade17632f2d4433' AS source_version_id, '5e478fdced5a0ac67865413d68b9359a97fffd980a2a6dee976d6ab984c599be' AS processing_key, 'windsor-foundation-v2.1' AS pipeline_version, '03829a2ce3b308a45e0205ca12a5288e5cb08b97189cf20b69c0e37d4c546e08' AS quality_policy_sha256, DATE '2026-01-12' AS source_week_start, DATE '2026-01-19' AS source_week_end_exclusive, '/Volumes/workspace/default/winterops_raw/snowplow-2026-01-12_2026-01-18.csv' AS original_csv_volume_path, 110337 AS expected_rows, 1800 AS long_gap_seconds, '{"review_lat_min": 42.1, "review_lat_max": 42.5, "review_lon_min": -83.3, "review_lon_max": -82.6, "nominal_interval_seconds": 15, "long_gap_seconds": 1800, "dense_hour_observations": 1000}' AS policy_json
UNION ALL
SELECT 'windsor_snowplow_activity' AS source_dataset, 'snowplow-2026-01-19_2026-01-25.csv' AS source_file_name, 'b78d0fb82c8e3c5204ee79eea7a03417cd54bc935ead9b04577a30dc908c7c49' AS source_file_sha256, 'd2a89e9a8582aefdca97264a482d51a6116b827a71f0241a0e1f0149ed14f97a' AS source_version_id, 'bb478f6992172da1298db36c3a5d92aa4c349769064ec66002f347a2458e415c' AS processing_key, 'windsor-foundation-v2.1' AS pipeline_version, '03829a2ce3b308a45e0205ca12a5288e5cb08b97189cf20b69c0e37d4c546e08' AS quality_policy_sha256, DATE '2026-01-19' AS source_week_start, DATE '2026-01-26' AS source_week_end_exclusive, '/Volumes/workspace/default/winterops_raw/original_csv/snowplow-2026-01-19_2026-01-25.csv/b78d0fb82c8e3c5204ee79eea7a03417cd54bc935ead9b04577a30dc908c7c49/snowplow-2026-01-19_2026-01-25.csv' AS original_csv_volume_path, 118159 AS expected_rows, 1800 AS long_gap_seconds, '{"review_lat_min": 42.1, "review_lat_max": 42.5, "review_lon_min": -83.3, "review_lon_max": -82.6, "nominal_interval_seconds": 15, "long_gap_seconds": 1800, "dense_hour_observations": 1000}' AS policy_json
UNION ALL
SELECT 'windsor_snowplow_activity' AS source_dataset, 'snowplow-2026-01-26_2026-02-01.csv' AS source_file_name, 'cebcbd758e2a0cf5d0624ecf9cd6993244e7becdd1846a4057b4f63be22ed6c6' AS source_file_sha256, 'ad5c201ccee0b96b2f4907f10ee3a064a7562d17429146d2205b1eaca46fdc00' AS source_version_id, '9c8e1b6f640e75c21f1c9f429ec670c389bf178269afd2f1543b2ae759c3eeae' AS processing_key, 'windsor-foundation-v2.1' AS pipeline_version, '03829a2ce3b308a45e0205ca12a5288e5cb08b97189cf20b69c0e37d4c546e08' AS quality_policy_sha256, DATE '2026-01-26' AS source_week_start, DATE '2026-02-02' AS source_week_end_exclusive, '/Volumes/workspace/default/winterops_raw/original_csv/snowplow-2026-01-26_2026-02-01.csv/cebcbd758e2a0cf5d0624ecf9cd6993244e7becdd1846a4057b4f63be22ed6c6/snowplow-2026-01-26_2026-02-01.csv' AS original_csv_volume_path, 66850 AS expected_rows, 1800 AS long_gap_seconds, '{"review_lat_min": 42.1, "review_lat_max": 42.5, "review_lon_min": -83.3, "review_lon_max": -82.6, "nominal_interval_seconds": 15, "long_gap_seconds": 1800, "dense_hour_observations": 1000}' AS policy_json),
_manifest_check AS (
 SELECT w.processing_key, COUNT(m.processing_key) AS n,
 SUM(CASE WHEN m.status='COMPLETE' AND m.last_successful_stage='COMPLETE' AND m.error_code IS NULL
  AND m.source_version_id=w.source_version_id AND m.source_file_name=w.source_file_name
  AND m.source_file_sha256=w.source_file_sha256 AND m.policy_json=w.policy_json
  AND m.bronze_rows=w.expected_rows AND m.silver_rows=w.expected_rows THEN 1 ELSE 0 END) AS good
 FROM _wanted w LEFT JOIN workspace.default.winterops_v2_dev_manifest m ON m.processing_key=w.processing_key GROUP BY w.processing_key),
_bronze_check AS (
 SELECT w.processing_key, COUNT(b.source_record_number) AS n, COUNT(DISTINCT b.source_record_number) AS unique_n,
 MIN(b.source_record_number) AS first_n, MAX(b.source_record_number) AS last_n,
 SUM(CASE WHEN COALESCE(b.source_dataset = w.source_dataset,FALSE) AND COALESCE(b.source_file_name = w.source_file_name,FALSE) AND COALESCE(b.source_file_sha256 = w.source_file_sha256,FALSE) AND COALESCE(b.source_week_start = w.source_week_start,FALSE) AND COALESCE(b.source_week_end_exclusive = w.source_week_end_exclusive,FALSE) AND b.source_version_id IS NOT NULL AND b.source_dataset IS NOT NULL AND b.source_file_name IS NOT NULL AND b.source_url IS NOT NULL AND b.source_file_path IS NOT NULL AND b.source_file_sha256 IS NOT NULL AND b.source_week_start IS NOT NULL AND b.source_week_end_exclusive IS NOT NULL AND b.retrieved_at_utc IS NOT NULL AND b.ingested_at_utc IS NOT NULL AND b.source_record_number IS NOT NULL AND b.source_line_end IS NOT NULL AND b.csv_parse_issues IS NOT NULL AND b.raw_values_json IS NOT NULL AND b.raw_record_json IS NOT NULL AND b.record_sha256 IS NOT NULL THEN 0 ELSE 1 END) AS bad
 FROM _wanted w LEFT JOIN workspace.default.winterops_v2_dev_bronze b ON b.source_version_id=w.source_version_id GROUP BY w.processing_key),
_silver_check AS (
 SELECT w.processing_key, COUNT(s.source_record_number) AS n, COUNT(DISTINCT s.source_record_number) AS unique_n,
 MIN(s.source_record_number) AS first_n, MAX(s.source_record_number) AS last_n,
 SUM(CASE WHEN COALESCE(s.source_version_id = w.source_version_id,FALSE) AND COALESCE(s.source_dataset = w.source_dataset,FALSE) AND COALESCE(s.source_file_name = w.source_file_name,FALSE) AND COALESCE(s.source_file_sha256 = w.source_file_sha256,FALSE) AND COALESCE(s.pipeline_version = w.pipeline_version,FALSE) AND COALESCE(s.quality_policy_sha256 = w.quality_policy_sha256,FALSE) AND COALESCE(s.source_week_start = w.source_week_start,FALSE) AND COALESCE(s.source_week_end_exclusive = w.source_week_end_exclusive,FALSE) AND s.source_version_id IS NOT NULL AND s.source_dataset IS NOT NULL AND s.source_file_name IS NOT NULL AND s.source_url IS NOT NULL AND s.source_file_path IS NOT NULL AND s.source_file_sha256 IS NOT NULL AND s.source_week_start IS NOT NULL AND s.source_week_end_exclusive IS NOT NULL AND s.retrieved_at_utc IS NOT NULL AND s.ingested_at_utc IS NOT NULL AND s.source_record_number IS NOT NULL AND s.source_line_end IS NOT NULL AND s.csv_parse_issues IS NOT NULL AND s.record_sha256 IS NOT NULL AND s.quality_issues IS NOT NULL AND s.quality_warnings IS NOT NULL AND s.quality_status IN ('HEADER','VALID','INVALID')
  AND (s.quality_status<>'VALID' OR (s.truck_id IS NOT NULL AND length(trim(s.truck_id))>0
   AND s.event_time_unzoned >= CAST(w.source_week_start AS TIMESTAMP_NTZ)
   AND s.event_time_unzoned < CAST(w.source_week_end_exclusive AS TIMESTAMP_NTZ)
   AND s.latitude BETWEEN -90 AND 90 AND s.longitude BETWEEN -180 AND 180
   AND s.plow_active IS NOT NULL AND s.spreader_active IS NOT NULL AND s.engine_active IS NOT NULL))
  AND ((s.quality_status='HEADER' AND s.is_repeated_header AND s.quality_issues='REPEATED_HEADER')
   OR (s.quality_status<>'HEADER' AND NOT s.is_repeated_header))
  THEN 0 ELSE 1 END) AS bad
 FROM _wanted w LEFT JOIN workspace.default.winterops_v2_dev_silver s ON s.processing_key=w.processing_key GROUP BY w.processing_key),
_lineage_check AS (SELECT w.processing_key, SUM(CASE WHEN (COALESCE(s.source_version_id=b.source_version_id,FALSE) OR (s.source_version_id IS NULL AND b.source_version_id IS NULL)) AND (COALESCE(s.source_dataset=b.source_dataset,FALSE) OR (s.source_dataset IS NULL AND b.source_dataset IS NULL)) AND (COALESCE(s.source_file_name=b.source_file_name,FALSE) OR (s.source_file_name IS NULL AND b.source_file_name IS NULL)) AND (COALESCE(s.source_url=b.source_url,FALSE) OR (s.source_url IS NULL AND b.source_url IS NULL)) AND (COALESCE(s.source_file_path=b.source_file_path,FALSE) OR (s.source_file_path IS NULL AND b.source_file_path IS NULL)) AND (COALESCE(s.source_file_sha256=b.source_file_sha256,FALSE) OR (s.source_file_sha256 IS NULL AND b.source_file_sha256 IS NULL)) AND (COALESCE(s.source_week_start=b.source_week_start,FALSE) OR (s.source_week_start IS NULL AND b.source_week_start IS NULL)) AND (COALESCE(s.source_week_end_exclusive=b.source_week_end_exclusive,FALSE) OR (s.source_week_end_exclusive IS NULL AND b.source_week_end_exclusive IS NULL)) AND (COALESCE(s.retrieved_at_utc=b.retrieved_at_utc,FALSE) OR (s.retrieved_at_utc IS NULL AND b.retrieved_at_utc IS NULL)) AND (COALESCE(s.ingested_at_utc=b.ingested_at_utc,FALSE) OR (s.ingested_at_utc IS NULL AND b.ingested_at_utc IS NULL)) AND (COALESCE(s.source_record_number=b.source_record_number,FALSE) OR (s.source_record_number IS NULL AND b.source_record_number IS NULL)) AND (COALESCE(s.source_line_end=b.source_line_end,FALSE) OR (s.source_line_end IS NULL AND b.source_line_end IS NULL)) AND (COALESCE(s.csv_parse_issues=b.csv_parse_issues,FALSE) OR (s.csv_parse_issues IS NULL AND b.csv_parse_issues IS NULL)) AND (COALESCE(s.record_sha256=b.record_sha256,FALSE) OR (s.record_sha256 IS NULL AND b.record_sha256 IS NULL)) THEN 0 ELSE 1 END) AS bad
 FROM _wanted w JOIN workspace.default.winterops_v2_dev_bronze b ON b.source_version_id=w.source_version_id
 JOIN workspace.default.winterops_v2_dev_silver s ON s.processing_key=w.processing_key AND s.source_record_number=b.source_record_number GROUP BY w.processing_key),
_frequencies AS (SELECT s.processing_key,s.record_sha256,COUNT(*) AS n
 FROM workspace.default.winterops_v2_dev_silver s JOIN _wanted w ON w.processing_key=s.processing_key GROUP BY s.processing_key,s.record_sha256),
_frequency_check AS (SELECT f.processing_key,SUM(CASE WHEN s.payload_occurrences=f.n
 AND s.has_repeated_payload=(f.n>1) THEN 0 ELSE 1 END) AS bad FROM _frequencies f
 JOIN workspace.default.winterops_v2_dev_silver s ON s.processing_key=f.processing_key AND s.record_sha256=f.record_sha256 GROUP BY f.processing_key),
_selection_gate AS (
 SELECT CASE WHEN COUNT(*)=4 AND SUM(CASE WHEN m.n=1 AND m.good=1
  AND b.n=w.expected_rows AND b.unique_n=w.expected_rows AND b.first_n=1 AND b.last_n=w.expected_rows AND b.bad=0
  AND s.n=w.expected_rows AND s.unique_n=w.expected_rows AND s.first_n=1 AND s.last_n=w.expected_rows AND s.bad=0
  AND l.bad=0 AND f.bad=0
  THEN 0 ELSE 1 END)=0 THEN 1 ELSE CAST(raise_error('V2 Gold selected COMPLETE scope or contract mismatch') AS INT) END AS ok
 FROM _wanted w JOIN _manifest_check m ON m.processing_key=w.processing_key
 JOIN _bronze_check b ON b.processing_key=w.processing_key JOIN _silver_check s ON s.processing_key=w.processing_key
 LEFT JOIN _lineage_check l ON l.processing_key=w.processing_key LEFT JOIN _frequency_check f ON f.processing_key=w.processing_key),
_selected AS (SELECT s.*, w.original_csv_volume_path, w.long_gap_seconds
 FROM workspace.default.winterops_v2_dev_silver s JOIN _wanted w ON s.processing_key=w.processing_key
 CROSS JOIN _selection_gate g WHERE g.ok=1),
_valid AS (SELECT *, CAST(substring(CAST(event_time_unzoned AS STRING),1,13) || ':00:00' AS TIMESTAMP_NTZ) AS source_local_naive_hour, CAST(event_time_unzoned AS DATE) AS source_local_naive_day,
 COUNT(*) OVER (PARTITION BY processing_key,record_sha256) AS valid_payload_occurrences
 FROM _selected WHERE quality_status='VALID'),
_hourly AS (SELECT source_dataset, source_file_name, source_file_sha256, source_version_id, processing_key, pipeline_version, quality_policy_sha256, source_week_start, source_week_end_exclusive, original_csv_volume_path, source_local_naive_hour, COUNT(*) AS observation_count,
 COUNT(CASE WHEN plow_active THEN 1 END) AS plow_active_observations,
 COUNT(CASE WHEN spreader_active THEN 1 END) AS spreader_active_observations,
 COUNT(CASE WHEN plow_active AND NOT spreader_active THEN 1 END) AS plow_only_observations,
 COUNT(CASE WHEN spreader_active AND NOT plow_active THEN 1 END) AS spreader_only_observations,
 COUNT(CASE WHEN plow_active AND spreader_active THEN 1 END) AS both_active_observations,
 COUNT(CASE WHEN NOT plow_active AND NOT spreader_active THEN 1 END) AS neither_active_observations,
 COUNT(CASE WHEN NOT engine_active THEN 1 END) AS engine_off_observations,
 COUNT(CASE WHEN NOT engine_active AND (plow_active OR spreader_active) THEN 1 END) AS engine_off_with_equipment_flag_observations,
 COUNT(CASE WHEN valid_payload_occurrences>1 THEN 1 END) AS repeated_valid_payload_observations,
 COUNT(DISTINCT truck_id) AS observed_identifier_count FROM _valid GROUP BY source_dataset, source_file_name, source_file_sha256, source_version_id, processing_key, pipeline_version, quality_policy_sha256, source_week_start, source_week_end_exclusive, original_csv_volume_path, source_local_naive_hour),
_day_counts AS (SELECT source_dataset, source_file_name, source_file_sha256, source_version_id, processing_key, pipeline_version, quality_policy_sha256, source_week_start, source_week_end_exclusive, original_csv_volume_path, source_local_naive_day, COUNT(*) AS observation_count,
 COUNT(CASE WHEN plow_active THEN 1 END) AS plow_active_observations,
 COUNT(CASE WHEN spreader_active THEN 1 END) AS spreader_active_observations,
 COUNT(CASE WHEN plow_active AND NOT spreader_active THEN 1 END) AS plow_only_observations,
 COUNT(CASE WHEN spreader_active AND NOT plow_active THEN 1 END) AS spreader_only_observations,
 COUNT(CASE WHEN plow_active AND spreader_active THEN 1 END) AS both_active_observations,
 COUNT(CASE WHEN NOT plow_active AND NOT spreader_active THEN 1 END) AS neither_active_observations,
 COUNT(CASE WHEN NOT engine_active THEN 1 END) AS engine_off_observations,
 COUNT(CASE WHEN NOT engine_active AND (plow_active OR spreader_active) THEN 1 END) AS engine_off_with_equipment_flag_observations,
 COUNT(CASE WHEN valid_payload_occurrences>1 THEN 1 END) AS repeated_valid_payload_observations,
 COUNT(DISTINCT truck_id) AS observed_identifier_count,
 COUNT(DISTINCT source_local_naive_hour) AS hours_containing_telemetry FROM _valid GROUP BY source_dataset, source_file_name, source_file_sha256, source_version_id, processing_key, pipeline_version, quality_policy_sha256, source_week_start, source_week_end_exclusive, original_csv_volume_path, source_local_naive_day),
_day_peaks AS (SELECT processing_key,CAST(source_local_naive_hour AS DATE) AS day,MAX(observed_identifier_count) AS maximum_hourly_identifiers
 FROM _hourly GROUP BY processing_key,CAST(source_local_naive_hour AS DATE)),
_daily AS (SELECT a.*,p.maximum_hourly_identifiers FROM _day_counts a JOIN _day_peaks p
 ON a.processing_key=p.processing_key AND a.source_local_naive_day=p.day),
_times AS (SELECT processing_key, source_record_number, long_gap_seconds,
 (CAST(datediff(CAST(substring(CAST(event_time_unzoned AS STRING), 1, 10) AS DATE), DATE '2000-01-01') AS BIGINT) * 86400000000 + CAST(substring(CAST(event_time_unzoned AS STRING), 12, 2) AS BIGINT) * 3600000000 + CAST(substring(CAST(event_time_unzoned AS STRING), 15, 2) AS BIGINT) * 60000000 + CAST(CAST(substring(CAST(event_time_unzoned AS STRING), 18, 9) AS DECIMAL(8,6)) * 1000000 AS BIGINT)) AS clock_us,
 LAG((CAST(datediff(CAST(substring(CAST(event_time_unzoned AS STRING), 1, 10) AS DATE), DATE '2000-01-01') AS BIGINT) * 86400000000 + CAST(substring(CAST(event_time_unzoned AS STRING), 12, 2) AS BIGINT) * 3600000000 + CAST(substring(CAST(event_time_unzoned AS STRING), 15, 2) AS BIGINT) * 60000000 + CAST(CAST(substring(CAST(event_time_unzoned AS STRING), 18, 9) AS DECIMAL(8,6)) * 1000000 AS BIGINT))) OVER (PARTITION BY processing_key,truck_id ORDER BY event_time_unzoned,source_record_number) AS prior_us FROM _valid),
_gaps AS (SELECT processing_key, COUNT(prior_us) AS consecutive_timestamp_pairs,
 COUNT(CASE WHEN clock_us=prior_us THEN 1 END) AS zero_gap_pairs,
 COUNT(CASE WHEN clock_us-prior_us>long_gap_seconds*1000000 THEN 1 END) AS long_gap_pairs,
 CAST(MAX(clock_us-prior_us) AS DOUBLE)/1000000 AS maximum_source_clock_gap_seconds FROM _times GROUP BY processing_key),
_payloads AS (SELECT processing_key,record_sha256,COUNT(*) AS n FROM _valid GROUP BY processing_key,record_sha256),
_duplicates AS (SELECT processing_key,COUNT(CASE WHEN n>1 THEN 1 END) AS repeated_valid_payload_groups,
 SUM(n-1) AS excess_valid_payload_observations FROM _payloads GROUP BY processing_key),
_valid_week AS (SELECT source_dataset, source_file_name, source_file_sha256, source_version_id, processing_key, pipeline_version, quality_policy_sha256, source_week_start, source_week_end_exclusive, original_csv_volume_path, COUNT(*) AS observation_count,
 COUNT(CASE WHEN plow_active THEN 1 END) AS plow_active_observations,
 COUNT(CASE WHEN spreader_active THEN 1 END) AS spreader_active_observations,
 COUNT(CASE WHEN plow_active AND NOT spreader_active THEN 1 END) AS plow_only_observations,
 COUNT(CASE WHEN spreader_active AND NOT plow_active THEN 1 END) AS spreader_only_observations,
 COUNT(CASE WHEN plow_active AND spreader_active THEN 1 END) AS both_active_observations,
 COUNT(CASE WHEN NOT plow_active AND NOT spreader_active THEN 1 END) AS neither_active_observations,
 COUNT(CASE WHEN NOT engine_active THEN 1 END) AS engine_off_observations,
 COUNT(CASE WHEN NOT engine_active AND (plow_active OR spreader_active) THEN 1 END) AS engine_off_with_equipment_flag_observations,
 COUNT(CASE WHEN valid_payload_occurrences>1 THEN 1 END) AS repeated_valid_payload_observations,
 COUNT(DISTINCT truck_id) AS observed_identifier_count, COUNT(DISTINCT source_local_naive_hour) AS hours_containing_telemetry,
 COUNT(DISTINCT source_local_naive_day) AS days_containing_telemetry FROM _valid GROUP BY source_dataset, source_file_name, source_file_sha256, source_version_id, processing_key, pipeline_version, quality_policy_sha256, source_week_start, source_week_end_exclusive, original_csv_volume_path),
_quality AS (SELECT processing_key,COUNT(*) AS silver_rows,
 COUNT(CASE WHEN quality_status='HEADER' THEN 1 END) AS header_rows,
 COUNT(CASE WHEN quality_status='VALID' THEN 1 END) AS valid_rows,
 COUNT(CASE WHEN quality_status='INVALID' THEN 1 END) AS invalid_rows,
 COUNT(CASE WHEN quality_status<>'VALID' THEN 1 END) AS quarantine_rows,
 COUNT(CASE WHEN quality_status='INVALID' AND (quality_issues LIKE '%INVALID_LATITUDE%' OR quality_issues LIKE '%INVALID_LONGITUDE%') THEN 1 END) AS invalid_coordinate_rows,
 COUNT(CASE WHEN quality_status<>'HEADER' AND quality_warnings LIKE '%OUTSIDE_REVIEW_ENVELOPE%' THEN 1 END) AS outside_review_envelope_rows
 FROM _selected GROUP BY processing_key),
_week_peaks AS (SELECT processing_key,MAX(observed_identifier_count) AS peak FROM _hourly GROUP BY processing_key),
_weekly AS (SELECT w.source_dataset, w.source_file_name, w.source_file_sha256, w.source_version_id, w.processing_key, w.pipeline_version, w.quality_policy_sha256, w.source_week_start, w.source_week_end_exclusive, w.original_csv_volume_path, w.expected_rows AS bronze_rows,
 q.silver_rows,q.header_rows,q.valid_rows,q.invalid_rows,q.quarantine_rows,q.invalid_coordinate_rows,q.outside_review_envelope_rows,
 COALESCE(v.observation_count,0) AS observation_count, COALESCE(v.plow_active_observations,0) AS plow_active_observations, COALESCE(v.spreader_active_observations,0) AS spreader_active_observations, COALESCE(v.plow_only_observations,0) AS plow_only_observations, COALESCE(v.spreader_only_observations,0) AS spreader_only_observations, COALESCE(v.both_active_observations,0) AS both_active_observations, COALESCE(v.neither_active_observations,0) AS neither_active_observations, COALESCE(v.engine_off_observations,0) AS engine_off_observations, COALESCE(v.engine_off_with_equipment_flag_observations,0) AS engine_off_with_equipment_flag_observations, COALESCE(v.repeated_valid_payload_observations,0) AS repeated_valid_payload_observations, COALESCE(v.observed_identifier_count,0) AS observed_identifier_count, COALESCE(v.hours_containing_telemetry,0) AS hours_containing_telemetry, COALESCE(v.days_containing_telemetry,0) AS days_containing_telemetry,
 COALESCE(p.peak,0) AS maximum_hourly_identifiers,
 COALESCE(d.repeated_valid_payload_groups,0) AS repeated_valid_payload_groups,
 COALESCE(d.excess_valid_payload_observations,0) AS excess_valid_payload_observations,
 COALESCE(g.consecutive_timestamp_pairs,0) AS consecutive_timestamp_pairs, COALESCE(g.zero_gap_pairs,0) AS zero_gap_pairs,
 COALESCE(g.long_gap_pairs,0) AS long_gap_pairs,g.maximum_source_clock_gap_seconds
 FROM _wanted w CROSS JOIN _selection_gate gate JOIN _quality q ON q.processing_key=w.processing_key
 LEFT JOIN _valid_week v ON v.processing_key=w.processing_key LEFT JOIN _duplicates d ON d.processing_key=w.processing_key
 LEFT JOIN _gaps g ON g.processing_key=w.processing_key LEFT JOIN _week_peaks p ON p.processing_key=w.processing_key WHERE gate.ok=1)
SELECT * FROM _weekly ORDER BY source_week_start;

-- READ-ONLY CANDIDATE: daily
WITH _wanted AS (SELECT 'windsor_snowplow_activity' AS source_dataset, 'snowplow-2026-01-05_2026-01-11.csv' AS source_file_name, '271c9339a42043f441b6c17e82dd309609db4b20e9953b9f368a95ec472d763d' AS source_file_sha256, '8ccb2a2dd5ec057361cf6d7cc7193b5acbdd858b84102ba550a92febe9bb4ed1' AS source_version_id, 'f07ba6a0ad499a9baf53d2f7c46df09607523371428791593143a29b56f6b466' AS processing_key, 'windsor-foundation-v2.1' AS pipeline_version, '03829a2ce3b308a45e0205ca12a5288e5cb08b97189cf20b69c0e37d4c546e08' AS quality_policy_sha256, DATE '2026-01-05' AS source_week_start, DATE '2026-01-12' AS source_week_end_exclusive, '/Volumes/workspace/default/winterops_raw/original_csv/snowplow-2026-01-05_2026-01-11.csv/271c9339a42043f441b6c17e82dd309609db4b20e9953b9f368a95ec472d763d/snowplow-2026-01-05_2026-01-11.csv' AS original_csv_volume_path, 2810 AS expected_rows, 1800 AS long_gap_seconds, '{"review_lat_min": 42.1, "review_lat_max": 42.5, "review_lon_min": -83.3, "review_lon_max": -82.6, "nominal_interval_seconds": 15, "long_gap_seconds": 1800, "dense_hour_observations": 1000}' AS policy_json
UNION ALL
SELECT 'windsor_snowplow_activity' AS source_dataset, 'snowplow-2026-01-12_2026-01-18.csv' AS source_file_name, 'f5d7633c910e1ad6be23b4111445bf0bc14fe2071c6ea0f0d4cd456295ea9e94' AS source_file_sha256, '73e9338d8a7e78ba01827806b2172a715a50b90c819959ba1ade17632f2d4433' AS source_version_id, '5e478fdced5a0ac67865413d68b9359a97fffd980a2a6dee976d6ab984c599be' AS processing_key, 'windsor-foundation-v2.1' AS pipeline_version, '03829a2ce3b308a45e0205ca12a5288e5cb08b97189cf20b69c0e37d4c546e08' AS quality_policy_sha256, DATE '2026-01-12' AS source_week_start, DATE '2026-01-19' AS source_week_end_exclusive, '/Volumes/workspace/default/winterops_raw/snowplow-2026-01-12_2026-01-18.csv' AS original_csv_volume_path, 110337 AS expected_rows, 1800 AS long_gap_seconds, '{"review_lat_min": 42.1, "review_lat_max": 42.5, "review_lon_min": -83.3, "review_lon_max": -82.6, "nominal_interval_seconds": 15, "long_gap_seconds": 1800, "dense_hour_observations": 1000}' AS policy_json
UNION ALL
SELECT 'windsor_snowplow_activity' AS source_dataset, 'snowplow-2026-01-19_2026-01-25.csv' AS source_file_name, 'b78d0fb82c8e3c5204ee79eea7a03417cd54bc935ead9b04577a30dc908c7c49' AS source_file_sha256, 'd2a89e9a8582aefdca97264a482d51a6116b827a71f0241a0e1f0149ed14f97a' AS source_version_id, 'bb478f6992172da1298db36c3a5d92aa4c349769064ec66002f347a2458e415c' AS processing_key, 'windsor-foundation-v2.1' AS pipeline_version, '03829a2ce3b308a45e0205ca12a5288e5cb08b97189cf20b69c0e37d4c546e08' AS quality_policy_sha256, DATE '2026-01-19' AS source_week_start, DATE '2026-01-26' AS source_week_end_exclusive, '/Volumes/workspace/default/winterops_raw/original_csv/snowplow-2026-01-19_2026-01-25.csv/b78d0fb82c8e3c5204ee79eea7a03417cd54bc935ead9b04577a30dc908c7c49/snowplow-2026-01-19_2026-01-25.csv' AS original_csv_volume_path, 118159 AS expected_rows, 1800 AS long_gap_seconds, '{"review_lat_min": 42.1, "review_lat_max": 42.5, "review_lon_min": -83.3, "review_lon_max": -82.6, "nominal_interval_seconds": 15, "long_gap_seconds": 1800, "dense_hour_observations": 1000}' AS policy_json
UNION ALL
SELECT 'windsor_snowplow_activity' AS source_dataset, 'snowplow-2026-01-26_2026-02-01.csv' AS source_file_name, 'cebcbd758e2a0cf5d0624ecf9cd6993244e7becdd1846a4057b4f63be22ed6c6' AS source_file_sha256, 'ad5c201ccee0b96b2f4907f10ee3a064a7562d17429146d2205b1eaca46fdc00' AS source_version_id, '9c8e1b6f640e75c21f1c9f429ec670c389bf178269afd2f1543b2ae759c3eeae' AS processing_key, 'windsor-foundation-v2.1' AS pipeline_version, '03829a2ce3b308a45e0205ca12a5288e5cb08b97189cf20b69c0e37d4c546e08' AS quality_policy_sha256, DATE '2026-01-26' AS source_week_start, DATE '2026-02-02' AS source_week_end_exclusive, '/Volumes/workspace/default/winterops_raw/original_csv/snowplow-2026-01-26_2026-02-01.csv/cebcbd758e2a0cf5d0624ecf9cd6993244e7becdd1846a4057b4f63be22ed6c6/snowplow-2026-01-26_2026-02-01.csv' AS original_csv_volume_path, 66850 AS expected_rows, 1800 AS long_gap_seconds, '{"review_lat_min": 42.1, "review_lat_max": 42.5, "review_lon_min": -83.3, "review_lon_max": -82.6, "nominal_interval_seconds": 15, "long_gap_seconds": 1800, "dense_hour_observations": 1000}' AS policy_json),
_manifest_check AS (
 SELECT w.processing_key, COUNT(m.processing_key) AS n,
 SUM(CASE WHEN m.status='COMPLETE' AND m.last_successful_stage='COMPLETE' AND m.error_code IS NULL
  AND m.source_version_id=w.source_version_id AND m.source_file_name=w.source_file_name
  AND m.source_file_sha256=w.source_file_sha256 AND m.policy_json=w.policy_json
  AND m.bronze_rows=w.expected_rows AND m.silver_rows=w.expected_rows THEN 1 ELSE 0 END) AS good
 FROM _wanted w LEFT JOIN workspace.default.winterops_v2_dev_manifest m ON m.processing_key=w.processing_key GROUP BY w.processing_key),
_bronze_check AS (
 SELECT w.processing_key, COUNT(b.source_record_number) AS n, COUNT(DISTINCT b.source_record_number) AS unique_n,
 MIN(b.source_record_number) AS first_n, MAX(b.source_record_number) AS last_n,
 SUM(CASE WHEN COALESCE(b.source_dataset = w.source_dataset,FALSE) AND COALESCE(b.source_file_name = w.source_file_name,FALSE) AND COALESCE(b.source_file_sha256 = w.source_file_sha256,FALSE) AND COALESCE(b.source_week_start = w.source_week_start,FALSE) AND COALESCE(b.source_week_end_exclusive = w.source_week_end_exclusive,FALSE) AND b.source_version_id IS NOT NULL AND b.source_dataset IS NOT NULL AND b.source_file_name IS NOT NULL AND b.source_url IS NOT NULL AND b.source_file_path IS NOT NULL AND b.source_file_sha256 IS NOT NULL AND b.source_week_start IS NOT NULL AND b.source_week_end_exclusive IS NOT NULL AND b.retrieved_at_utc IS NOT NULL AND b.ingested_at_utc IS NOT NULL AND b.source_record_number IS NOT NULL AND b.source_line_end IS NOT NULL AND b.csv_parse_issues IS NOT NULL AND b.raw_values_json IS NOT NULL AND b.raw_record_json IS NOT NULL AND b.record_sha256 IS NOT NULL THEN 0 ELSE 1 END) AS bad
 FROM _wanted w LEFT JOIN workspace.default.winterops_v2_dev_bronze b ON b.source_version_id=w.source_version_id GROUP BY w.processing_key),
_silver_check AS (
 SELECT w.processing_key, COUNT(s.source_record_number) AS n, COUNT(DISTINCT s.source_record_number) AS unique_n,
 MIN(s.source_record_number) AS first_n, MAX(s.source_record_number) AS last_n,
 SUM(CASE WHEN COALESCE(s.source_version_id = w.source_version_id,FALSE) AND COALESCE(s.source_dataset = w.source_dataset,FALSE) AND COALESCE(s.source_file_name = w.source_file_name,FALSE) AND COALESCE(s.source_file_sha256 = w.source_file_sha256,FALSE) AND COALESCE(s.pipeline_version = w.pipeline_version,FALSE) AND COALESCE(s.quality_policy_sha256 = w.quality_policy_sha256,FALSE) AND COALESCE(s.source_week_start = w.source_week_start,FALSE) AND COALESCE(s.source_week_end_exclusive = w.source_week_end_exclusive,FALSE) AND s.source_version_id IS NOT NULL AND s.source_dataset IS NOT NULL AND s.source_file_name IS NOT NULL AND s.source_url IS NOT NULL AND s.source_file_path IS NOT NULL AND s.source_file_sha256 IS NOT NULL AND s.source_week_start IS NOT NULL AND s.source_week_end_exclusive IS NOT NULL AND s.retrieved_at_utc IS NOT NULL AND s.ingested_at_utc IS NOT NULL AND s.source_record_number IS NOT NULL AND s.source_line_end IS NOT NULL AND s.csv_parse_issues IS NOT NULL AND s.record_sha256 IS NOT NULL AND s.quality_issues IS NOT NULL AND s.quality_warnings IS NOT NULL AND s.quality_status IN ('HEADER','VALID','INVALID')
  AND (s.quality_status<>'VALID' OR (s.truck_id IS NOT NULL AND length(trim(s.truck_id))>0
   AND s.event_time_unzoned >= CAST(w.source_week_start AS TIMESTAMP_NTZ)
   AND s.event_time_unzoned < CAST(w.source_week_end_exclusive AS TIMESTAMP_NTZ)
   AND s.latitude BETWEEN -90 AND 90 AND s.longitude BETWEEN -180 AND 180
   AND s.plow_active IS NOT NULL AND s.spreader_active IS NOT NULL AND s.engine_active IS NOT NULL))
  AND ((s.quality_status='HEADER' AND s.is_repeated_header AND s.quality_issues='REPEATED_HEADER')
   OR (s.quality_status<>'HEADER' AND NOT s.is_repeated_header))
  THEN 0 ELSE 1 END) AS bad
 FROM _wanted w LEFT JOIN workspace.default.winterops_v2_dev_silver s ON s.processing_key=w.processing_key GROUP BY w.processing_key),
_lineage_check AS (SELECT w.processing_key, SUM(CASE WHEN (COALESCE(s.source_version_id=b.source_version_id,FALSE) OR (s.source_version_id IS NULL AND b.source_version_id IS NULL)) AND (COALESCE(s.source_dataset=b.source_dataset,FALSE) OR (s.source_dataset IS NULL AND b.source_dataset IS NULL)) AND (COALESCE(s.source_file_name=b.source_file_name,FALSE) OR (s.source_file_name IS NULL AND b.source_file_name IS NULL)) AND (COALESCE(s.source_url=b.source_url,FALSE) OR (s.source_url IS NULL AND b.source_url IS NULL)) AND (COALESCE(s.source_file_path=b.source_file_path,FALSE) OR (s.source_file_path IS NULL AND b.source_file_path IS NULL)) AND (COALESCE(s.source_file_sha256=b.source_file_sha256,FALSE) OR (s.source_file_sha256 IS NULL AND b.source_file_sha256 IS NULL)) AND (COALESCE(s.source_week_start=b.source_week_start,FALSE) OR (s.source_week_start IS NULL AND b.source_week_start IS NULL)) AND (COALESCE(s.source_week_end_exclusive=b.source_week_end_exclusive,FALSE) OR (s.source_week_end_exclusive IS NULL AND b.source_week_end_exclusive IS NULL)) AND (COALESCE(s.retrieved_at_utc=b.retrieved_at_utc,FALSE) OR (s.retrieved_at_utc IS NULL AND b.retrieved_at_utc IS NULL)) AND (COALESCE(s.ingested_at_utc=b.ingested_at_utc,FALSE) OR (s.ingested_at_utc IS NULL AND b.ingested_at_utc IS NULL)) AND (COALESCE(s.source_record_number=b.source_record_number,FALSE) OR (s.source_record_number IS NULL AND b.source_record_number IS NULL)) AND (COALESCE(s.source_line_end=b.source_line_end,FALSE) OR (s.source_line_end IS NULL AND b.source_line_end IS NULL)) AND (COALESCE(s.csv_parse_issues=b.csv_parse_issues,FALSE) OR (s.csv_parse_issues IS NULL AND b.csv_parse_issues IS NULL)) AND (COALESCE(s.record_sha256=b.record_sha256,FALSE) OR (s.record_sha256 IS NULL AND b.record_sha256 IS NULL)) THEN 0 ELSE 1 END) AS bad
 FROM _wanted w JOIN workspace.default.winterops_v2_dev_bronze b ON b.source_version_id=w.source_version_id
 JOIN workspace.default.winterops_v2_dev_silver s ON s.processing_key=w.processing_key AND s.source_record_number=b.source_record_number GROUP BY w.processing_key),
_frequencies AS (SELECT s.processing_key,s.record_sha256,COUNT(*) AS n
 FROM workspace.default.winterops_v2_dev_silver s JOIN _wanted w ON w.processing_key=s.processing_key GROUP BY s.processing_key,s.record_sha256),
_frequency_check AS (SELECT f.processing_key,SUM(CASE WHEN s.payload_occurrences=f.n
 AND s.has_repeated_payload=(f.n>1) THEN 0 ELSE 1 END) AS bad FROM _frequencies f
 JOIN workspace.default.winterops_v2_dev_silver s ON s.processing_key=f.processing_key AND s.record_sha256=f.record_sha256 GROUP BY f.processing_key),
_selection_gate AS (
 SELECT CASE WHEN COUNT(*)=4 AND SUM(CASE WHEN m.n=1 AND m.good=1
  AND b.n=w.expected_rows AND b.unique_n=w.expected_rows AND b.first_n=1 AND b.last_n=w.expected_rows AND b.bad=0
  AND s.n=w.expected_rows AND s.unique_n=w.expected_rows AND s.first_n=1 AND s.last_n=w.expected_rows AND s.bad=0
  AND l.bad=0 AND f.bad=0
  THEN 0 ELSE 1 END)=0 THEN 1 ELSE CAST(raise_error('V2 Gold selected COMPLETE scope or contract mismatch') AS INT) END AS ok
 FROM _wanted w JOIN _manifest_check m ON m.processing_key=w.processing_key
 JOIN _bronze_check b ON b.processing_key=w.processing_key JOIN _silver_check s ON s.processing_key=w.processing_key
 LEFT JOIN _lineage_check l ON l.processing_key=w.processing_key LEFT JOIN _frequency_check f ON f.processing_key=w.processing_key),
_selected AS (SELECT s.*, w.original_csv_volume_path, w.long_gap_seconds
 FROM workspace.default.winterops_v2_dev_silver s JOIN _wanted w ON s.processing_key=w.processing_key
 CROSS JOIN _selection_gate g WHERE g.ok=1),
_valid AS (SELECT *, CAST(substring(CAST(event_time_unzoned AS STRING),1,13) || ':00:00' AS TIMESTAMP_NTZ) AS source_local_naive_hour, CAST(event_time_unzoned AS DATE) AS source_local_naive_day,
 COUNT(*) OVER (PARTITION BY processing_key,record_sha256) AS valid_payload_occurrences
 FROM _selected WHERE quality_status='VALID'),
_hourly AS (SELECT source_dataset, source_file_name, source_file_sha256, source_version_id, processing_key, pipeline_version, quality_policy_sha256, source_week_start, source_week_end_exclusive, original_csv_volume_path, source_local_naive_hour, COUNT(*) AS observation_count,
 COUNT(CASE WHEN plow_active THEN 1 END) AS plow_active_observations,
 COUNT(CASE WHEN spreader_active THEN 1 END) AS spreader_active_observations,
 COUNT(CASE WHEN plow_active AND NOT spreader_active THEN 1 END) AS plow_only_observations,
 COUNT(CASE WHEN spreader_active AND NOT plow_active THEN 1 END) AS spreader_only_observations,
 COUNT(CASE WHEN plow_active AND spreader_active THEN 1 END) AS both_active_observations,
 COUNT(CASE WHEN NOT plow_active AND NOT spreader_active THEN 1 END) AS neither_active_observations,
 COUNT(CASE WHEN NOT engine_active THEN 1 END) AS engine_off_observations,
 COUNT(CASE WHEN NOT engine_active AND (plow_active OR spreader_active) THEN 1 END) AS engine_off_with_equipment_flag_observations,
 COUNT(CASE WHEN valid_payload_occurrences>1 THEN 1 END) AS repeated_valid_payload_observations,
 COUNT(DISTINCT truck_id) AS observed_identifier_count FROM _valid GROUP BY source_dataset, source_file_name, source_file_sha256, source_version_id, processing_key, pipeline_version, quality_policy_sha256, source_week_start, source_week_end_exclusive, original_csv_volume_path, source_local_naive_hour),
_day_counts AS (SELECT source_dataset, source_file_name, source_file_sha256, source_version_id, processing_key, pipeline_version, quality_policy_sha256, source_week_start, source_week_end_exclusive, original_csv_volume_path, source_local_naive_day, COUNT(*) AS observation_count,
 COUNT(CASE WHEN plow_active THEN 1 END) AS plow_active_observations,
 COUNT(CASE WHEN spreader_active THEN 1 END) AS spreader_active_observations,
 COUNT(CASE WHEN plow_active AND NOT spreader_active THEN 1 END) AS plow_only_observations,
 COUNT(CASE WHEN spreader_active AND NOT plow_active THEN 1 END) AS spreader_only_observations,
 COUNT(CASE WHEN plow_active AND spreader_active THEN 1 END) AS both_active_observations,
 COUNT(CASE WHEN NOT plow_active AND NOT spreader_active THEN 1 END) AS neither_active_observations,
 COUNT(CASE WHEN NOT engine_active THEN 1 END) AS engine_off_observations,
 COUNT(CASE WHEN NOT engine_active AND (plow_active OR spreader_active) THEN 1 END) AS engine_off_with_equipment_flag_observations,
 COUNT(CASE WHEN valid_payload_occurrences>1 THEN 1 END) AS repeated_valid_payload_observations,
 COUNT(DISTINCT truck_id) AS observed_identifier_count,
 COUNT(DISTINCT source_local_naive_hour) AS hours_containing_telemetry FROM _valid GROUP BY source_dataset, source_file_name, source_file_sha256, source_version_id, processing_key, pipeline_version, quality_policy_sha256, source_week_start, source_week_end_exclusive, original_csv_volume_path, source_local_naive_day),
_day_peaks AS (SELECT processing_key,CAST(source_local_naive_hour AS DATE) AS day,MAX(observed_identifier_count) AS maximum_hourly_identifiers
 FROM _hourly GROUP BY processing_key,CAST(source_local_naive_hour AS DATE)),
_daily AS (SELECT a.*,p.maximum_hourly_identifiers FROM _day_counts a JOIN _day_peaks p
 ON a.processing_key=p.processing_key AND a.source_local_naive_day=p.day),
_times AS (SELECT processing_key, source_record_number, long_gap_seconds,
 (CAST(datediff(CAST(substring(CAST(event_time_unzoned AS STRING), 1, 10) AS DATE), DATE '2000-01-01') AS BIGINT) * 86400000000 + CAST(substring(CAST(event_time_unzoned AS STRING), 12, 2) AS BIGINT) * 3600000000 + CAST(substring(CAST(event_time_unzoned AS STRING), 15, 2) AS BIGINT) * 60000000 + CAST(CAST(substring(CAST(event_time_unzoned AS STRING), 18, 9) AS DECIMAL(8,6)) * 1000000 AS BIGINT)) AS clock_us,
 LAG((CAST(datediff(CAST(substring(CAST(event_time_unzoned AS STRING), 1, 10) AS DATE), DATE '2000-01-01') AS BIGINT) * 86400000000 + CAST(substring(CAST(event_time_unzoned AS STRING), 12, 2) AS BIGINT) * 3600000000 + CAST(substring(CAST(event_time_unzoned AS STRING), 15, 2) AS BIGINT) * 60000000 + CAST(CAST(substring(CAST(event_time_unzoned AS STRING), 18, 9) AS DECIMAL(8,6)) * 1000000 AS BIGINT))) OVER (PARTITION BY processing_key,truck_id ORDER BY event_time_unzoned,source_record_number) AS prior_us FROM _valid),
_gaps AS (SELECT processing_key, COUNT(prior_us) AS consecutive_timestamp_pairs,
 COUNT(CASE WHEN clock_us=prior_us THEN 1 END) AS zero_gap_pairs,
 COUNT(CASE WHEN clock_us-prior_us>long_gap_seconds*1000000 THEN 1 END) AS long_gap_pairs,
 CAST(MAX(clock_us-prior_us) AS DOUBLE)/1000000 AS maximum_source_clock_gap_seconds FROM _times GROUP BY processing_key),
_payloads AS (SELECT processing_key,record_sha256,COUNT(*) AS n FROM _valid GROUP BY processing_key,record_sha256),
_duplicates AS (SELECT processing_key,COUNT(CASE WHEN n>1 THEN 1 END) AS repeated_valid_payload_groups,
 SUM(n-1) AS excess_valid_payload_observations FROM _payloads GROUP BY processing_key),
_valid_week AS (SELECT source_dataset, source_file_name, source_file_sha256, source_version_id, processing_key, pipeline_version, quality_policy_sha256, source_week_start, source_week_end_exclusive, original_csv_volume_path, COUNT(*) AS observation_count,
 COUNT(CASE WHEN plow_active THEN 1 END) AS plow_active_observations,
 COUNT(CASE WHEN spreader_active THEN 1 END) AS spreader_active_observations,
 COUNT(CASE WHEN plow_active AND NOT spreader_active THEN 1 END) AS plow_only_observations,
 COUNT(CASE WHEN spreader_active AND NOT plow_active THEN 1 END) AS spreader_only_observations,
 COUNT(CASE WHEN plow_active AND spreader_active THEN 1 END) AS both_active_observations,
 COUNT(CASE WHEN NOT plow_active AND NOT spreader_active THEN 1 END) AS neither_active_observations,
 COUNT(CASE WHEN NOT engine_active THEN 1 END) AS engine_off_observations,
 COUNT(CASE WHEN NOT engine_active AND (plow_active OR spreader_active) THEN 1 END) AS engine_off_with_equipment_flag_observations,
 COUNT(CASE WHEN valid_payload_occurrences>1 THEN 1 END) AS repeated_valid_payload_observations,
 COUNT(DISTINCT truck_id) AS observed_identifier_count, COUNT(DISTINCT source_local_naive_hour) AS hours_containing_telemetry,
 COUNT(DISTINCT source_local_naive_day) AS days_containing_telemetry FROM _valid GROUP BY source_dataset, source_file_name, source_file_sha256, source_version_id, processing_key, pipeline_version, quality_policy_sha256, source_week_start, source_week_end_exclusive, original_csv_volume_path),
_quality AS (SELECT processing_key,COUNT(*) AS silver_rows,
 COUNT(CASE WHEN quality_status='HEADER' THEN 1 END) AS header_rows,
 COUNT(CASE WHEN quality_status='VALID' THEN 1 END) AS valid_rows,
 COUNT(CASE WHEN quality_status='INVALID' THEN 1 END) AS invalid_rows,
 COUNT(CASE WHEN quality_status<>'VALID' THEN 1 END) AS quarantine_rows,
 COUNT(CASE WHEN quality_status='INVALID' AND (quality_issues LIKE '%INVALID_LATITUDE%' OR quality_issues LIKE '%INVALID_LONGITUDE%') THEN 1 END) AS invalid_coordinate_rows,
 COUNT(CASE WHEN quality_status<>'HEADER' AND quality_warnings LIKE '%OUTSIDE_REVIEW_ENVELOPE%' THEN 1 END) AS outside_review_envelope_rows
 FROM _selected GROUP BY processing_key),
_week_peaks AS (SELECT processing_key,MAX(observed_identifier_count) AS peak FROM _hourly GROUP BY processing_key),
_weekly AS (SELECT w.source_dataset, w.source_file_name, w.source_file_sha256, w.source_version_id, w.processing_key, w.pipeline_version, w.quality_policy_sha256, w.source_week_start, w.source_week_end_exclusive, w.original_csv_volume_path, w.expected_rows AS bronze_rows,
 q.silver_rows,q.header_rows,q.valid_rows,q.invalid_rows,q.quarantine_rows,q.invalid_coordinate_rows,q.outside_review_envelope_rows,
 COALESCE(v.observation_count,0) AS observation_count, COALESCE(v.plow_active_observations,0) AS plow_active_observations, COALESCE(v.spreader_active_observations,0) AS spreader_active_observations, COALESCE(v.plow_only_observations,0) AS plow_only_observations, COALESCE(v.spreader_only_observations,0) AS spreader_only_observations, COALESCE(v.both_active_observations,0) AS both_active_observations, COALESCE(v.neither_active_observations,0) AS neither_active_observations, COALESCE(v.engine_off_observations,0) AS engine_off_observations, COALESCE(v.engine_off_with_equipment_flag_observations,0) AS engine_off_with_equipment_flag_observations, COALESCE(v.repeated_valid_payload_observations,0) AS repeated_valid_payload_observations, COALESCE(v.observed_identifier_count,0) AS observed_identifier_count, COALESCE(v.hours_containing_telemetry,0) AS hours_containing_telemetry, COALESCE(v.days_containing_telemetry,0) AS days_containing_telemetry,
 COALESCE(p.peak,0) AS maximum_hourly_identifiers,
 COALESCE(d.repeated_valid_payload_groups,0) AS repeated_valid_payload_groups,
 COALESCE(d.excess_valid_payload_observations,0) AS excess_valid_payload_observations,
 COALESCE(g.consecutive_timestamp_pairs,0) AS consecutive_timestamp_pairs, COALESCE(g.zero_gap_pairs,0) AS zero_gap_pairs,
 COALESCE(g.long_gap_pairs,0) AS long_gap_pairs,g.maximum_source_clock_gap_seconds
 FROM _wanted w CROSS JOIN _selection_gate gate JOIN _quality q ON q.processing_key=w.processing_key
 LEFT JOIN _valid_week v ON v.processing_key=w.processing_key LEFT JOIN _duplicates d ON d.processing_key=w.processing_key
 LEFT JOIN _gaps g ON g.processing_key=w.processing_key LEFT JOIN _week_peaks p ON p.processing_key=w.processing_key WHERE gate.ok=1)
SELECT * FROM _daily ORDER BY source_week_start, source_local_naive_day;

-- READ-ONLY CANDIDATE: hourly
WITH _wanted AS (SELECT 'windsor_snowplow_activity' AS source_dataset, 'snowplow-2026-01-05_2026-01-11.csv' AS source_file_name, '271c9339a42043f441b6c17e82dd309609db4b20e9953b9f368a95ec472d763d' AS source_file_sha256, '8ccb2a2dd5ec057361cf6d7cc7193b5acbdd858b84102ba550a92febe9bb4ed1' AS source_version_id, 'f07ba6a0ad499a9baf53d2f7c46df09607523371428791593143a29b56f6b466' AS processing_key, 'windsor-foundation-v2.1' AS pipeline_version, '03829a2ce3b308a45e0205ca12a5288e5cb08b97189cf20b69c0e37d4c546e08' AS quality_policy_sha256, DATE '2026-01-05' AS source_week_start, DATE '2026-01-12' AS source_week_end_exclusive, '/Volumes/workspace/default/winterops_raw/original_csv/snowplow-2026-01-05_2026-01-11.csv/271c9339a42043f441b6c17e82dd309609db4b20e9953b9f368a95ec472d763d/snowplow-2026-01-05_2026-01-11.csv' AS original_csv_volume_path, 2810 AS expected_rows, 1800 AS long_gap_seconds, '{"review_lat_min": 42.1, "review_lat_max": 42.5, "review_lon_min": -83.3, "review_lon_max": -82.6, "nominal_interval_seconds": 15, "long_gap_seconds": 1800, "dense_hour_observations": 1000}' AS policy_json
UNION ALL
SELECT 'windsor_snowplow_activity' AS source_dataset, 'snowplow-2026-01-12_2026-01-18.csv' AS source_file_name, 'f5d7633c910e1ad6be23b4111445bf0bc14fe2071c6ea0f0d4cd456295ea9e94' AS source_file_sha256, '73e9338d8a7e78ba01827806b2172a715a50b90c819959ba1ade17632f2d4433' AS source_version_id, '5e478fdced5a0ac67865413d68b9359a97fffd980a2a6dee976d6ab984c599be' AS processing_key, 'windsor-foundation-v2.1' AS pipeline_version, '03829a2ce3b308a45e0205ca12a5288e5cb08b97189cf20b69c0e37d4c546e08' AS quality_policy_sha256, DATE '2026-01-12' AS source_week_start, DATE '2026-01-19' AS source_week_end_exclusive, '/Volumes/workspace/default/winterops_raw/snowplow-2026-01-12_2026-01-18.csv' AS original_csv_volume_path, 110337 AS expected_rows, 1800 AS long_gap_seconds, '{"review_lat_min": 42.1, "review_lat_max": 42.5, "review_lon_min": -83.3, "review_lon_max": -82.6, "nominal_interval_seconds": 15, "long_gap_seconds": 1800, "dense_hour_observations": 1000}' AS policy_json
UNION ALL
SELECT 'windsor_snowplow_activity' AS source_dataset, 'snowplow-2026-01-19_2026-01-25.csv' AS source_file_name, 'b78d0fb82c8e3c5204ee79eea7a03417cd54bc935ead9b04577a30dc908c7c49' AS source_file_sha256, 'd2a89e9a8582aefdca97264a482d51a6116b827a71f0241a0e1f0149ed14f97a' AS source_version_id, 'bb478f6992172da1298db36c3a5d92aa4c349769064ec66002f347a2458e415c' AS processing_key, 'windsor-foundation-v2.1' AS pipeline_version, '03829a2ce3b308a45e0205ca12a5288e5cb08b97189cf20b69c0e37d4c546e08' AS quality_policy_sha256, DATE '2026-01-19' AS source_week_start, DATE '2026-01-26' AS source_week_end_exclusive, '/Volumes/workspace/default/winterops_raw/original_csv/snowplow-2026-01-19_2026-01-25.csv/b78d0fb82c8e3c5204ee79eea7a03417cd54bc935ead9b04577a30dc908c7c49/snowplow-2026-01-19_2026-01-25.csv' AS original_csv_volume_path, 118159 AS expected_rows, 1800 AS long_gap_seconds, '{"review_lat_min": 42.1, "review_lat_max": 42.5, "review_lon_min": -83.3, "review_lon_max": -82.6, "nominal_interval_seconds": 15, "long_gap_seconds": 1800, "dense_hour_observations": 1000}' AS policy_json
UNION ALL
SELECT 'windsor_snowplow_activity' AS source_dataset, 'snowplow-2026-01-26_2026-02-01.csv' AS source_file_name, 'cebcbd758e2a0cf5d0624ecf9cd6993244e7becdd1846a4057b4f63be22ed6c6' AS source_file_sha256, 'ad5c201ccee0b96b2f4907f10ee3a064a7562d17429146d2205b1eaca46fdc00' AS source_version_id, '9c8e1b6f640e75c21f1c9f429ec670c389bf178269afd2f1543b2ae759c3eeae' AS processing_key, 'windsor-foundation-v2.1' AS pipeline_version, '03829a2ce3b308a45e0205ca12a5288e5cb08b97189cf20b69c0e37d4c546e08' AS quality_policy_sha256, DATE '2026-01-26' AS source_week_start, DATE '2026-02-02' AS source_week_end_exclusive, '/Volumes/workspace/default/winterops_raw/original_csv/snowplow-2026-01-26_2026-02-01.csv/cebcbd758e2a0cf5d0624ecf9cd6993244e7becdd1846a4057b4f63be22ed6c6/snowplow-2026-01-26_2026-02-01.csv' AS original_csv_volume_path, 66850 AS expected_rows, 1800 AS long_gap_seconds, '{"review_lat_min": 42.1, "review_lat_max": 42.5, "review_lon_min": -83.3, "review_lon_max": -82.6, "nominal_interval_seconds": 15, "long_gap_seconds": 1800, "dense_hour_observations": 1000}' AS policy_json),
_manifest_check AS (
 SELECT w.processing_key, COUNT(m.processing_key) AS n,
 SUM(CASE WHEN m.status='COMPLETE' AND m.last_successful_stage='COMPLETE' AND m.error_code IS NULL
  AND m.source_version_id=w.source_version_id AND m.source_file_name=w.source_file_name
  AND m.source_file_sha256=w.source_file_sha256 AND m.policy_json=w.policy_json
  AND m.bronze_rows=w.expected_rows AND m.silver_rows=w.expected_rows THEN 1 ELSE 0 END) AS good
 FROM _wanted w LEFT JOIN workspace.default.winterops_v2_dev_manifest m ON m.processing_key=w.processing_key GROUP BY w.processing_key),
_bronze_check AS (
 SELECT w.processing_key, COUNT(b.source_record_number) AS n, COUNT(DISTINCT b.source_record_number) AS unique_n,
 MIN(b.source_record_number) AS first_n, MAX(b.source_record_number) AS last_n,
 SUM(CASE WHEN COALESCE(b.source_dataset = w.source_dataset,FALSE) AND COALESCE(b.source_file_name = w.source_file_name,FALSE) AND COALESCE(b.source_file_sha256 = w.source_file_sha256,FALSE) AND COALESCE(b.source_week_start = w.source_week_start,FALSE) AND COALESCE(b.source_week_end_exclusive = w.source_week_end_exclusive,FALSE) AND b.source_version_id IS NOT NULL AND b.source_dataset IS NOT NULL AND b.source_file_name IS NOT NULL AND b.source_url IS NOT NULL AND b.source_file_path IS NOT NULL AND b.source_file_sha256 IS NOT NULL AND b.source_week_start IS NOT NULL AND b.source_week_end_exclusive IS NOT NULL AND b.retrieved_at_utc IS NOT NULL AND b.ingested_at_utc IS NOT NULL AND b.source_record_number IS NOT NULL AND b.source_line_end IS NOT NULL AND b.csv_parse_issues IS NOT NULL AND b.raw_values_json IS NOT NULL AND b.raw_record_json IS NOT NULL AND b.record_sha256 IS NOT NULL THEN 0 ELSE 1 END) AS bad
 FROM _wanted w LEFT JOIN workspace.default.winterops_v2_dev_bronze b ON b.source_version_id=w.source_version_id GROUP BY w.processing_key),
_silver_check AS (
 SELECT w.processing_key, COUNT(s.source_record_number) AS n, COUNT(DISTINCT s.source_record_number) AS unique_n,
 MIN(s.source_record_number) AS first_n, MAX(s.source_record_number) AS last_n,
 SUM(CASE WHEN COALESCE(s.source_version_id = w.source_version_id,FALSE) AND COALESCE(s.source_dataset = w.source_dataset,FALSE) AND COALESCE(s.source_file_name = w.source_file_name,FALSE) AND COALESCE(s.source_file_sha256 = w.source_file_sha256,FALSE) AND COALESCE(s.pipeline_version = w.pipeline_version,FALSE) AND COALESCE(s.quality_policy_sha256 = w.quality_policy_sha256,FALSE) AND COALESCE(s.source_week_start = w.source_week_start,FALSE) AND COALESCE(s.source_week_end_exclusive = w.source_week_end_exclusive,FALSE) AND s.source_version_id IS NOT NULL AND s.source_dataset IS NOT NULL AND s.source_file_name IS NOT NULL AND s.source_url IS NOT NULL AND s.source_file_path IS NOT NULL AND s.source_file_sha256 IS NOT NULL AND s.source_week_start IS NOT NULL AND s.source_week_end_exclusive IS NOT NULL AND s.retrieved_at_utc IS NOT NULL AND s.ingested_at_utc IS NOT NULL AND s.source_record_number IS NOT NULL AND s.source_line_end IS NOT NULL AND s.csv_parse_issues IS NOT NULL AND s.record_sha256 IS NOT NULL AND s.quality_issues IS NOT NULL AND s.quality_warnings IS NOT NULL AND s.quality_status IN ('HEADER','VALID','INVALID')
  AND (s.quality_status<>'VALID' OR (s.truck_id IS NOT NULL AND length(trim(s.truck_id))>0
   AND s.event_time_unzoned >= CAST(w.source_week_start AS TIMESTAMP_NTZ)
   AND s.event_time_unzoned < CAST(w.source_week_end_exclusive AS TIMESTAMP_NTZ)
   AND s.latitude BETWEEN -90 AND 90 AND s.longitude BETWEEN -180 AND 180
   AND s.plow_active IS NOT NULL AND s.spreader_active IS NOT NULL AND s.engine_active IS NOT NULL))
  AND ((s.quality_status='HEADER' AND s.is_repeated_header AND s.quality_issues='REPEATED_HEADER')
   OR (s.quality_status<>'HEADER' AND NOT s.is_repeated_header))
  THEN 0 ELSE 1 END) AS bad
 FROM _wanted w LEFT JOIN workspace.default.winterops_v2_dev_silver s ON s.processing_key=w.processing_key GROUP BY w.processing_key),
_lineage_check AS (SELECT w.processing_key, SUM(CASE WHEN (COALESCE(s.source_version_id=b.source_version_id,FALSE) OR (s.source_version_id IS NULL AND b.source_version_id IS NULL)) AND (COALESCE(s.source_dataset=b.source_dataset,FALSE) OR (s.source_dataset IS NULL AND b.source_dataset IS NULL)) AND (COALESCE(s.source_file_name=b.source_file_name,FALSE) OR (s.source_file_name IS NULL AND b.source_file_name IS NULL)) AND (COALESCE(s.source_url=b.source_url,FALSE) OR (s.source_url IS NULL AND b.source_url IS NULL)) AND (COALESCE(s.source_file_path=b.source_file_path,FALSE) OR (s.source_file_path IS NULL AND b.source_file_path IS NULL)) AND (COALESCE(s.source_file_sha256=b.source_file_sha256,FALSE) OR (s.source_file_sha256 IS NULL AND b.source_file_sha256 IS NULL)) AND (COALESCE(s.source_week_start=b.source_week_start,FALSE) OR (s.source_week_start IS NULL AND b.source_week_start IS NULL)) AND (COALESCE(s.source_week_end_exclusive=b.source_week_end_exclusive,FALSE) OR (s.source_week_end_exclusive IS NULL AND b.source_week_end_exclusive IS NULL)) AND (COALESCE(s.retrieved_at_utc=b.retrieved_at_utc,FALSE) OR (s.retrieved_at_utc IS NULL AND b.retrieved_at_utc IS NULL)) AND (COALESCE(s.ingested_at_utc=b.ingested_at_utc,FALSE) OR (s.ingested_at_utc IS NULL AND b.ingested_at_utc IS NULL)) AND (COALESCE(s.source_record_number=b.source_record_number,FALSE) OR (s.source_record_number IS NULL AND b.source_record_number IS NULL)) AND (COALESCE(s.source_line_end=b.source_line_end,FALSE) OR (s.source_line_end IS NULL AND b.source_line_end IS NULL)) AND (COALESCE(s.csv_parse_issues=b.csv_parse_issues,FALSE) OR (s.csv_parse_issues IS NULL AND b.csv_parse_issues IS NULL)) AND (COALESCE(s.record_sha256=b.record_sha256,FALSE) OR (s.record_sha256 IS NULL AND b.record_sha256 IS NULL)) THEN 0 ELSE 1 END) AS bad
 FROM _wanted w JOIN workspace.default.winterops_v2_dev_bronze b ON b.source_version_id=w.source_version_id
 JOIN workspace.default.winterops_v2_dev_silver s ON s.processing_key=w.processing_key AND s.source_record_number=b.source_record_number GROUP BY w.processing_key),
_frequencies AS (SELECT s.processing_key,s.record_sha256,COUNT(*) AS n
 FROM workspace.default.winterops_v2_dev_silver s JOIN _wanted w ON w.processing_key=s.processing_key GROUP BY s.processing_key,s.record_sha256),
_frequency_check AS (SELECT f.processing_key,SUM(CASE WHEN s.payload_occurrences=f.n
 AND s.has_repeated_payload=(f.n>1) THEN 0 ELSE 1 END) AS bad FROM _frequencies f
 JOIN workspace.default.winterops_v2_dev_silver s ON s.processing_key=f.processing_key AND s.record_sha256=f.record_sha256 GROUP BY f.processing_key),
_selection_gate AS (
 SELECT CASE WHEN COUNT(*)=4 AND SUM(CASE WHEN m.n=1 AND m.good=1
  AND b.n=w.expected_rows AND b.unique_n=w.expected_rows AND b.first_n=1 AND b.last_n=w.expected_rows AND b.bad=0
  AND s.n=w.expected_rows AND s.unique_n=w.expected_rows AND s.first_n=1 AND s.last_n=w.expected_rows AND s.bad=0
  AND l.bad=0 AND f.bad=0
  THEN 0 ELSE 1 END)=0 THEN 1 ELSE CAST(raise_error('V2 Gold selected COMPLETE scope or contract mismatch') AS INT) END AS ok
 FROM _wanted w JOIN _manifest_check m ON m.processing_key=w.processing_key
 JOIN _bronze_check b ON b.processing_key=w.processing_key JOIN _silver_check s ON s.processing_key=w.processing_key
 LEFT JOIN _lineage_check l ON l.processing_key=w.processing_key LEFT JOIN _frequency_check f ON f.processing_key=w.processing_key),
_selected AS (SELECT s.*, w.original_csv_volume_path, w.long_gap_seconds
 FROM workspace.default.winterops_v2_dev_silver s JOIN _wanted w ON s.processing_key=w.processing_key
 CROSS JOIN _selection_gate g WHERE g.ok=1),
_valid AS (SELECT *, CAST(substring(CAST(event_time_unzoned AS STRING),1,13) || ':00:00' AS TIMESTAMP_NTZ) AS source_local_naive_hour, CAST(event_time_unzoned AS DATE) AS source_local_naive_day,
 COUNT(*) OVER (PARTITION BY processing_key,record_sha256) AS valid_payload_occurrences
 FROM _selected WHERE quality_status='VALID'),
_hourly AS (SELECT source_dataset, source_file_name, source_file_sha256, source_version_id, processing_key, pipeline_version, quality_policy_sha256, source_week_start, source_week_end_exclusive, original_csv_volume_path, source_local_naive_hour, COUNT(*) AS observation_count,
 COUNT(CASE WHEN plow_active THEN 1 END) AS plow_active_observations,
 COUNT(CASE WHEN spreader_active THEN 1 END) AS spreader_active_observations,
 COUNT(CASE WHEN plow_active AND NOT spreader_active THEN 1 END) AS plow_only_observations,
 COUNT(CASE WHEN spreader_active AND NOT plow_active THEN 1 END) AS spreader_only_observations,
 COUNT(CASE WHEN plow_active AND spreader_active THEN 1 END) AS both_active_observations,
 COUNT(CASE WHEN NOT plow_active AND NOT spreader_active THEN 1 END) AS neither_active_observations,
 COUNT(CASE WHEN NOT engine_active THEN 1 END) AS engine_off_observations,
 COUNT(CASE WHEN NOT engine_active AND (plow_active OR spreader_active) THEN 1 END) AS engine_off_with_equipment_flag_observations,
 COUNT(CASE WHEN valid_payload_occurrences>1 THEN 1 END) AS repeated_valid_payload_observations,
 COUNT(DISTINCT truck_id) AS observed_identifier_count FROM _valid GROUP BY source_dataset, source_file_name, source_file_sha256, source_version_id, processing_key, pipeline_version, quality_policy_sha256, source_week_start, source_week_end_exclusive, original_csv_volume_path, source_local_naive_hour),
_day_counts AS (SELECT source_dataset, source_file_name, source_file_sha256, source_version_id, processing_key, pipeline_version, quality_policy_sha256, source_week_start, source_week_end_exclusive, original_csv_volume_path, source_local_naive_day, COUNT(*) AS observation_count,
 COUNT(CASE WHEN plow_active THEN 1 END) AS plow_active_observations,
 COUNT(CASE WHEN spreader_active THEN 1 END) AS spreader_active_observations,
 COUNT(CASE WHEN plow_active AND NOT spreader_active THEN 1 END) AS plow_only_observations,
 COUNT(CASE WHEN spreader_active AND NOT plow_active THEN 1 END) AS spreader_only_observations,
 COUNT(CASE WHEN plow_active AND spreader_active THEN 1 END) AS both_active_observations,
 COUNT(CASE WHEN NOT plow_active AND NOT spreader_active THEN 1 END) AS neither_active_observations,
 COUNT(CASE WHEN NOT engine_active THEN 1 END) AS engine_off_observations,
 COUNT(CASE WHEN NOT engine_active AND (plow_active OR spreader_active) THEN 1 END) AS engine_off_with_equipment_flag_observations,
 COUNT(CASE WHEN valid_payload_occurrences>1 THEN 1 END) AS repeated_valid_payload_observations,
 COUNT(DISTINCT truck_id) AS observed_identifier_count,
 COUNT(DISTINCT source_local_naive_hour) AS hours_containing_telemetry FROM _valid GROUP BY source_dataset, source_file_name, source_file_sha256, source_version_id, processing_key, pipeline_version, quality_policy_sha256, source_week_start, source_week_end_exclusive, original_csv_volume_path, source_local_naive_day),
_day_peaks AS (SELECT processing_key,CAST(source_local_naive_hour AS DATE) AS day,MAX(observed_identifier_count) AS maximum_hourly_identifiers
 FROM _hourly GROUP BY processing_key,CAST(source_local_naive_hour AS DATE)),
_daily AS (SELECT a.*,p.maximum_hourly_identifiers FROM _day_counts a JOIN _day_peaks p
 ON a.processing_key=p.processing_key AND a.source_local_naive_day=p.day),
_times AS (SELECT processing_key, source_record_number, long_gap_seconds,
 (CAST(datediff(CAST(substring(CAST(event_time_unzoned AS STRING), 1, 10) AS DATE), DATE '2000-01-01') AS BIGINT) * 86400000000 + CAST(substring(CAST(event_time_unzoned AS STRING), 12, 2) AS BIGINT) * 3600000000 + CAST(substring(CAST(event_time_unzoned AS STRING), 15, 2) AS BIGINT) * 60000000 + CAST(CAST(substring(CAST(event_time_unzoned AS STRING), 18, 9) AS DECIMAL(8,6)) * 1000000 AS BIGINT)) AS clock_us,
 LAG((CAST(datediff(CAST(substring(CAST(event_time_unzoned AS STRING), 1, 10) AS DATE), DATE '2000-01-01') AS BIGINT) * 86400000000 + CAST(substring(CAST(event_time_unzoned AS STRING), 12, 2) AS BIGINT) * 3600000000 + CAST(substring(CAST(event_time_unzoned AS STRING), 15, 2) AS BIGINT) * 60000000 + CAST(CAST(substring(CAST(event_time_unzoned AS STRING), 18, 9) AS DECIMAL(8,6)) * 1000000 AS BIGINT))) OVER (PARTITION BY processing_key,truck_id ORDER BY event_time_unzoned,source_record_number) AS prior_us FROM _valid),
_gaps AS (SELECT processing_key, COUNT(prior_us) AS consecutive_timestamp_pairs,
 COUNT(CASE WHEN clock_us=prior_us THEN 1 END) AS zero_gap_pairs,
 COUNT(CASE WHEN clock_us-prior_us>long_gap_seconds*1000000 THEN 1 END) AS long_gap_pairs,
 CAST(MAX(clock_us-prior_us) AS DOUBLE)/1000000 AS maximum_source_clock_gap_seconds FROM _times GROUP BY processing_key),
_payloads AS (SELECT processing_key,record_sha256,COUNT(*) AS n FROM _valid GROUP BY processing_key,record_sha256),
_duplicates AS (SELECT processing_key,COUNT(CASE WHEN n>1 THEN 1 END) AS repeated_valid_payload_groups,
 SUM(n-1) AS excess_valid_payload_observations FROM _payloads GROUP BY processing_key),
_valid_week AS (SELECT source_dataset, source_file_name, source_file_sha256, source_version_id, processing_key, pipeline_version, quality_policy_sha256, source_week_start, source_week_end_exclusive, original_csv_volume_path, COUNT(*) AS observation_count,
 COUNT(CASE WHEN plow_active THEN 1 END) AS plow_active_observations,
 COUNT(CASE WHEN spreader_active THEN 1 END) AS spreader_active_observations,
 COUNT(CASE WHEN plow_active AND NOT spreader_active THEN 1 END) AS plow_only_observations,
 COUNT(CASE WHEN spreader_active AND NOT plow_active THEN 1 END) AS spreader_only_observations,
 COUNT(CASE WHEN plow_active AND spreader_active THEN 1 END) AS both_active_observations,
 COUNT(CASE WHEN NOT plow_active AND NOT spreader_active THEN 1 END) AS neither_active_observations,
 COUNT(CASE WHEN NOT engine_active THEN 1 END) AS engine_off_observations,
 COUNT(CASE WHEN NOT engine_active AND (plow_active OR spreader_active) THEN 1 END) AS engine_off_with_equipment_flag_observations,
 COUNT(CASE WHEN valid_payload_occurrences>1 THEN 1 END) AS repeated_valid_payload_observations,
 COUNT(DISTINCT truck_id) AS observed_identifier_count, COUNT(DISTINCT source_local_naive_hour) AS hours_containing_telemetry,
 COUNT(DISTINCT source_local_naive_day) AS days_containing_telemetry FROM _valid GROUP BY source_dataset, source_file_name, source_file_sha256, source_version_id, processing_key, pipeline_version, quality_policy_sha256, source_week_start, source_week_end_exclusive, original_csv_volume_path),
_quality AS (SELECT processing_key,COUNT(*) AS silver_rows,
 COUNT(CASE WHEN quality_status='HEADER' THEN 1 END) AS header_rows,
 COUNT(CASE WHEN quality_status='VALID' THEN 1 END) AS valid_rows,
 COUNT(CASE WHEN quality_status='INVALID' THEN 1 END) AS invalid_rows,
 COUNT(CASE WHEN quality_status<>'VALID' THEN 1 END) AS quarantine_rows,
 COUNT(CASE WHEN quality_status='INVALID' AND (quality_issues LIKE '%INVALID_LATITUDE%' OR quality_issues LIKE '%INVALID_LONGITUDE%') THEN 1 END) AS invalid_coordinate_rows,
 COUNT(CASE WHEN quality_status<>'HEADER' AND quality_warnings LIKE '%OUTSIDE_REVIEW_ENVELOPE%' THEN 1 END) AS outside_review_envelope_rows
 FROM _selected GROUP BY processing_key),
_week_peaks AS (SELECT processing_key,MAX(observed_identifier_count) AS peak FROM _hourly GROUP BY processing_key),
_weekly AS (SELECT w.source_dataset, w.source_file_name, w.source_file_sha256, w.source_version_id, w.processing_key, w.pipeline_version, w.quality_policy_sha256, w.source_week_start, w.source_week_end_exclusive, w.original_csv_volume_path, w.expected_rows AS bronze_rows,
 q.silver_rows,q.header_rows,q.valid_rows,q.invalid_rows,q.quarantine_rows,q.invalid_coordinate_rows,q.outside_review_envelope_rows,
 COALESCE(v.observation_count,0) AS observation_count, COALESCE(v.plow_active_observations,0) AS plow_active_observations, COALESCE(v.spreader_active_observations,0) AS spreader_active_observations, COALESCE(v.plow_only_observations,0) AS plow_only_observations, COALESCE(v.spreader_only_observations,0) AS spreader_only_observations, COALESCE(v.both_active_observations,0) AS both_active_observations, COALESCE(v.neither_active_observations,0) AS neither_active_observations, COALESCE(v.engine_off_observations,0) AS engine_off_observations, COALESCE(v.engine_off_with_equipment_flag_observations,0) AS engine_off_with_equipment_flag_observations, COALESCE(v.repeated_valid_payload_observations,0) AS repeated_valid_payload_observations, COALESCE(v.observed_identifier_count,0) AS observed_identifier_count, COALESCE(v.hours_containing_telemetry,0) AS hours_containing_telemetry, COALESCE(v.days_containing_telemetry,0) AS days_containing_telemetry,
 COALESCE(p.peak,0) AS maximum_hourly_identifiers,
 COALESCE(d.repeated_valid_payload_groups,0) AS repeated_valid_payload_groups,
 COALESCE(d.excess_valid_payload_observations,0) AS excess_valid_payload_observations,
 COALESCE(g.consecutive_timestamp_pairs,0) AS consecutive_timestamp_pairs, COALESCE(g.zero_gap_pairs,0) AS zero_gap_pairs,
 COALESCE(g.long_gap_pairs,0) AS long_gap_pairs,g.maximum_source_clock_gap_seconds
 FROM _wanted w CROSS JOIN _selection_gate gate JOIN _quality q ON q.processing_key=w.processing_key
 LEFT JOIN _valid_week v ON v.processing_key=w.processing_key LEFT JOIN _duplicates d ON d.processing_key=w.processing_key
 LEFT JOIN _gaps g ON g.processing_key=w.processing_key LEFT JOIN _week_peaks p ON p.processing_key=w.processing_key WHERE gate.ok=1)
SELECT * FROM _hourly ORDER BY source_week_start, source_local_naive_hour;

-- READ-ONLY CANDIDATE: cell_hour
WITH _wanted AS (SELECT 'windsor_snowplow_activity' AS source_dataset, 'snowplow-2026-01-05_2026-01-11.csv' AS source_file_name, '271c9339a42043f441b6c17e82dd309609db4b20e9953b9f368a95ec472d763d' AS source_file_sha256, '8ccb2a2dd5ec057361cf6d7cc7193b5acbdd858b84102ba550a92febe9bb4ed1' AS source_version_id, 'f07ba6a0ad499a9baf53d2f7c46df09607523371428791593143a29b56f6b466' AS processing_key, 'windsor-foundation-v2.1' AS pipeline_version, '03829a2ce3b308a45e0205ca12a5288e5cb08b97189cf20b69c0e37d4c546e08' AS quality_policy_sha256, DATE '2026-01-05' AS source_week_start, DATE '2026-01-12' AS source_week_end_exclusive, '/Volumes/workspace/default/winterops_raw/original_csv/snowplow-2026-01-05_2026-01-11.csv/271c9339a42043f441b6c17e82dd309609db4b20e9953b9f368a95ec472d763d/snowplow-2026-01-05_2026-01-11.csv' AS original_csv_volume_path, 2810 AS expected_rows, 1800 AS long_gap_seconds, '{"review_lat_min": 42.1, "review_lat_max": 42.5, "review_lon_min": -83.3, "review_lon_max": -82.6, "nominal_interval_seconds": 15, "long_gap_seconds": 1800, "dense_hour_observations": 1000}' AS policy_json
UNION ALL
SELECT 'windsor_snowplow_activity' AS source_dataset, 'snowplow-2026-01-12_2026-01-18.csv' AS source_file_name, 'f5d7633c910e1ad6be23b4111445bf0bc14fe2071c6ea0f0d4cd456295ea9e94' AS source_file_sha256, '73e9338d8a7e78ba01827806b2172a715a50b90c819959ba1ade17632f2d4433' AS source_version_id, '5e478fdced5a0ac67865413d68b9359a97fffd980a2a6dee976d6ab984c599be' AS processing_key, 'windsor-foundation-v2.1' AS pipeline_version, '03829a2ce3b308a45e0205ca12a5288e5cb08b97189cf20b69c0e37d4c546e08' AS quality_policy_sha256, DATE '2026-01-12' AS source_week_start, DATE '2026-01-19' AS source_week_end_exclusive, '/Volumes/workspace/default/winterops_raw/snowplow-2026-01-12_2026-01-18.csv' AS original_csv_volume_path, 110337 AS expected_rows, 1800 AS long_gap_seconds, '{"review_lat_min": 42.1, "review_lat_max": 42.5, "review_lon_min": -83.3, "review_lon_max": -82.6, "nominal_interval_seconds": 15, "long_gap_seconds": 1800, "dense_hour_observations": 1000}' AS policy_json
UNION ALL
SELECT 'windsor_snowplow_activity' AS source_dataset, 'snowplow-2026-01-19_2026-01-25.csv' AS source_file_name, 'b78d0fb82c8e3c5204ee79eea7a03417cd54bc935ead9b04577a30dc908c7c49' AS source_file_sha256, 'd2a89e9a8582aefdca97264a482d51a6116b827a71f0241a0e1f0149ed14f97a' AS source_version_id, 'bb478f6992172da1298db36c3a5d92aa4c349769064ec66002f347a2458e415c' AS processing_key, 'windsor-foundation-v2.1' AS pipeline_version, '03829a2ce3b308a45e0205ca12a5288e5cb08b97189cf20b69c0e37d4c546e08' AS quality_policy_sha256, DATE '2026-01-19' AS source_week_start, DATE '2026-01-26' AS source_week_end_exclusive, '/Volumes/workspace/default/winterops_raw/original_csv/snowplow-2026-01-19_2026-01-25.csv/b78d0fb82c8e3c5204ee79eea7a03417cd54bc935ead9b04577a30dc908c7c49/snowplow-2026-01-19_2026-01-25.csv' AS original_csv_volume_path, 118159 AS expected_rows, 1800 AS long_gap_seconds, '{"review_lat_min": 42.1, "review_lat_max": 42.5, "review_lon_min": -83.3, "review_lon_max": -82.6, "nominal_interval_seconds": 15, "long_gap_seconds": 1800, "dense_hour_observations": 1000}' AS policy_json
UNION ALL
SELECT 'windsor_snowplow_activity' AS source_dataset, 'snowplow-2026-01-26_2026-02-01.csv' AS source_file_name, 'cebcbd758e2a0cf5d0624ecf9cd6993244e7becdd1846a4057b4f63be22ed6c6' AS source_file_sha256, 'ad5c201ccee0b96b2f4907f10ee3a064a7562d17429146d2205b1eaca46fdc00' AS source_version_id, '9c8e1b6f640e75c21f1c9f429ec670c389bf178269afd2f1543b2ae759c3eeae' AS processing_key, 'windsor-foundation-v2.1' AS pipeline_version, '03829a2ce3b308a45e0205ca12a5288e5cb08b97189cf20b69c0e37d4c546e08' AS quality_policy_sha256, DATE '2026-01-26' AS source_week_start, DATE '2026-02-02' AS source_week_end_exclusive, '/Volumes/workspace/default/winterops_raw/original_csv/snowplow-2026-01-26_2026-02-01.csv/cebcbd758e2a0cf5d0624ecf9cd6993244e7becdd1846a4057b4f63be22ed6c6/snowplow-2026-01-26_2026-02-01.csv' AS original_csv_volume_path, 66850 AS expected_rows, 1800 AS long_gap_seconds, '{"review_lat_min": 42.1, "review_lat_max": 42.5, "review_lon_min": -83.3, "review_lon_max": -82.6, "nominal_interval_seconds": 15, "long_gap_seconds": 1800, "dense_hour_observations": 1000}' AS policy_json),
_manifest_check AS (
 SELECT w.processing_key, COUNT(m.processing_key) AS n,
 SUM(CASE WHEN m.status='COMPLETE' AND m.last_successful_stage='COMPLETE' AND m.error_code IS NULL
  AND m.source_version_id=w.source_version_id AND m.source_file_name=w.source_file_name
  AND m.source_file_sha256=w.source_file_sha256 AND m.policy_json=w.policy_json
  AND m.bronze_rows=w.expected_rows AND m.silver_rows=w.expected_rows THEN 1 ELSE 0 END) AS good
 FROM _wanted w LEFT JOIN workspace.default.winterops_v2_dev_manifest m ON m.processing_key=w.processing_key GROUP BY w.processing_key),
_bronze_check AS (
 SELECT w.processing_key, COUNT(b.source_record_number) AS n, COUNT(DISTINCT b.source_record_number) AS unique_n,
 MIN(b.source_record_number) AS first_n, MAX(b.source_record_number) AS last_n,
 SUM(CASE WHEN COALESCE(b.source_dataset = w.source_dataset,FALSE) AND COALESCE(b.source_file_name = w.source_file_name,FALSE) AND COALESCE(b.source_file_sha256 = w.source_file_sha256,FALSE) AND COALESCE(b.source_week_start = w.source_week_start,FALSE) AND COALESCE(b.source_week_end_exclusive = w.source_week_end_exclusive,FALSE) AND b.source_version_id IS NOT NULL AND b.source_dataset IS NOT NULL AND b.source_file_name IS NOT NULL AND b.source_url IS NOT NULL AND b.source_file_path IS NOT NULL AND b.source_file_sha256 IS NOT NULL AND b.source_week_start IS NOT NULL AND b.source_week_end_exclusive IS NOT NULL AND b.retrieved_at_utc IS NOT NULL AND b.ingested_at_utc IS NOT NULL AND b.source_record_number IS NOT NULL AND b.source_line_end IS NOT NULL AND b.csv_parse_issues IS NOT NULL AND b.raw_values_json IS NOT NULL AND b.raw_record_json IS NOT NULL AND b.record_sha256 IS NOT NULL THEN 0 ELSE 1 END) AS bad
 FROM _wanted w LEFT JOIN workspace.default.winterops_v2_dev_bronze b ON b.source_version_id=w.source_version_id GROUP BY w.processing_key),
_silver_check AS (
 SELECT w.processing_key, COUNT(s.source_record_number) AS n, COUNT(DISTINCT s.source_record_number) AS unique_n,
 MIN(s.source_record_number) AS first_n, MAX(s.source_record_number) AS last_n,
 SUM(CASE WHEN COALESCE(s.source_version_id = w.source_version_id,FALSE) AND COALESCE(s.source_dataset = w.source_dataset,FALSE) AND COALESCE(s.source_file_name = w.source_file_name,FALSE) AND COALESCE(s.source_file_sha256 = w.source_file_sha256,FALSE) AND COALESCE(s.pipeline_version = w.pipeline_version,FALSE) AND COALESCE(s.quality_policy_sha256 = w.quality_policy_sha256,FALSE) AND COALESCE(s.source_week_start = w.source_week_start,FALSE) AND COALESCE(s.source_week_end_exclusive = w.source_week_end_exclusive,FALSE) AND s.source_version_id IS NOT NULL AND s.source_dataset IS NOT NULL AND s.source_file_name IS NOT NULL AND s.source_url IS NOT NULL AND s.source_file_path IS NOT NULL AND s.source_file_sha256 IS NOT NULL AND s.source_week_start IS NOT NULL AND s.source_week_end_exclusive IS NOT NULL AND s.retrieved_at_utc IS NOT NULL AND s.ingested_at_utc IS NOT NULL AND s.source_record_number IS NOT NULL AND s.source_line_end IS NOT NULL AND s.csv_parse_issues IS NOT NULL AND s.record_sha256 IS NOT NULL AND s.quality_issues IS NOT NULL AND s.quality_warnings IS NOT NULL AND s.quality_status IN ('HEADER','VALID','INVALID')
  AND (s.quality_status<>'VALID' OR (s.truck_id IS NOT NULL AND length(trim(s.truck_id))>0
   AND s.event_time_unzoned >= CAST(w.source_week_start AS TIMESTAMP_NTZ)
   AND s.event_time_unzoned < CAST(w.source_week_end_exclusive AS TIMESTAMP_NTZ)
   AND s.latitude BETWEEN -90 AND 90 AND s.longitude BETWEEN -180 AND 180
   AND s.plow_active IS NOT NULL AND s.spreader_active IS NOT NULL AND s.engine_active IS NOT NULL))
  AND ((s.quality_status='HEADER' AND s.is_repeated_header AND s.quality_issues='REPEATED_HEADER')
   OR (s.quality_status<>'HEADER' AND NOT s.is_repeated_header))
  THEN 0 ELSE 1 END) AS bad
 FROM _wanted w LEFT JOIN workspace.default.winterops_v2_dev_silver s ON s.processing_key=w.processing_key GROUP BY w.processing_key),
_lineage_check AS (SELECT w.processing_key, SUM(CASE WHEN (COALESCE(s.source_version_id=b.source_version_id,FALSE) OR (s.source_version_id IS NULL AND b.source_version_id IS NULL)) AND (COALESCE(s.source_dataset=b.source_dataset,FALSE) OR (s.source_dataset IS NULL AND b.source_dataset IS NULL)) AND (COALESCE(s.source_file_name=b.source_file_name,FALSE) OR (s.source_file_name IS NULL AND b.source_file_name IS NULL)) AND (COALESCE(s.source_url=b.source_url,FALSE) OR (s.source_url IS NULL AND b.source_url IS NULL)) AND (COALESCE(s.source_file_path=b.source_file_path,FALSE) OR (s.source_file_path IS NULL AND b.source_file_path IS NULL)) AND (COALESCE(s.source_file_sha256=b.source_file_sha256,FALSE) OR (s.source_file_sha256 IS NULL AND b.source_file_sha256 IS NULL)) AND (COALESCE(s.source_week_start=b.source_week_start,FALSE) OR (s.source_week_start IS NULL AND b.source_week_start IS NULL)) AND (COALESCE(s.source_week_end_exclusive=b.source_week_end_exclusive,FALSE) OR (s.source_week_end_exclusive IS NULL AND b.source_week_end_exclusive IS NULL)) AND (COALESCE(s.retrieved_at_utc=b.retrieved_at_utc,FALSE) OR (s.retrieved_at_utc IS NULL AND b.retrieved_at_utc IS NULL)) AND (COALESCE(s.ingested_at_utc=b.ingested_at_utc,FALSE) OR (s.ingested_at_utc IS NULL AND b.ingested_at_utc IS NULL)) AND (COALESCE(s.source_record_number=b.source_record_number,FALSE) OR (s.source_record_number IS NULL AND b.source_record_number IS NULL)) AND (COALESCE(s.source_line_end=b.source_line_end,FALSE) OR (s.source_line_end IS NULL AND b.source_line_end IS NULL)) AND (COALESCE(s.csv_parse_issues=b.csv_parse_issues,FALSE) OR (s.csv_parse_issues IS NULL AND b.csv_parse_issues IS NULL)) AND (COALESCE(s.record_sha256=b.record_sha256,FALSE) OR (s.record_sha256 IS NULL AND b.record_sha256 IS NULL)) THEN 0 ELSE 1 END) AS bad
 FROM _wanted w JOIN workspace.default.winterops_v2_dev_bronze b ON b.source_version_id=w.source_version_id
 JOIN workspace.default.winterops_v2_dev_silver s ON s.processing_key=w.processing_key AND s.source_record_number=b.source_record_number GROUP BY w.processing_key),
_frequencies AS (SELECT s.processing_key,s.record_sha256,COUNT(*) AS n
 FROM workspace.default.winterops_v2_dev_silver s JOIN _wanted w ON w.processing_key=s.processing_key GROUP BY s.processing_key,s.record_sha256),
_frequency_check AS (SELECT f.processing_key,SUM(CASE WHEN s.payload_occurrences=f.n
 AND s.has_repeated_payload=(f.n>1) THEN 0 ELSE 1 END) AS bad FROM _frequencies f
 JOIN workspace.default.winterops_v2_dev_silver s ON s.processing_key=f.processing_key AND s.record_sha256=f.record_sha256 GROUP BY f.processing_key),
_selection_gate AS (
 SELECT CASE WHEN COUNT(*)=4 AND SUM(CASE WHEN m.n=1 AND m.good=1
  AND b.n=w.expected_rows AND b.unique_n=w.expected_rows AND b.first_n=1 AND b.last_n=w.expected_rows AND b.bad=0
  AND s.n=w.expected_rows AND s.unique_n=w.expected_rows AND s.first_n=1 AND s.last_n=w.expected_rows AND s.bad=0
  AND l.bad=0 AND f.bad=0
  THEN 0 ELSE 1 END)=0 THEN 1 ELSE CAST(raise_error('V2 Gold selected COMPLETE scope or contract mismatch') AS INT) END AS ok
 FROM _wanted w JOIN _manifest_check m ON m.processing_key=w.processing_key
 JOIN _bronze_check b ON b.processing_key=w.processing_key JOIN _silver_check s ON s.processing_key=w.processing_key
 LEFT JOIN _lineage_check l ON l.processing_key=w.processing_key LEFT JOIN _frequency_check f ON f.processing_key=w.processing_key),
_selected AS (SELECT s.*, w.original_csv_volume_path, w.long_gap_seconds
 FROM workspace.default.winterops_v2_dev_silver s JOIN _wanted w ON s.processing_key=w.processing_key
 CROSS JOIN _selection_gate g WHERE g.ok=1),
_valid AS (SELECT *, CAST(substring(CAST(event_time_unzoned AS STRING),1,13) || ':00:00' AS TIMESTAMP_NTZ) AS source_local_naive_hour, CAST(event_time_unzoned AS DATE) AS source_local_naive_day,
 COUNT(*) OVER (PARTITION BY processing_key,record_sha256) AS valid_payload_occurrences
 FROM _selected WHERE quality_status='VALID'),
_cells AS (SELECT *,
 'q25:' || CAST(CAST(FLOOR(latitude*4) AS INT) AS STRING) || ':' ||
 CAST(CAST(FLOOR(longitude*4) AS INT) AS STRING) AS spatial_bin FROM _valid)
SELECT source_dataset, source_file_name, source_file_sha256, source_version_id, processing_key, pipeline_version, quality_policy_sha256, source_week_start, source_week_end_exclusive, original_csv_volume_path, source_local_naive_hour, spatial_bin, COUNT(*) AS observation_count,
 COUNT(CASE WHEN plow_active THEN 1 END) AS plow_active_observations,
 COUNT(CASE WHEN spreader_active THEN 1 END) AS spreader_active_observations,
 COUNT(CASE WHEN plow_active AND NOT spreader_active THEN 1 END) AS plow_only_observations,
 COUNT(CASE WHEN spreader_active AND NOT plow_active THEN 1 END) AS spreader_only_observations,
 COUNT(CASE WHEN plow_active AND spreader_active THEN 1 END) AS both_active_observations,
 COUNT(CASE WHEN NOT plow_active AND NOT spreader_active THEN 1 END) AS neither_active_observations,
 COUNT(CASE WHEN NOT engine_active THEN 1 END) AS engine_off_observations,
 COUNT(CASE WHEN NOT engine_active AND (plow_active OR spreader_active) THEN 1 END) AS engine_off_with_equipment_flag_observations,
 COUNT(CASE WHEN valid_payload_occurrences>1 THEN 1 END) AS repeated_valid_payload_observations,
 COUNT(DISTINCT truck_id) AS observed_identifier_count,
 COUNT(CASE WHEN quality_warnings LIKE '%OUTSIDE_REVIEW_ENVELOPE%' THEN 1 END) AS outside_source_review_observations
FROM _cells GROUP BY source_dataset, source_file_name, source_file_sha256, source_version_id, processing_key, pipeline_version, quality_policy_sha256, source_week_start, source_week_end_exclusive, original_csv_volume_path, source_local_naive_hour, spatial_bin
ORDER BY processing_key, spatial_bin, source_local_naive_hour;