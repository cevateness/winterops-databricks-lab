-- READ ONLY. Requires the private validated cell_weather relation; no native binding exists.
WITH distinct_grid_hours AS (
 SELECT DISTINCT processing_key, source_local_hour, timezone_hypothesis,
 weather_snapshot_id, grid_id, temperature_valid_time_utc, accumulation_valid_time_utc,
 temperature_2m_c, precipitation_activity_hour_mm, snowfall_activity_hour_cm,
 precipitation_antecedent_mm, snowfall_antecedent_cm FROM cell_weather)
SELECT processing_key, source_local_hour, timezone_hypothesis, weather_snapshot_id,
 COUNT(*) AS sampled_grid_hours, AVG(temperature_2m_c) AS temperature_2m_c_mean,
 MIN(temperature_2m_c) AS temperature_2m_c_min, MAX(temperature_2m_c) AS temperature_2m_c_max,
 AVG(precipitation_activity_hour_mm) AS precipitation_activity_hour_mm_mean,
 MAX(precipitation_activity_hour_mm) AS precipitation_activity_hour_mm_max,
 AVG(snowfall_activity_hour_cm) AS snowfall_activity_hour_cm_mean,
 AVG(precipitation_antecedent_mm) AS precipitation_antecedent_mm_mean,
 AVG(snowfall_antecedent_cm) AS snowfall_antecedent_cm_mean
FROM distinct_grid_hours
GROUP BY processing_key, source_local_hour, timezone_hypothesis, weather_snapshot_id;
