#!/usr/bin/env python3
"""Inspect an untrusted CSV's raw schema and simple quality signals without Pandas.

Example: python scripts/inspect_csv.py data/synthetic/snowplow_demo_synthetic.csv
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path


def inspect_csv(path: Path, sample_limit: int = 3) -> dict:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    if sample_limit < 0:
        raise ValueError('sample_limit must be >= 0')

    digest = hashlib.sha256()
    with path.open('rb') as binary:
        for chunk in iter(lambda: binary.read(1024 * 1024), b''):
            digest.update(chunk)

    with path.open('r', encoding='utf-8-sig', newline='') as f:
        reader = csv.reader(f)
        headers = next(reader, None)
        if not headers:
            raise ValueError('Missing CSV header row')
        counts = [0] * len(headers)
        malformed = 0
        row_count = 0
        examples = []
        for row in reader:
            if not row:  # ignore fully blank lines
                continue
            row_count += 1
            if len(row) != len(headers):
                malformed += 1
            for i, value in enumerate(row[:len(headers)]):
                if not value.strip():
                    counts[i] += 1
            if len(row) < len(headers):
                for i in range(len(row), len(headers)):
                    counts[i] += 1
            if len(examples) < sample_limit:
                examples.append(dict(zip(headers, row)))

    return {
        'file': path.name,
        'bytes': path.stat().st_size,
        'sha256': digest.hexdigest(),
        'rows': row_count,
        'columns': headers,
        'duplicate_headers': sorted({h for h in headers if headers.count(h) > 1}),
        'empty_header_positions_0_based': [i for i, h in enumerate(headers) if not h.strip()],
        'malformed_row_count': malformed,
        'empty_cell_counts_by_column_position': counts,
        'examples': examples,
        'warning': 'Samples may contain sensitive data; review before sharing. No datatype or time zone inferred.',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file', type=Path)
    parser.add_argument('--sample', type=int, default=3, help='Sample rows to include (default: 3, use 0 to avoid printing raw records)')
    parser.add_argument('--output', type=Path, default=None, help='Optional JSON report path')
    args = parser.parse_args()
    report = inspect_csv(args.file, sample_limit=args.sample)
    text = json.dumps(report, indent=2, ensure_ascii=False)
    print(text)
    if args.output:
        args.output.write_text(text + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
