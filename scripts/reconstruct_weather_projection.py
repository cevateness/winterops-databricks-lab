"""Recover pinned public CSVs and reconstruct private local Silver for weather.

No Databricks or weather API access. Raw files/projection remain outside Git.
This does not establish current native COMPLETE state or replace private Gold plans.
"""
from collections import Counter
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from winterops.foundation import PIPELINE_VERSION, processing_key, read_bronze, silver_rows
from winterops.sources import LocalStager, SourceVersion, outside_git
from winterops.unified_gold import load_selection
from winterops.weather import canonical, require

FIELDS = ('source_dataset', 'source_file_name', 'source_file_sha256', 'source_version_id', 'pipeline_version',
          'quality_policy_sha256', 'source_week_start', 'source_week_end_exclusive', 'processing_key',
          'source_record_number', 'event_time_unzoned', 'latitude', 'longitude', 'quality_status')


def reconstruct(selected, directory, *, download=None):
    directory = outside_git(Path(directory))
    require(1 <= len(selected) <= 4, 'RECONSTRUCTION_FOUR_SOURCE_BOUND')
    require(all(s.pipeline_version == PIPELINE_VERSION for s in selected), 'RECONSTRUCTION_PIPELINE_MISMATCH')
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / 'silver_projection.jsonl'
    require(not target.exists(), 'RECONSTRUCTION_OUTPUT_ALREADY_EXISTS')
    total_bytes, results = 0, []
    # A failed projection remains incomplete and must not be used as a full scope.
    # Only a success receipt establishes completion; no overwrite/automatic repair.
    with target.open('xb') as output:
        for scope in selected:
            remaining = 32 * 1024 * 1024 - total_bytes
            require(remaining > 0, 'RECONSTRUCTION_TOTAL_BYTE_BOUND')
            if download is not None:
                version = download(scope.source)
            else:
                store = LocalStager(directory / 'sources', max_bytes=min(16 * 1024 * 1024, remaining), deadline_seconds=30)
                path = store.root / 'raw' / scope.source_file_name / scope.source_file_sha256 / scope.source_file_name
                if path.exists():
                    version = SourceVersion.from_dict(json.loads(path.with_suffix('.version.json').read_text()))
                else:
                    version, _ = store.download(scope.source)
            version.verify()
            require(version.source == scope.source and version.source_file_sha256 == scope.source_file_sha256
                    and version.version_id == scope.source_version_id
                    and processing_key(version, scope.policy) == scope.processing_key, 'RECONSTRUCTION_PIN_MISMATCH')
            total_bytes += version.byte_count
            require(version.byte_count <= 16 * 1024 * 1024 and total_bytes <= 32 * 1024 * 1024,
                    'RECONSTRUCTION_TOTAL_BYTE_BOUND')
            bronze = list(read_bronze(version))
            typed = silver_rows(bronze, version, scope.policy)
            require(len(typed) == len(bronze) == scope.expected_rows, 'RECONSTRUCTION_ROW_COUNT_MISMATCH')
            quality = Counter(r['quality_status'] for r in typed)
            for row in typed:
                output.write(canonical({k: row[k] for k in FIELDS}) + b'\n')
            results.append(dict(source_file_name=scope.source_file_name, source_version_id=scope.source_version_id,
                                source_file_sha256=scope.source_file_sha256, rows=len(typed), quality=dict(quality)))
            del bronze, typed
    receipt = dict(evidence='LOCAL_RECONSTRUCTION_FROM_EXACT_PUBLIC_BYTES_NOT_NATIVE_READ',
                   complete=True, total_source_bytes=total_bytes, sources=results)
    (directory / 'reconstruction_receipt.json').write_bytes(canonical(receipt) + b'\n')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--selection', type=Path, default=ROOT / 'docs/FOUR_WEEK_SELECTION.json')
    parser.add_argument('--private-root', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = reconstruct(load_selection(args.selection).selected, args.private_root)
        print(json.dumps(dict(status='LOCAL_RECONSTRUCTION_COMPLETE', source_count=len(result['sources']),
                              rows=sum(r['rows'] for r in result['sources']))))
        return 0
    except Exception as error:
        print(json.dumps(dict(status='FAILED', error_type=type(error).__name__)), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
