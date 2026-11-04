"""Private local reconstruction using synthetic CSVs; no network or native I/O."""
from dataclasses import replace
import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from reconstruct_weather_projection import reconstruct
from winterops.foundation import SOURCE_COLUMNS
from winterops.landing import OriginalLanding
from winterops.sources import LocalStager, WeeklySource
from winterops.unified_gold import SelectedVersion
from winterops.weather import WeatherContractError


class WeatherReconstructionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        source = WeeklySource.from_url('https://opendata.citywindsor.ca/Uploads/snowplow-2026-01-05_2026-01-11.csv')
        raw = self.root / 'synthetic.csv'
        with raw.open('w', newline='') as output:
            writer = csv.writer(output)
            writer.writerow(SOURCE_COLUMNS)
            point = ['42.3', '-83.0', '2026-01-05 00:00:00', 'True', 'False', 'True', 'SYNTHETIC_PRIVATE_ID']
            writer.writerows([point, point, list(SOURCE_COLUMNS)])
        self.version, _ = LocalStager(self.root / 'source').adopt(source, raw)
        self.scope = SelectedVersion.from_version(self.version, 3, OriginalLanding(source,
                                  self.version.source_file_sha256, self.version.byte_count))

    def test_reconstruction_preserves_multiplicity_and_omits_vehicle_identifiers(self):
        downloader = Mock(return_value=self.version)
        output = self.root / 'projection'
        receipt = reconstruct([self.scope], output, download=downloader)
        rows = [json.loads(line) for line in (output / 'silver_projection.jsonl').read_text().splitlines()]
        self.assertEqual([r['source_record_number'] for r in rows], [1, 2, 3])
        self.assertEqual(receipt['sources'][0]['quality'], dict(VALID=2, HEADER=1))
        self.assertNotIn('SYNTHETIC_PRIVATE_ID', (output / 'silver_projection.jsonl').read_text())
        self.assertTrue(receipt['complete'])
        downloader.assert_called_once()

    def test_existing_output_stops_before_another_download(self):
        output = self.root / 'projection'
        downloader = Mock(return_value=self.version)
        reconstruct([self.scope], output, download=downloader)
        with self.assertRaisesRegex(WeatherContractError, 'OUTPUT_ALREADY_EXISTS'):
            reconstruct([self.scope], output, download=downloader)
        downloader.assert_called_once()

    def test_incorrect_row_contract_has_no_success_receipt(self):
        output = self.root / 'projection'
        with self.assertRaisesRegex(WeatherContractError, 'ROW_COUNT_MISMATCH'):
            reconstruct([replace(self.scope, expected_rows=4)], output, download=lambda _: self.version)
        self.assertFalse((output / 'reconstruction_receipt.json').exists())
