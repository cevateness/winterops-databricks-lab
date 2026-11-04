"""Conservative coarse hulls and regional collection cost; no GPS or HTTP."""
from dataclasses import replace
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from weather_activity import synthetic_inputs
from winterops.weather import WeatherContractError
from winterops.weather_demand import DemandPlan, aggregate_activity
from winterops.weather_footprint import coarse_footprint, collection_comparison


class CoarseFootprintTests(unittest.TestCase):
    def test_empty_activity_has_no_geometry_or_collection(self):
        result = coarse_footprint([])
        self.assertIsNone(result['bbox'])
        self.assertIsNone(result['convex_hull'])
        self.assertEqual(result['hull_candidate_count'], 0)
        self.assertEqual(DemandPlan(()).public_contract()['regional_collection_comparison']['activity_driven_api_hours'], 0)

    def test_one_cell_is_a_closed_coarse_polygon_not_a_degenerate_gps_hull(self):
        f = coarse_footprint(['q25:169:-333'])
        self.assertEqual(f['bbox'], [-83.25, 42.25, -83.0, 42.5])
        ring = f['convex_hull']['coordinates'][0]
        self.assertEqual(ring[0], ring[-1])
        self.assertEqual(len(ring), 5)
        self.assertEqual(f['coordinate_order'], 'longitude_latitude')
        self.assertEqual(f['hull_candidate_bins'], ['q25:169:-333'])

    def test_duplicate_and_input_order_do_not_change_geometry(self):
        keys = ['q25:168:-333', 'q25:169:-333', 'q25:168:-331']
        self.assertEqual(coarse_footprint(keys), coarse_footprint(list(reversed(keys)) + keys))

    def test_triangle_envelope_has_fewer_candidates_than_bounding_box(self):
        f = coarse_footprint(['q25:168:-334', 'q25:170:-334', 'q25:168:-332'])
        self.assertEqual((f['occupied_bin_count'], f['hull_candidate_count'], f['bbox_candidate_count']), (3, 8, 9))
        self.assertTrue(set(f['occupied_bins']) <= set(f['hull_candidate_bins']))
        self.assertNotIn('q25:170:-332', f['hull_candidate_bins'])

    def test_collinear_occupied_cells_still_have_a_finite_cell_envelope(self):
        f = coarse_footprint(['q25:168:-333', 'q25:169:-333', 'q25:170:-333'])
        self.assertEqual((f['hull_candidate_count'], f['bbox_candidate_count']), (3, 3))
        self.assertEqual(len(f['convex_hull']['coordinates'][0]), 5)

    def test_points_on_hull_edges_are_included_exactly(self):
        f = coarse_footprint(['q25:168:-334', 'q25:170:-334', 'q25:168:-332'])
        self.assertIn('q25:170:-333', f['hull_candidate_bins'])
        self.assertIn('q25:169:-332', f['hull_candidate_bins'])

    def test_raw_coordinates_bad_bins_or_out_of_scope_points_are_rejected(self):
        for key in ('42.301234,-83.021234', 'q25:0169:-333', 'q25:169.0:-333',
                    'q25:0:0', 'q25:169:-333:extra', None):
            with self.subTest(key=key), self.assertRaises(WeatherContractError):
                coarse_footprint([key])

    def test_sparse_suppression_keeps_eligible_and_retained_footprints_distinct(self):
        scope, rows = synthetic_inputs()
        rows = rows[:5] + rows[5:6]
        hours, audit = aggregate_activity(rows, [scope])
        plan = DemandPlan(hours)
        self.assertEqual(audit['eligible_coarse_footprint']['occupied_bin_count'], 2)
        self.assertEqual(plan.public_contract()['retained_coarse_footprint']['occupied_bin_count'], 1)
        self.assertEqual(audit['suppressed_observations'], 1)
        self.assertEqual(len(plan.requests), 1)

    def test_footprint_adds_no_requests_and_compares_location_time_overcollection(self):
        scope, rows = synthetic_inputs()
        hours, _ = aggregate_activity(rows, [scope])
        plan = DemandPlan(hours)
        before = plan.requests
        contract = plan.public_contract()
        self.assertEqual(plan.requests, before)
        self.assertEqual(contract['request_count'], 3)
        comparison = contract['regional_collection_comparison']
        self.assertEqual(comparison['activity_driven_api_hours'], 120)
        self.assertEqual(comparison['hull_region_all_dates_api_hours'], 144)
        self.assertEqual(comparison['bbox_region_all_dates_api_hours'], 144)
        self.assertFalse(comparison['regional_requests_executed'])
        self.assertIn('UNKNOWN', comparison['unique_provider_grid_count'])

    def test_preview_does_not_expose_exact_positions_or_claim_physical_area(self):
        scope, rows = synthetic_inputs()
        hours, audit = aggregate_activity(rows, [scope])
        text = json.dumps(dict(audit=audit, demand=DemandPlan(hours).public_contract()))
        for sentinel in ('42.301234', '42.241234', '-83.021234', 'truck_id', 'square_km', 'SYNTHETIC_POSITION_SENTINEL'):
            self.assertNotIn(sentinel, text)


if __name__ == '__main__':
    unittest.main()
