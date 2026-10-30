"""Render a private pinned Jobs/SQL package. No authentication or remote calls."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from winterops.batch import BatchRequest, prepare_job, synthetic_request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--request', type=Path, help='Private reviewed BatchRequest JSON')
    source.add_argument('--synthetic-example', action='store_true', help='Fictitious rendering fixture; never execute')
    parser.add_argument('--output-root', type=Path, required=True, help='Private directory outside Git')
    parser.add_argument('--warehouse-id', required=True, help='Previously approved existing SQL warehouse')
    parser.add_argument('--workspace-root', required=True, help='Reviewed private Workspace files destination')
    args = parser.parse_args()
    try:
        request = synthetic_request() if args.synthetic_example else BatchRequest.from_dict(
            json.loads(args.request.read_text(encoding='utf-8-sig')))
        print(json.dumps(prepare_job(request, args.output_root, args.warehouse_id, args.workspace_root), indent=2))
    except Exception as error:
        # Paths, API configuration and record-bearing exception text stay private.
        print(json.dumps(dict(status='FAILED', error_type=type(error).__name__)), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
