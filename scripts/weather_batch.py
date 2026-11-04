"""Fetch once, verify offline, or reproduce a conditional historical example."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from winterops.unified_gold import load_selection
from winterops.weather import ATTRIBUTION, WeatherContractError, WeatherRequest, acquire_snapshot, canonical, digest, load_snapshot
from winterops.weather_analysis import join_daily_activity

SAMPLE = ROOT / 'data/weather/windsor_era5_20260104_20260202'


def example(snapshot):
    metadata, weather = load_snapshot(snapshot)
    evidence_path = ROOT / 'docs/FOUR_WEEK_LOCAL_EVIDENCE.json'
    evidence = json.loads(evidence_path.read_text())
    selection = load_selection(ROOT / 'docs/FOUR_WEEK_SELECTION.json')
    activity = evidence['fourth_week_daily']
    scenarios = {zone: join_daily_activity(activity, weather, selection.selected[-1:], timezone_assumption=zone)
                 for zone in ('America/Toronto', 'UTC')}
    comparison = []
    for toronto, utc in zip(scenarios['America/Toronto'], scenarios['UTC']):
        comparison.append(dict(day=toronto['day'], activity_present=toronto['activity_present'],
                               observation_count=toronto['observation_count'],
                               toronto_precipitation_mm=toronto['precipitation_sum_mm'],
                               utc_precipitation_mm=utc['precipitation_sum_mm'],
                               toronto_snowfall_cm=toronto['snowfall_sum_cm'],
                               utc_snowfall_cm=utc['snowfall_sum_cm']))
    return dict(status='EXECUTED_FIXED_POINT_TEMPORAL_FIXTURE_ONLY', attribution=ATTRIBUTION,
                spatial_matching_status='NOT_LOCATION_MATCHED_TO_ACTIVITY',
                activity_timezone_verified=False, predictive_features_allowed=False,
                activity_evidence_path=str(evidence_path.relative_to(ROOT)),
                activity_evidence_sha256=digest(evidence_path.read_bytes()),
                activity_evidence_kind='RECORDED_OFFLINE_AGGREGATES_NOT_FRESH_NATIVE_READ',
                snapshot_id=metadata['snapshot_id'], weather_hours=len(weather),
                selected_activity_processing_key=selection.selected[-1].processing_key,
                observed_activity_days=len(activity), calendar_days_per_scenario=7,
                scenarios=scenarios, sensitivity=comparison)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    fetch = sub.add_parser('fetch', help='One bounded request; existing bundle is verified and reused offline')
    fetch.add_argument('--output', required=True, type=Path)
    fetch.add_argument('--start-date', default=WeatherRequest().start_date)
    fetch.add_argument('--end-date', default=WeatherRequest().end_date)
    for command in ('validate', 'example'):
        p = sub.add_parser(command)
        p.add_argument('--snapshot', type=Path, default=SAMPLE)
        if command == 'example':
            p.add_argument('--output', type=Path, required=True, help='Create-only derived JSON file')
        else:
            p.add_argument('--staging-output', type=Path, help='Optional create-only typed hourly JSONL')
    args = parser.parse_args()
    try:
        if args.command == 'fetch':
            metadata, rows = acquire_snapshot(args.output, WeatherRequest(args.start_date, args.end_date))
        elif args.command == 'example':
            result = example(args.snapshot)
            with args.output.open('xb') as output:
                output.write(canonical(result) + b'\n')
            print(json.dumps({k: v for k, v in result.items() if k not in ('scenarios', 'sensitivity')}))
            return 0
        else:
            metadata, rows = load_snapshot(args.snapshot)
            if args.staging_output:
                with args.staging_output.open('xb') as output:
                    for row in rows:
                        output.write(canonical(row) + b'\n')
        print(json.dumps(dict(status='VERIFIED_LOCAL_WEATHER_SNAPSHOT', rows=len(rows),
                              snapshot_id=metadata['snapshot_id'], response_sha256=metadata['response_sha256'],
                              missing_values=sum(len(r['missing_variables']) for r in rows), attribution=ATTRIBUTION)))
        return 0
    except Exception as error:
        code = str(error) if isinstance(error, WeatherContractError) else type(error).__name__
        print(json.dumps(dict(status='FAILED', code=code)), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
