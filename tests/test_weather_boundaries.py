"""Explicit collection units, spatial edge assignment and exclusion accounting."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from weather_activity import synthetic_inputs, synthetic_snapshots
from winterops.weather_demand import DemandPlan, aggregate_activity, matched_projection, weather_catalog


class WeatherBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.scope, self.raw = synthetic_inputs()

    def rows_at(self, points):
        return [dict(self.raw[0], source_record_number=i + 1, latitude=lat, longitude=lon)
                for i, (lat, lon) in enumerate(points)]

    def test_collection_size_is_record_count_not_runtime_or_request_count(self):
        hours, _ = aggregate_activity(self.raw, [self.scope])
        plan = DemandPlan(hours).public_contract()
        self.assertEqual(plan['request_count'], 3)
        self.assertEqual(plan['requested_hourly_location_records'], 120)
        self.assertEqual(plan['requested_measurement_values'], 360)
        self.assertIsNone(plan['estimated_runtime_seconds'])
        self.assertIn('NOT_EXECUTION_HOURS', plan['collection_size_unit'])

    def test_points_either_side_of_internal_edges_are_assigned_once(self):
        epsilon = 1e-9
        points = [(lat, lon) for lat in (42.25 - epsilon, 42.25, 42.25 + epsilon)
                  for lon in (-83.0 - epsilon, -83.0, -83.0 + epsilon)]
        hours, audit = aggregate_activity(self.rows_at(points), [self.scope], minimum_observations=1)
        self.assertEqual(sum(a.observation_count for a in hours), 9)
        self.assertEqual(len(hours), 4)
        self.assertEqual(audit['outside_review_rows'], 0)
        self.assertEqual(audit['coverage_accounting']['hull_or_bbox_clipped_rows'], 0)

    def test_geographic_review_edges_are_inclusive_just_outside_is_visible(self):
        p, e = self.scope.policy, 1e-9
        edges = [(p.review_lat_min, -83), (p.review_lat_max, -83),
                 (42.3, p.review_lon_min), (42.3, p.review_lon_max)]
        outside = [(p.review_lat_min - e, -83), (p.review_lat_max + e, -83),
                   (42.3, p.review_lon_min - e), (42.3, p.review_lon_max + e)]
        hours, audit = aggregate_activity(self.rows_at(edges + outside), [self.scope], minimum_observations=1)
        self.assertEqual(sum(a.observation_count for a in hours), 4)
        self.assertEqual((audit['outside_review_rows'], audit['outside_near_review_rows']), (4, 4))
        self.assertEqual(audit['coverage_accounting']['geographic_status'], 'REVIEW_EXCLUDED_COORDINATES')
        self.assertTrue(audit['coverage_accounting']['all_input_rows_accounted_for'])

    def test_new_valid_points_outside_old_footprint_expand_plan_instead_of_being_clipped(self):
        old_hours, _ = aggregate_activity(self.raw, [self.scope])
        old_plan = DemandPlan(old_hours)
        rows = self.raw + [dict(self.raw[0], source_record_number=16 + n, latitude=42.34, longitude=-82.7)
                           for n in range(5)]
        hours, audit = aggregate_activity(rows, [self.scope])
        plan = DemandPlan(hours)
        self.assertEqual(audit['retained_observations'], 20)
        self.assertEqual(len(plan.needed), len(old_plan.needed) + 1)
        self.assertIn('q25:169:-331', plan.needed)
        self.assertTrue(any(r.longitude == -82.625 for r in plan.requests))

    def test_input_partition_makes_quality_geography_and_sparse_exclusions_explicit(self):
        rows = deepcopy(self.raw[:5])
        rows += [dict(rows[0], source_record_number=6, quality_status='HEADER'),
                 dict(rows[0], source_record_number=7, quality_status='INVALID'),
                 dict(rows[0], source_record_number=8, latitude=42.500001),
                 dict(rows[0], source_record_number=9, latitude=41.0),
                 dict(rows[0], source_record_number=10, latitude=42.24)]
        _, audit = aggregate_activity(rows, [self.scope])
        self.assertEqual((audit['input_rows'], audit['excluded_quality_rows'], audit['outside_review_rows'],
                          audit['suppressed_observations'], audit['retained_observations']), (10, 2, 2, 1, 5))
        self.assertEqual(audit['outside_near_review_rows'], 1)
        self.assertEqual(audit['coverage_accounting']['sparse_status'], 'SPARSE_BUCKETS_EXCLUDED')

    def test_returned_weather_grid_is_not_clipped_to_activity_hull(self):
        hours, _ = aggregate_activity(self.raw, [self.scope])
        plan = DemandPlan(hours)
        snapshots = deepcopy(synthetic_snapshots(plan))
        for metadata, _ in snapshots:
            metadata['grid']['longitude'] = -83.3  # outside synthetic footprint's -83.25 edge
        catalog = weather_catalog(plan, snapshots)
        matches = matched_projection(plan, catalog)['matches']
        self.assertEqual(len(matches), 6)
        self.assertTrue(all(r['weather_coverage'] == 'COMPLETE' for r in matches))

    def test_explicit_weather_only_margin_preserves_nearby_records_without_changing_source_policy(self):
        rows = self.rows_at([(42.500001, -83.0), (42.7, -83.0)])
        hours, audit = aggregate_activity(rows, [self.scope], minimum_observations=1, geographic_margin_degrees=.01)
        self.assertEqual((audit['retained_observations'], audit['outside_review_rows'],
                          audit['included_boundary_context_rows']), (1, 1, 1))
        self.assertEqual(hours[0].quality_policy_sha256, self.scope.policy.policy_sha256)
        self.assertEqual(hours[0].boundary_context_observations, 1)
        self.assertEqual(audit['outside_selected_review_rows'], 2)

    def test_weather_margin_cannot_expand_arbitrarily(self):
        from winterops.weather import WeatherContractError
        for margin in (-.01, 1.01, True, float('nan')):
            with self.assertRaises(WeatherContractError):
                aggregate_activity(self.raw, [self.scope], geographic_margin_degrees=margin)


if __name__ == '__main__':
    unittest.main()
