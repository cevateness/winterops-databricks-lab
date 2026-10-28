"""Render read-only dashboard/diagnostic SQL offline; no credentials or execution."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from winterops.analytics import AnalyticsConfig, SourceScope
from winterops.gold_products import DiagnosticSettings, PRODUCT_NAMES, build_products
from winterops.quality import QualitySnapshot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-file-sha256', required=True)
    parser.add_argument('--expected-summary', type=Path, required=True)
    for key in ('source_file_name', 'source_file_path', 'source_dataset'):
        parser.add_argument('--' + key.replace('_', '-'), default=SourceScope.__dataclass_fields__[key].default)
    parser.add_argument('--start-unzoned', default='2026-01-12')
    parser.add_argument('--end-unzoned', default='2026-01-19')
    parser.add_argument('--catalog', default='workspace')
    parser.add_argument('--schema', default='default')
    parser.add_argument('--long-gap-seconds', type=int, default=1800)
    parser.add_argument('--dense-hour-observations', type=int, default=1000)
    parser.add_argument('--product', choices=('all', *PRODUCT_NAMES), default='all')
    parser.add_argument('--output', type=Path, help='Optional UTF-8 local SQL file; still no execution')
    args = parser.parse_args()
    try:
        scope = SourceScope(args.source_file_sha256, args.source_file_name, args.source_file_path,
                            args.source_dataset, datetime.fromisoformat(args.start_unzoned),
                            datetime.fromisoformat(args.end_unzoned))
        expected = QualitySnapshot.from_mapping(json.loads(args.expected_summary.read_text(encoding='utf-8')))
        plan = build_products(AnalyticsConfig(scope, expected, args.catalog, args.schema),
                              DiagnosticSettings(args.long_gap_seconds, args.dense_hour_observations))
        rendered = plan.render(None if args.product == 'all' else args.product)
        if args.output:
            args.output.write_text(rendered, encoding='utf-8')
        else:
            print(rendered, end='')
    except (ValueError, TypeError, KeyError, OSError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
