"""Synthetic fixture loader shared by offline product tests only."""
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from winterops.analytics import AnalyticsConfig, SourceScope
from winterops.quality import QualitySnapshot


def fixture():
    raw = json.loads((ROOT / 'data/fixtures/synthetic_gold_products.json').read_text(encoding='utf-8'))
    scope = SourceScope(raw['source_file_sha256'], raw['source_file_name'], raw['source_file_path'],
                        raw['source_dataset'], datetime.fromisoformat(raw['start_unzoned']),
                        datetime.fromisoformat(raw['end_unzoned']))
    config = AnalyticsConfig(scope, QualitySnapshot.from_mapping(raw['expected_summary']))
    frequencies = Counter(row['payload'] for row in raw['observations'])
    rows = []
    for observation in raw['observations']:
        row = {key: value for key, value in observation.items() if key != 'payload'}
        row.update({key: getattr(scope, key) for key in ('source_dataset', 'source_file_name', 'source_file_path', 'source_file_sha256')})
        row.update(record_sha256=hashlib.sha256(observation['payload'].encode()).hexdigest(),
                   payload_occurrences=frequencies[observation['payload']],
                   has_repeated_payload=frequencies[observation['payload']] > 1,
                   quality_status='VALID', quality_issues='', is_repeated_header=False,
                   latitude=42.0, longitude=-83.0)
        rows.append(row)
    return config, rows
