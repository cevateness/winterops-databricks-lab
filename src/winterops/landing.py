"""Original CSV identity and immutable Volume landing plans; never performs I/O."""
from dataclasses import dataclass
import re

from winterops.sources import WeeklySource

VOLUME = '/Volumes/workspace/default/winterops_raw'


@dataclass(frozen=True)
class OriginalLanding:
    source: WeeklySource
    sha256: str
    byte_count: int
    existing_path: str | None = None

    def __post_init__(self):
        if (not re.fullmatch('[0-9a-f]{64}', self.sha256)
                or type(self.byte_count) is not int or not 1 <= self.byte_count <= 64 * 1024 * 1024):
            raise ValueError('Exact bounded original CSV required')
        if self.existing_path is not None and self.existing_path != VOLUME + '/' + self.source.source_file_name:
            raise ValueError('Reuse only the exact existing original CSV path')

    @property
    def path(self):
        return self.existing_path or f'{VOLUME}/original_csv/{self.source.source_file_name}/{self.sha256}/{self.source.source_file_name}'

    def plan(self):
        return dict(kind='original_csv', source_file_name=self.source.source_file_name,
                    source_url=self.source.source_url, source_file_sha256=self.sha256,
                    bytes=self.byte_count, volume_path=self.path,
                    action='VERIFY_AND_REUSE' if self.existing_path else 'UPLOAD_IF_ABSENT_ELSE_VERIFY_IDENTICAL',
                    overwrite=False, source_week_start=self.source.covered_start,
                    source_week_end_exclusive=self.source.covered_end_exclusive)

    def fingerprint_sql(self):
        return f"""SELECT assert_true(COUNT(*) = 1 AND MIN(sha2(content,256)) = '{self.sha256}'
 AND MIN(length) = {self.byte_count} AND MAX(length) = {self.byte_count},
 'Original CSV bytes or source identity changed') AS original_csv_check
FROM read_files('{self.path}', format => 'binaryFile')"""
