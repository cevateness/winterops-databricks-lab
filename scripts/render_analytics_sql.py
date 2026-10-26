"""Offline SQL renderer. Never connects to Databricks or applies DDL."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from winterops.analytics import AnalyticsConfig, SourceScope, build_plan
from winterops.quality import QualitySnapshot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-file-sha256", required=True)
    parser.add_argument("--expected-summary", type=Path, required=True,
                        help="Reviewed aggregate evidence for the selected source version")
    parser.add_argument("--source-file-name", default=SourceScope.__dataclass_fields__["source_file_name"].default)
    parser.add_argument("--source-file-path", default=SourceScope.__dataclass_fields__["source_file_path"].default)
    parser.add_argument("--source-dataset", default="windsor_snowplow_activity")
    parser.add_argument("--start-unzoned", default="2026-01-12")
    parser.add_argument("--end-unzoned", default="2026-01-19")
    parser.add_argument("--catalog", default="workspace")
    parser.add_argument("--schema", default="default")
    args = parser.parse_args()
    try:
        expected = QualitySnapshot.from_mapping(json.loads(args.expected_summary.read_text(encoding="utf-8")))
        scope = SourceScope(args.source_file_sha256, args.source_file_name, args.source_file_path,
                            args.source_dataset, datetime.fromisoformat(args.start_unzoned),
                            datetime.fromisoformat(args.end_unzoned))
        plan = build_plan(AnalyticsConfig(scope, expected, args.catalog, args.schema))
    except (ValueError, TypeError, KeyError, OSError) as error:
        parser.error(str(error))
    print("-- OFFLINE PLAN ONLY. Review SQL and obtain workspace approval before executing.")
    print(plan.render(), end="")


if __name__ == "__main__":
    main()
