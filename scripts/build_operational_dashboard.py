"""Build the real historical dashboard offline; never download or deploy data.

Default: regenerate from the committed public aggregate snapshot. Full rebuild:
read four locally cached pinned CSVs and the existing private weather replay ZIP.
"""
import argparse
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from winterops.foundation import processing_key, read_bronze, silver_rows
from winterops.operational_analytics import (match_cached_weather, public_bundle, validate_products)
from winterops.operational_dashboard import pack, render_dashboard, unpack
from winterops.operational_sql import LocalGold, analytical_queries, weather_hourly_query, check_weather_sql
from winterops.sources import SourceVersion, fingerprint, outside_git
from winterops.temporal_review import summarize_matches
from winterops.unified_gold import load_selection
from winterops.weather import WeatherContractError, canonical, digest, require


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def build_actual(source_cache, archive_path, private_output):
    source_cache, archive_path, private_output = map(outside_git, (source_cache, archive_path, private_output))
    require(not private_output.exists(), 'ANALYTICS_PRIVATE_OUTPUT_EXISTS')
    plan = load_selection(ROOT / 'docs/FOUR_WEEK_SELECTION.json')
    pin = read_json(ROOT / 'docs/WEATHER_ACTIVITY_EXECUTION_RESULTS.json')['private_download_artifact']
    require(archive_path.stat().st_size == pin['bytes'] and fingerprint(archive_path) == pin['sha256'],
            'ANALYTICS_ARCHIVE_PIN_MISMATCH')
    with zipfile.ZipFile(archive_path) as archive:
        require(archive.getinfo('matched_activity_weather.json').file_size <= 8 * 1024 * 1024,
                'ANALYTICS_ARCHIVE_MEMBER_BOUND')
        saved = json.loads(archive.read('matched_activity_weather.json'))
    local = LocalGold(plan)
    source_bytes = 0
    try:
        for scope in plan.selected:
            path = source_cache / 'raw' / scope.source_file_name / scope.source_file_sha256 / scope.source_file_name
            version = SourceVersion.from_dict(read_json(path.with_suffix('.version.json')))
            require(Path(version.local_path).resolve() == path.resolve(), 'ANALYTICS_CACHE_PATH_MISMATCH')
            version.verify()
            source_bytes += version.byte_count
            require(source_bytes <= 32 * 1024 * 1024 and version.byte_count <= 16 * 1024 * 1024,
                    'ANALYTICS_SOURCE_BYTE_BOUND')
            require(version.source == scope.source and version.source_file_sha256 == scope.source_file_sha256 and
                    version.version_id == scope.source_version_id and processing_key(version, scope.policy) == scope.processing_key,
                    'ANALYTICS_SOURCE_PIN_MISMATCH')
            bronze = list(read_bronze(version))
            typed = silver_rows(bronze, version, scope.policy)
            local.add_verified_scope(scope, typed)
            del bronze, typed
        products = local.products()
    finally:
        local.close()
    validation = validate_products(products, plan)
    prior = read_json(ROOT / 'docs/FOUR_WEEK_LOCAL_EVIDENCE.json')
    require(all(validation['totals'][k] == prior['totals'][k] for k in validation['totals']),
            'ANALYTICS_RECORDED_GOLD_TOTALS')
    require(validation['rows'] == dict(hourly=325, daily=25, weekly=4, cell_hour=842), 'ANALYTICS_EXPECTED_GRAINS')
    clock_evidence = read_json(ROOT / 'data/fixtures/source_time_evidence.json')
    require({r['source_local_naive_hour']: r['observation_count'] for r in products['hourly']} ==
            clock_evidence['local_source_hour_profile'], 'ANALYTICS_INDEPENDENT_HOUR_PROFILE')
    matches = match_cached_weather(products, saved['weather'], saved['matches'])
    temporal = summarize_matches(matches)
    require(temporal == read_json(ROOT / 'docs/TEMPORAL_REVIEW_RESULTS.json')['analytical_review'],
            'ANALYTICS_RECORDED_WEATHER_DAILY')
    provenance = {k: saved['weather'][k] for k in ('weather_snapshot_id', 'weather_kind', 'requested_model', 'model_attestation')}
    provenance.update(archive_sha256=pin['sha256'], original_collection_date='2026-11-03',
                      raw_response_provenance='Hash-pinned private replay ZIP: request metadata and original responses.',
                      weather_requests_during_build=0)
    bundle = public_bundle(products, plan, matches, evidence='EXECUTED_LOCAL_PINNED_CSV_GOLD_AND_CACHED_WEATHER',
                           clock_evidence=clock_evidence, weather_provenance=provenance)
    private_output.mkdir(parents=True)
    for name, rows in (('cell_hour', products['cell_hour']), ('cell_weather', matches)):
        (private_output / (name + '.json')).write_bytes(canonical(rows) + b'\n')
    receipt = dict(evidence=bundle['evidence'], source_bytes_verified=source_bytes, validation=validation,
                   weather_sql=check_weather_sql(matches, bundle['weather_hourly']),
                   weather_matches=len(matches), weather_totals_by_hypothesis=temporal['hypothesis_totals'],
                   independent_source_hour_profile='PASS_EXACT_325_HOURS', recorded_weather_daily='PASS_EXACT_50_ROWS',
                   public_map_observations=sum(r['observation_count'] for r in bundle['cells']),
                   public_map_suppressed_observations=sum(bundle['suppressed_map_observations'].values()),
                   detailed_spatial_validation='RERUN_FROM_EXACT_CSV_BYTES_AND_CACHED_MATCHES',
                   weather_http_requests=0, municipal_http_requests=0, native_requests=0,
                   native_publication='BLOCKED_PRIVATE_MATRICES_AND_SECURE_BINDINGS_UNAVAILABLE',
                   private_output_sha256={p.name: fingerprint(p) for p in private_output.glob('*.json')})
    return bundle, receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-root', type=Path, required=True, help='New create-only directory')
    parser.add_argument('--source-cache', type=Path, help='Existing LocalStager cache outside Git; never downloaded here')
    parser.add_argument('--archive', type=Path, help='Existing private replay ZIP outside Git')
    parser.add_argument('--private-output', type=Path, help='New private detail directory outside Git')
    args = parser.parse_args()
    try:
        require(not args.output_root.exists(), 'ANALYTICS_OUTPUT_EXISTS')
        full = (args.source_cache, args.archive, args.private_output)
        require(all(full) or not any(full), 'ANALYTICS_ALL_REBUILD_INPUTS_REQUIRED')
        if all(full):
            bundle, receipt = build_actual(*full)
        else:
            bundle = unpack(read_json(ROOT / 'dashboard/analytics.json'))
            expected = bundle.pop('content_sha256')
            require(digest(canonical(bundle)) == expected, 'ANALYTICS_PUBLIC_SNAPSHOT_HASH')
            bundle['content_sha256'] = expected
            receipt = dict(evidence='PUBLIC_AGGREGATE_REPLAY_ONLY',
                           detailed_spatial_validation='NOT_RERUN_WITHOUT_PRIVATE_INPUTS',
                           weather_http_requests=0, municipal_http_requests=0, native_requests=0)
        args.output_root.mkdir(parents=True)
        (args.output_root / 'analytics.json').write_bytes(canonical(pack(bundle)) + b'\n')
        (args.output_root / 'index.html').write_text(render_dashboard(bundle), encoding='utf-8')
        plan = load_selection(ROOT / 'docs/FOUR_WEEK_SELECTION.json')
        (args.output_root / 'databricks_candidates.sql').write_text('\n\n'.join(
            '-- READ-ONLY CANDIDATE: ' + name + '\n' + sql + ';' for name, sql in analytical_queries(plan).items()), encoding='utf-8')
        (args.output_root / 'weather_hourly.sql').write_text(
            '-- READ ONLY. Requires the private validated cell_weather relation; no native binding exists.\n' +
            weather_hourly_query() + ';\n', encoding='utf-8')
        receipt['public_content_sha256'] = bundle['content_sha256']
        receipt['files_sha256'] = {p.name: fingerprint(p) for p in args.output_root.iterdir() if p.is_file()}
        (args.output_root / 'execution.json').write_bytes(canonical(receipt) + b'\n')
        print(json.dumps(receipt))
        return 0
    except Exception as error:
        print(json.dumps(dict(status='FAILED', code=str(error) if isinstance(error, WeatherContractError)
                              else type(error).__name__)), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
