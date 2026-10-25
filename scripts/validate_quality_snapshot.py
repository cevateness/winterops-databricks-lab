#!/usr/bin/env python3
"""Validate a user-reported *aggregate* QA snapshot without Databricks access."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from winterops.quality import QualitySnapshot, validate_snapshot


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot_json", type=Path)
    args = parser.parse_args()
    data = json.loads(args.snapshot_json.read_text(encoding="utf-8"))
    snapshot = QualitySnapshot.from_mapping(data)
    errors = validate_snapshot(snapshot)
    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print(f"PASS: aggregate invariants for {snapshot.source_file}")
    print("NOTE: This does not verify the data in Databricks or license real telemetry for redistribution.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
