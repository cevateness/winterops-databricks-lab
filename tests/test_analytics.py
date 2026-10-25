"""Offline source/version contracts and execution ordering; no Spark runtime."""
import ast
from collections import Counter
from dataclasses import replace
from datetime import datetime, timezone
import csv
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from winterops.analytics import (AnalyticsConfig, SILVER_TYPES, SourceScope, build_plan,
                                 hourly_observations, run_plan, validate_silver_schema)
from winterops.quality import QualitySnapshot


class AnalyticsTests(unittest.TestCase):
    def setUp(self):
        self.scope = SourceScope("a" * 64, "synthetic.csv",
                                 "/Volumes/workspace/default/winterops_raw/synthetic.csv",
                                 "synthetic", datetime(2026, 1, 15), datetime(2026, 1, 16))
        with (ROOT / "data/synthetic/snowplow_demo_synthetic.csv").open(newline="", encoding="utf-8") as handle:
            source = list(csv.DictReader(handle))
        hashes = [hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest() for row in source]
        frequency = Counter(hashes)
        self.rows = [dict(
            source_dataset=self.scope.source_dataset, source_file_name=self.scope.source_file_name,
            source_file_path=self.scope.source_file_path, source_file_sha256=self.scope.source_file_sha256,
            record_sha256=sha, quality_status="VALID", truck_id=row["Vehicle_ID"],
            event_time_unzoned=row["Date_Time"], plow_active=row["Is_Plow_Status"] == "TRUE",
            spreader_active=row["Is_Spreader_Status"] == "TRUE", has_repeated_payload=frequency[sha] > 1,
        ) for row, sha in zip(source, hashes)]
        self.expected = QualitySnapshot("synthetic.csv", 15, 15, 1, 13, 1, 3, 10, 7)
        self.config = AnalyticsConfig(self.scope, self.expected)

    def test_duplicates_count_without_inflating_distinct_trucks(self):
        self.assertEqual(hourly_observations(self.rows, self.scope), [dict(
            source_local_naive_hour=datetime(2026, 1, 15, 7), observation_count=13,
            plow_active_observation_count=10, spreader_active_observation_count=7,
            distinct_truck_count=3, repeated_payload_observation_count=2)])

    def test_header_invalid_and_other_versions_are_excluded(self):
        extra = [dict(self.rows[0], quality_status="HEADER", event_time_unzoned=None),
                 dict(self.rows[0], quality_status="INVALID", event_time_unzoned=None),
                 dict(self.rows[0], source_file_sha256="b" * 64),
                 dict(self.rows[0], source_file_path="/Volumes/other/path/synthetic.csv")]
        self.assertEqual(hourly_observations(self.rows + extra, self.scope),
                         hourly_observations(self.rows, self.scope))

    def test_unknown_quality_is_rejected(self):
        for quality in (None, "GOOD"):
            with self.subTest(quality=quality), self.assertRaises(ValueError):
                hourly_observations([dict(self.rows[0], quality_status=quality)], self.scope)

    def test_hour_boundary_and_distinct_counts_are_per_hour(self):
        rows = [dict(self.rows[0], event_time_unzoned="2026-01-15 07:59:59.999999"),
                dict(self.rows[0], event_time_unzoned="2026-01-15 08:00:00")]
        result = hourly_observations(rows, self.scope)
        self.assertEqual([row["source_local_naive_hour"].hour for row in result], [7, 8])
        self.assertEqual([row["distinct_truck_count"] for row in result], [1, 1])

    def test_window_is_half_open(self):
        rows = [dict(self.rows[0], event_time_unzoned=self.scope.start_unzoned)]
        self.assertEqual(hourly_observations(rows, self.scope)[0]["observation_count"], 1)
        for event in ("2026-01-14 23:59:59", "2026-01-16 00:00:00"):
            with self.subTest(event=event), self.assertRaises(ValueError):
                hourly_observations([dict(self.rows[0], event_time_unzoned=event)], self.scope)

    def test_valid_timestamps_must_be_naive_and_parseable(self):
        for event in (None, "bad", "2026-01-15T07:00:00Z", datetime(2026, 1, 15, tzinfo=timezone.utc)):
            with self.subTest(event=event), self.assertRaises(ValueError):
                hourly_observations([dict(self.rows[0], event_time_unzoned=event)], self.scope)

    def test_valid_boolean_and_truck_contract(self):
        for changes in ({"plow_active": "TRUE"}, {"has_repeated_payload": None}, {"truck_id": " "}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                hourly_observations([dict(self.rows[0], **changes)], self.scope)

    def test_source_hash_is_explicit_and_cannot_inject_sql(self):
        for sha in ("", None, "a" * 63, "A" * 64, "x'; DROP TABLE x;--"):
            with self.subTest(sha=sha), self.assertRaises(ValueError):
                replace(self.scope, source_file_sha256=sha)

    def test_source_paths_and_identifiers_cannot_inject_sql(self):
        for changes in ({"source_file_path": "/Volumes/../synthetic.csv"},
                        {"source_file_name": "other.csv"}, {"source_dataset": "x' OR 1=1--"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(self.scope, **changes)
        with self.assertRaises(ValueError):
            replace(self.config, schema="default; DROP SCHEMA x")

    def test_window_is_bounded_and_has_no_timezone(self):
        for changes in ({"end_unzoned": datetime(2026, 1, 15)},
                        {"end_unzoned": datetime(2026, 1, 23)},
                        {"start_unzoned": datetime(2026, 1, 15, 1)},
                        {"start_unzoned": datetime(2026, 1, 15, tzinfo=timezone.utc)}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(self.scope, **changes)

    def test_evidence_matches_filename_counts_and_types(self):
        for expected in (replace(self.expected, source_file="other.csv"),
                         replace(self.expected, bronze_rows=16),
                         replace(self.expected, bronze_rows=True)):
            with self.subTest(expected=expected), self.assertRaises((TypeError, ValueError)):
                replace(self.config, expected=expected)

    def test_schema_rejects_instant_timestamp_and_missing_boolean(self):
        validate_silver_schema(dict(SILVER_TYPES, extra_column="string"))
        for changes in ({"event_time_unzoned": "timestamp"}, {"plow_active": "string"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                validate_silver_schema(dict(SILVER_TYPES, **changes))
        with self.assertRaises(ValueError):
            validate_silver_schema({})

    def test_plan_checks_multiplicity_and_never_deduplicates_consumers(self):
        plan = build_plan(self.config)
        self.assertIn("FULL OUTER JOIN", plan.preflight[1])
        self.assertIn("s.min_occurrences <> b.n", plan.preflight[1])
        self.assertIn("s.unknown_rows = 0", plan.preflight[0])
        self.assertIn("w.all_rows = s.silver_rows", plan.preflight[0])
        self.assertIn("b.bronze_rows = 15", plan.preflight[0])
        for view in plan.views[:2]:
            self.assertIn("source_file_sha256 = '" + "a" * 64 + "'", view)
            self.assertIn(self.scope.source_file_path, view)
            self.assertNotIn("DISTINCT", view)
        self.assertIn("quality_status <> 'VALID' OR quality_status IS NULL", plan.views[1])

    def test_gold_reads_valid_view_with_ntz_hour_semantics(self):
        gold = build_plan(self.config).views[2]
        self.assertIn(self.config.table("valid"), gold)
        self.assertNotIn(self.config.table("silver"), gold)
        self.assertNotIn(self.config.table("bronze"), gold)
        self.assertIn("AS TIMESTAMP_NTZ", gold)
        self.assertIn("source_local_naive_hour", gold)
        self.assertIn("COUNT(*) AS observation_count", gold)
        self.assertIn("COUNT(DISTINCT truck_id)", gold)
        self.assertNotIn("to_utc_timestamp", gold.lower())

    def test_reported_fixture_is_an_explicit_plan_input(self):
        raw = json.loads((ROOT / "data/fixtures/windsor_week_2026_01_12_18_summary.json").read_text())
        plan = build_plan(AnalyticsConfig(SourceScope("c" * 64), QualitySnapshot.from_mapping(raw)))
        self.assertIn("b.bronze_rows = 110337", plan.preflight[0])
        self.assertNotIn("110337", build_plan(self.config).render())

    def test_dry_run_never_touches_spark(self):
        self.assertEqual(run_plan(None, self.config), build_plan(self.config))
        with self.assertRaises(TypeError):
            run_plan(None, self.config, apply="false")

    def test_failure_stops_before_any_view_writes(self):
        engine = FakeSpark(fail=True)
        with self.assertRaises(RuntimeError):
            run_plan(engine, self.config, apply=True)
        self.assertEqual(len(engine.statements), 1)
        self.assertEqual(engine.views, {})

    def test_schema_failure_precedes_sql_execution(self):
        engine = FakeSpark(schema=dict(SILVER_TYPES, event_time_unzoned="timestamp"))
        with self.assertRaises(ValueError):
            run_plan(engine, self.config, apply=True)
        self.assertEqual(engine.statements, [])

    def test_rerun_reuses_exact_view_definitions_and_order(self):
        engine = FakeSpark()
        first = run_plan(engine, self.config, apply=True)
        definitions = engine.views.copy()
        self.assertEqual(first, run_plan(engine, self.config, apply=True))
        self.assertEqual(engine.views, definitions)
        self.assertEqual(len(definitions), 3)
        expected = [*first.preflight, *first.views, *first.postflight]
        self.assertEqual(engine.statements, expected * 2)

    def test_new_entrypoints_compile_without_spark(self):
        for name in ("notebooks/06_silver_consumers_hourly.py", "scripts/render_analytics_sql.py",
                     "scripts/check_databricks.py"):
            ast.parse((ROOT / name).read_text(encoding="utf-8"))


class FakeSpark:
    """Ordering and DDL-definition test double; does not validate Spark SQL."""
    def __init__(self, *, fail=False, schema=None):
        self.fail = fail
        self.statements = []
        self.views = {}
        self.types = schema or SILVER_TYPES

    def table(self, name):
        fields = [SimpleNamespace(name=name, dataType=SimpleNamespace(simpleString=lambda kind=kind: kind))
                  for name, kind in self.types.items()]
        return SimpleNamespace(schema=SimpleNamespace(fields=fields))

    def sql(self, statement):
        self.statements.append(statement)
        if statement.startswith("CREATE OR REPLACE VIEW"):
            self.views[statement.splitlines()[0]] = statement

        def collect():
            if self.fail:
                raise RuntimeError("Synthetic preflight failure")
            return []
        return SimpleNamespace(collect=collect)


if __name__ == "__main__":
    unittest.main()
