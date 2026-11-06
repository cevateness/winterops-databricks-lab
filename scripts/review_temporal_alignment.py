"""Replay recorded public clock evidence and optionally a hash-pinned private ZIP.

No HTTP or Databricks calls. Output contains city-day aggregates only, never bins,
coordinates or identifiers. Downloaded archive stays outside the repository.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from winterops.temporal_review import review_clock, summarize_matches
from winterops.weather import WeatherContractError, require


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='Create-only JSON result')
    parser.add_argument('--archive', type=Path, help='Existing private weather replay ZIP, outside Git')
    args = parser.parse_args()
    try:
        require(not args.output.exists(), 'REVIEW_OUTPUT_ALREADY_EXISTS')
        evidence = json.loads((ROOT / 'data/fixtures/source_time_evidence.json').read_text(encoding='utf-8'))
        result = dict(evidence='RECORDED_SOURCE_TIME_REVIEW', weather_http_requests=0, native_requests=0,
                      clock=review_clock(evidence))
        if args.archive:
            path = args.archive.resolve()
            require(ROOT not in path.parents, 'REVIEW_ARCHIVE_MUST_STAY_OUTSIDE_REPOSITORY')
            receipt = json.loads((ROOT / 'docs/WEATHER_ACTIVITY_EXECUTION_RESULTS.json').read_text(encoding='utf-8'))
            pin = receipt['private_download_artifact']
            require(path.stat().st_size == pin['bytes'], 'REVIEW_ARCHIVE_SIZE_MISMATCH')
            require(hashlib.sha256(path.read_bytes()).hexdigest() == pin['sha256'], 'REVIEW_ARCHIVE_HASH_MISMATCH')
            with zipfile.ZipFile(path) as archive:
                name = 'matched_activity_weather.json'
                require(archive.getinfo(name).file_size <= 8 * 1024 * 1024, 'REVIEW_MEMBER_SIZE_LIMIT')
                matched = json.loads(archive.read(name))
            result['archive_sha256'] = pin['sha256']
            result['analytical_review'] = summarize_matches(matched['matches'])
        with args.output.open('x', encoding='utf-8') as stream:
            json.dump(result, stream, indent=2, sort_keys=True)
            stream.write('\n')
        print(json.dumps(dict(status='WROTE_OFFLINE_REVIEW', clock_status=result['clock']['status'],
                              daily_rows=len(result.get('analytical_review', {}).get('days', [])),
                              weather_http_requests=0, native_requests=0)))
        return 0
    except Exception as error:
        print(json.dumps(dict(status='FAILED', code=str(error) if isinstance(error, WeatherContractError)
                              else type(error).__name__)), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
