WITH legacy AS (
 SELECT COUNT(*) AS legacy_hourly_rows,SUM(observation_count) AS legacy_observations,
 SUM(plow_active_observation_count) AS legacy_plow_observations,
 SUM(spreader_active_observation_count) AS legacy_spreader_observations
 FROM workspace.default.winterops_gold_windsor_hourly_observations),
 weekly AS (SELECT source_week_start,bronze_rows,silver_rows,header_rows,valid_rows,invalid_rows,
 observation_count,plow_active_observations,spreader_active_observations,
 hours_containing_telemetry,days_containing_telemetry
 FROM workspace.default.winterops_v2_gold_weekly_quality)
SELECT weekly.*,legacy.* FROM weekly CROSS JOIN legacy ORDER BY source_week_start
