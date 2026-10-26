"""Execute SQL logic in SQLite with explicit dialect adaptations, NOT Spark QA."""
from collections import Counter
from datetime import datetime
import hashlib
from pathlib import Path
import re
import sqlite3
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from winterops.analytics import AnalyticsConfig, SILVER_TYPES, SourceScope, build_plan
from winterops.quality import QualitySnapshot


class CountIf:
    def __init__(self):
        self.count = 0

    def step(self, value):
        self.count += bool(value)

    def finalize(self):
        return self.count


def sqlite_dialect(statement):
    """Only emulate names, assertion/count functions, and NTZ textual operations.

    Databricks parsing, NTZ typing, privileges, view metadata and optimizer behavior
    are deliberately outside this test's evidence.
    """
    statement = re.sub(r"`[^`]+`\.`[^`]+`\.`([^`]+)`", r'"\1"', statement)
    statement = re.sub(r"TIMESTAMP_NTZ ('[^']+')", r"\1", statement)
    statement = statement.replace(" RLIKE ", " REGEXP ")
    statement = statement.replace(
        "CAST(substring(CAST(event_time_unzoned AS STRING), 1, 13) || ':00:00' AS TIMESTAMP_NTZ)",
        "(substr(event_time_unzoned, 1, 13) || ':00:00')",
    )
    statement = re.sub(r"(?m)^COMMENT '[^']*'\n", "", statement)
    return statement.replace("CREATE OR REPLACE VIEW", "CREATE VIEW")


class SqlLogicTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)
        self.db.create_aggregate("count_if", 1, CountIf)
        self.db.create_function("regexp", 2, lambda pattern, value: value is not None and bool(re.search(pattern, value)))

        def assertion(condition, message):
            if not condition:
                raise ValueError(message)
            return None
        self.db.create_function("assert_true", 2, assertion)
        self.scope = SourceScope("a" * 64, "synthetic.csv", "/Volumes/demo/default/raw/synthetic.csv",
                                 "synthetic", datetime(2026, 1, 15), datetime(2026, 1, 16))
        self.config = AnalyticsConfig(self.scope, QualitySnapshot("synthetic.csv", 5, 5, 1, 3, 1, 2, 2, 1))
        self.plan = build_plan(self.config)
        columns = ", ".join(name + " " + kind for name, kind in SILVER_TYPES.items())
        for table in ("winterops_bronze_windsor_activity", "winterops_silver_windsor_week_sample"):
            self.db.execute(f"CREATE TABLE {table} ({columns})")
        # Two identical valid observations, one other valid observation, one header, one invalid.
        payloads = ["repeat", "repeat", "other", "header", "invalid"]
        multiplicities = Counter(payloads)
        for index, payload in enumerate(payloads):
            is_header, is_invalid = payload == "header", payload == "invalid"
            row = dict(
                source_dataset=self.scope.source_dataset, source_file_name=self.scope.source_file_name,
                source_file_path=self.scope.source_file_path, source_file_sha256=self.scope.source_file_sha256,
                record_sha256=hashlib.sha256(payload.encode()).hexdigest(),
                truck_id="SYN-1" if payload == "repeat" else "SYN-2",
                event_time_unzoned=None if is_header or is_invalid else "2026-01-15 07:30:00",
                latitude=42.3, longitude=-83.0, plow_active=payload == "repeat",
                spreader_active=payload == "other", engine_active=True,
                payload_occurrences=multiplicities[payload], has_repeated_payload=multiplicities[payload] > 1,
                is_repeated_header=is_header,
                quality_status="HEADER" if is_header else "INVALID" if is_invalid else "VALID",
                quality_issues="REPEATED_HEADER" if is_header else "INVALID_TIMESTAMP" if is_invalid else "",
            )
            values = [row[name] for name in SILVER_TYPES]
            placeholders = ",".join("?" for _ in values)
            for table in ("winterops_bronze_windsor_activity", "winterops_silver_windsor_week_sample"):
                self.db.execute(f"INSERT INTO {table} VALUES ({placeholders})", values)

    def execute(self, statement):
        return self.db.execute(sqlite_dialect(statement)).fetchall()

    def publish(self):
        for statement in self.plan.preflight:
            self.execute(statement)
        for statement in self.plan.views:
            name = re.search(r"VIEW (`[^`]+`\.`[^`]+`\.`([^`]+)`)", statement).group(2)
            self.db.execute(f'DROP VIEW IF EXISTS "{name}"')
            self.execute(statement)
        for statement in self.plan.postflight:
            self.execute(statement)

    def test_complete_sql_plan_counts_and_rerun(self):
        for _ in range(2):
            self.publish()
            rows = self.db.execute("SELECT source_local_naive_hour, observation_count, "
                                   "plow_active_observation_count, spreader_active_observation_count, "
                                   "distinct_truck_count, repeated_payload_observation_count "
                                   "FROM winterops_gold_windsor_hourly_observations").fetchall()
            self.assertEqual(rows, [("2026-01-15 07:00:00", 3, 2, 1, 2, 2)])
            for table in ("winterops_bronze_windsor_activity", "winterops_silver_windsor_week_sample"):
                self.assertEqual(self.db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0], 5)

    def test_equal_totals_do_not_hide_changed_payload_multiplicities(self):
        self.db.execute("UPDATE winterops_silver_windsor_week_sample SET record_sha256 = ? WHERE rowid=3",
                        ("d" * 64,))
        self.execute(self.plan.preflight[0])
        with self.assertRaises(sqlite3.OperationalError):
            self.execute(self.plan.preflight[1])

    def test_out_of_window_valid_row_stops_publication(self):
        self.db.execute("UPDATE winterops_silver_windsor_week_sample "
                        "SET event_time_unzoned='2026-01-16 00:00:00' WHERE rowid=3")
        with self.assertRaises(sqlite3.OperationalError):
            self.publish()
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='view'").fetchone()[0], 0)

    def test_unrelated_silver_version_stops_publication(self):
        self.db.execute("UPDATE winterops_silver_windsor_week_sample SET source_file_sha256=? WHERE rowid=3",
                        ("b" * 64,))
        with self.assertRaises(sqlite3.OperationalError):
            self.publish()

    def test_incorrect_repeat_warning_count_is_detected(self):
        self.db.execute("UPDATE winterops_silver_windsor_week_sample "
                        "SET payload_occurrences=1, has_repeated_payload=0 WHERE rowid=1")
        self.execute(self.plan.preflight[0])
        with self.assertRaises(sqlite3.OperationalError):
            self.execute(self.plan.preflight[1])


if __name__ == "__main__":
    unittest.main()
