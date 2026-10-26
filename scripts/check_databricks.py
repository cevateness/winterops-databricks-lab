"""Read-only Databricks API smoke test; prints sanitized status, never CLI output."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from winterops.databricks_probe import probe


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--workspace-host", required=True)
    parser.add_argument("--include-jobs", action="store_true", help="Optional Jobs API metadata probe")
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()
    try:
        result = probe(args.profile, args.workspace_host, include_jobs=args.include_jobs,
                       timeout=args.timeout)
    except ValueError:
        parser.error("Invalid profile, workspace-host or timeout; use --help for the contract")
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
