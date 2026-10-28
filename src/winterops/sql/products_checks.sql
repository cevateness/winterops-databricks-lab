_product_daily AS ($q_daily_activity),
_product_hourly_composition AS ($q_equipment_hourly),
_product_daily_composition AS ($q_equipment_daily),
_product_overview AS ($q_fleet_overview),
_product_participation AS ($q_fleet_daily_participation),
_product_frequency AS ($q_fleet_observation_frequency),
_product_gaps AS ($q_fleet_gap_distribution),
_product_reporting_days AS ($q_fleet_reporting_days),
_composition_totals AS (
  SELECT COUNT(*) AS bad_rows FROM (
    SELECT observation_count, plow_only_observations, spreader_only_observations,
           both_active_observations, neither_active_observations, engine_off_observations,
           engine_off_with_equipment_flag_observations FROM _product_hourly_composition
    UNION ALL
    SELECT observation_count, plow_only_observations, spreader_only_observations,
           both_active_observations, neither_active_observations, engine_off_observations,
           engine_off_with_equipment_flag_observations FROM _product_daily_composition
  ) c WHERE plow_only_observations + spreader_only_observations + both_active_observations
              + neither_active_observations <> observation_count
         OR engine_off_with_equipment_flag_observations > engine_off_observations
         OR engine_off_with_equipment_flag_observations > plow_only_observations + spreader_only_observations + both_active_observations
), _daily_mismatches AS (
  SELECT COUNT(*) AS n FROM _product_daily d FULL OUTER JOIN _product_daily_composition c
  ON d.source_local_naive_day = c.source_local_naive_day
  WHERE d.source_local_naive_day IS NULL OR c.source_local_naive_day IS NULL
     OR d.observation_count <> c.observation_count
     OR d.plow_active_observations <> c.plow_only_observations + c.both_active_observations
     OR d.spreader_active_observations <> c.spreader_only_observations + c.both_active_observations
)
SELECT assert_true((SELECT COALESCE(SUM(observation_count), 0) FROM _product_daily) = $valid_rows
         AND (SELECT SUM(plow_active_observations) FROM _product_daily) = $plow_rows
         AND (SELECT SUM(spreader_active_observations) FROM _product_daily) = $spreader_rows
         AND (SELECT SUM(hours_containing_telemetry) FROM _product_daily) = (SELECT COUNT(*) FROM _gold)
         AND (SELECT SUM(observation_count) FROM _product_hourly_composition) = $valid_rows
         AND (SELECT bad_rows FROM _composition_totals) = 0
         AND (SELECT n FROM _daily_mismatches) = 0,
         'Daily/hourly activity and equipment products do not reconcile') AS activity_composition_check,
       assert_true(f.observed_identifier_count = $valid_trucks AND f.observation_count = $valid_rows
         AND f.consecutive_timestamp_pairs = f.observation_count - f.observed_identifier_count
         AND (SELECT COALESCE(SUM(consecutive_timestamp_pairs), 0) FROM _product_gaps) = f.consecutive_timestamp_pairs
         AND (SELECT SUM(identifier_count) FROM _product_frequency) = f.observed_identifier_count
         AND (SELECT SUM(observation_count) FROM _product_frequency) = f.observation_count
         AND (SELECT SUM(identifier_count) FROM _product_reporting_days) = f.observed_identifier_count
         AND (SELECT SUM(observation_count) FROM _product_reporting_days) = f.observation_count
         AND (SELECT SUM(observation_count) FROM _product_participation) = f.observation_count,
         'Fleet diagnostic products do not reconcile') AS fleet_check
FROM _product_overview f
