"""Activity-driven weather demand/matching; demo is wholly synthetic/offline.

Private Silver commands require user-supplied local input outside this repository.
They never query Databricks. Only fetch performs bounded public weather requests.
"""
from dataclasses import asdict
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from winterops.batch import synthetic_request
from winterops.landing import OriginalLanding
from winterops.unified_gold import SelectedVersion, load_selection
from winterops.weather import ATTRIBUTION, WeatherContractError, canonical, require, stage_response
from winterops.weather_demand import (DemandPlan, acquire_demand, aggregate_activity,
                                     load_demand, matched_projection, weather_catalog)


def synthetic_inputs():
    """Fictitious scope/records; intentionally includes coordinate/time sentinels."""
    r = synthetic_request()
    v = r.version
    scope = SelectedVersion.from_version(v, 100, OriginalLanding(v.source, v.source_file_sha256, v.byte_count))
    rows = []
    for lat, day, hour in ((42.301234, '2026-01-05', 0), (42.241234, '2026-01-05', 0),
                           (42.301234, '2026-01-08', 12)):
        for second in range(5):
            rows.append(dict(scope.dimensions(), processing_key=scope.processing_key,
                             source_record_number=len(rows) + 1, quality_status='VALID',
                             latitude=lat, longitude=-83.021234,
                             event_time_unzoned=f'{day} {hour:02d}:00:{second:02d}',
                             truck_id='SYNTHETIC_POSITION_SENTINEL'))
    return scope, rows


def synthetic_snapshots(plan):
    """Mock provider maps two candidate points to one returned grid; no HTTP."""
    result = []
    for r in plan.requests:
        n = len(r.epochs)
        body = dict(latitude=42.25, longitude=-83.0, elevation=180.0, timezone='GMT', utc_offset_seconds=0,
                    hourly_units=dict(time='unixtime', temperature_2m='°C', precipitation='mm', snowfall='cm'),
                    hourly=dict(time=list(r.epochs), temperature_2m=[float((t // 3600) % 24) for t in r.epochs],
                                precipitation=[float((t // 3600) % 3) for t in r.epochs], snowfall=[0.0] * n))
        staged, grid = stage_response(canonical(body), r)
        metadata = dict(request_id=r.request_id, request_url=r.url, snapshot_id=staged[0]['snapshot_id'],
                        grid=grid, weather_kind='historical_reanalysis', model_attestation='REQUEST_PARAMETER_ONLY')
        result.append((metadata, staged))
    return tuple(result)


def demo():
    scope, rows = synthetic_inputs()
    hours, audit = aggregate_activity(rows, [scope])
    plan = DemandPlan(hours)
    catalog = weather_catalog(plan, synthetic_snapshots(plan))
    projection = matched_projection(plan, catalog)
    return dict(evidence='SYNTHETIC_OFFLINE_ONLY', live_spatial_matching='BLOCKED_PRIVATE_SILVER_UNAVAILABLE',
                native_requests=0, weather_http_requests=0, attribution=ATTRIBUTION,
                audit=audit, demand=plan.public_contract(), coarse_activity=[asdict(a) for a in hours],
                weather=catalog, **projection)


def private_path(path):
    path = path.resolve()
    require(path != ROOT and ROOT not in path.parents, 'DEMAND_PRIVATE_FILES_MUST_STAY_OUTSIDE_REPOSITORY')
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    d = commands.add_parser('demo', help='Synthetic-only proof; no private source or HTTP')
    d.add_argument('--output', type=Path, required=True)
    for command in ('plan', 'fetch', 'match'):
        p = commands.add_parser(command)
        p.add_argument('--private-silver', type=Path, required=True, help='Private typed Silver JSONL projection')
        p.add_argument('--selection', type=Path, default=ROOT / 'docs/FOUR_WEEK_SELECTION.json')
        p.add_argument('--output', type=Path, required=True, help='Private create-only JSON evidence file')
        p.add_argument('--lookback-hours', type=int, default=2)
        if command in ('fetch', 'match'):
            p.add_argument('--snapshots', type=Path, required=True, help='Private weather snapshot cache outside Git')
    args = parser.parse_args()
    try:
        require(not args.output.exists(), 'DEMAND_OUTPUT_ALREADY_EXISTS')
        if args.command == 'demo':
            result = demo()
        else:
            private_path(args.output)
            path = private_path(args.private_silver)
            def read_rows():
                with path.open(encoding='utf-8') as stream:
                    for line in stream:
                        require(len(line) <= 65536, 'DEMAND_PRIVATE_ROW_SIZE')
                        row = json.loads(line)
                        require(type(row) is dict, 'DEMAND_PRIVATE_ROW_OBJECT')
                        yield row
            hours, audit = aggregate_activity(read_rows(), load_selection(args.selection).selected)
            plan = DemandPlan(hours, args.lookback_hours)
            result = dict(evidence='PRIVATE_LOCAL_INPUT_NOT_NATIVE_VERIFIED_HERE', attribution=ATTRIBUTION,
                          audit=audit, demand=plan.public_contract())
            if args.command in ('fetch', 'match'):
                cache = private_path(args.snapshots)
                snapshots = acquire_demand(plan, cache) if args.command == 'fetch' else load_demand(plan, cache)
                catalog = weather_catalog(plan, snapshots)
                result.update(weather=catalog, **matched_projection(plan, catalog))
        with args.output.open('xb') as output:
            output.write(canonical(result) + b'\n')
        print(json.dumps(dict(status='WROTE_LOCAL_CONTRACT_RESULT', evidence=result['evidence'],
                              matches=len(result.get('matches', [])))))
        return 0
    except Exception as error:
        print(json.dumps(dict(status='FAILED', code=str(error) if isinstance(error, WeatherContractError)
                              else type(error).__name__)), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
