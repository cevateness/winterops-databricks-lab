"""Explicit COMPLETE-version V2 analytics. Rendering never authenticates or executes."""
from dataclasses import asdict, dataclass
import hashlib
import json
import re

from winterops.foundation import PIPELINE_VERSION, QualityPolicy, processing_key
from winterops.gold_products import ntz_clock_index_sql
from winterops.landing import OriginalLanding, VOLUME
from winterops.sources import DATASET, WeeklySource
from winterops.spark_ingestion import AUDIT_TYPES, BRONZE_TYPES, SILVER_TYPES, MANIFEST_TYPES, DevelopmentTargets

DIMENSIONS = ('source_dataset', 'source_file_name', 'source_file_sha256', 'source_version_id',
              'processing_key', 'pipeline_version', 'quality_policy_sha256', 'source_week_start',
              'source_week_end_exclusive', 'original_csv_volume_path')
ADDITIVE = ('observation_count', 'plow_active_observations', 'spreader_active_observations',
            'plow_only_observations', 'spreader_only_observations', 'both_active_observations',
            'neither_active_observations', 'engine_off_observations',
            'engine_off_with_equipment_flag_observations', 'repeated_valid_payload_observations')
HOUR = "CAST(substring(CAST(event_time_unzoned AS STRING),1,13) || ':00:00' AS TIMESTAMP_NTZ)"


def literal(value):
    return "'" + str(value).replace("'", "''") + "'"


@dataclass(frozen=True)
class SelectedVersion:
    source_file_name: str
    source_file_sha256: str
    source_version_id: str
    processing_key: str
    expected_rows: int
    original_csv_volume_path: str
    policy: QualityPolicy = QualityPolicy()
    pipeline_version: str = PIPELINE_VERSION

    def __post_init__(self):
        if not isinstance(self.policy, QualityPolicy):
            raise ValueError('Explicit validated quality policy required')
        source = self.source
        if any(not re.fullmatch('[0-9a-f]{64}', v) for v in
               (self.source_file_sha256, self.source_version_id, self.processing_key)):
            raise ValueError('Exact hashes and keys required')
        if not re.fullmatch('[a-zA-Z0-9_.-]{1,80}', self.pipeline_version):
            raise ValueError('Unsafe pipeline revision')
        expected = hashlib.sha256('\0'.join((DATASET, source.source_file_name, self.source_file_sha256)).encode()).hexdigest()
        key = hashlib.sha256('\0'.join((expected, self.pipeline_version, self.policy.policy_sha256)).encode()).hexdigest()
        landing = OriginalLanding(source, self.source_file_sha256, 1)
        if (expected != self.source_version_id or key != self.processing_key
                or type(self.expected_rows) is not int or not 1 <= self.expected_rows <= 500000
                or self.original_csv_volume_path not in (landing.path, VOLUME + '/' + source.source_file_name)):
            raise ValueError('Inconsistent explicit processing/source/landing selection')

    @property
    def source(self):
        return WeeklySource.from_url('https://opendata.citywindsor.ca/Uploads/' + self.source_file_name)

    @classmethod
    def from_version(cls, version, expected_rows, landing, policy=QualityPolicy()):
        if landing.source != version.source or landing.sha256 != version.source_file_sha256 or landing.byte_count != version.byte_count:
            raise ValueError('Original landing differs from staged source')
        return cls(version.source.source_file_name, version.source_file_sha256, version.version_id,
                   processing_key(version, policy), expected_rows, landing.path, policy)

    def dimensions(self):
        return dict(source_dataset=DATASET, source_file_name=self.source_file_name,
                    source_file_sha256=self.source_file_sha256, source_version_id=self.source_version_id,
                    processing_key=self.processing_key, pipeline_version=self.pipeline_version,
                    quality_policy_sha256=self.policy.policy_sha256, source_week_start=self.source.covered_start,
                    source_week_end_exclusive=self.source.covered_end_exclusive,
                    original_csv_volume_path=self.original_csv_volume_path)


@dataclass(frozen=True)
class UnifiedGold:
    selected: tuple[SelectedVersion, ...]
    allow_mixed_policies: bool = False
    targets: DevelopmentTargets = DevelopmentTargets()

    def __post_init__(self):
        if not isinstance(self.selected, tuple) or not 1 <= len(self.selected) <= 12:
            raise ValueError('Supply 1..12 explicit source processing selections')
        if type(self.allow_mixed_policies) is not bool:
            raise ValueError('Mixed policies require explicit Boolean opt-in')
        if any(not isinstance(s, SelectedVersion) for s in self.selected):
            raise ValueError('Explicit SelectedVersion objects required')
        if (len({s.source_file_name for s in self.selected}) != len(self.selected)
                or len({s.processing_key for s in self.selected}) != len(self.selected)):
            raise ValueError('Ambiguous source revision or policy for one source week')
        ordered = sorted(self.selected, key=lambda s: s.source.covered_start)
        if any(a.source.covered_end_exclusive > b.source.covered_start for a,b in zip(ordered, ordered[1:])):
            raise ValueError('Overlapping selected weeks')
        if len({s.policy.policy_sha256 for s in self.selected}) > 1 and not self.allow_mixed_policies:
            raise ValueError('Mixed policies require explicit opt-in and remain separate grains')

    def view_name(self, product):
        suffix = {'hourly': 'hourly_observations', 'daily': 'daily_activity', 'weekly': 'weekly_quality'}[product]
        return f'{self.targets.catalog}.{self.targets.schema}.winterops_v2_gold_{suffix}'

    def wanted_sql(self):
        rows = []
        for s in self.selected:
            values = s.dimensions()
            values.update(expected_rows=s.expected_rows, long_gap_seconds=s.policy.long_gap_seconds,
                          policy_json=json.dumps(asdict(s.policy)))
            rows.append('SELECT ' + ', '.join((str(v) if type(v) is int else
                        "DATE " + literal(v) if k in ('source_week_start','source_week_end_exclusive') else literal(v))
                        + ' AS ' + k for k,v in values.items()))
        return '\nUNION ALL\n'.join(rows)

    def source_ctes(self):
        # No implicit latest/promotion. Other source revisions/policies are not read.
        bronze_ok = ' AND '.join(f'COALESCE(b.{c} = w.{c},FALSE)' for c in
                                ('source_dataset','source_file_name','source_file_sha256','source_week_start','source_week_end_exclusive'))
        bronze_ok += ' AND ' + ' AND '.join(f'b.{c} IS NOT NULL' for c in BRONZE_TYPES)
        silver_ok = ' AND '.join(f'COALESCE(s.{c} = w.{c},FALSE)' for c in
                                ('source_version_id','source_dataset','source_file_name','source_file_sha256','pipeline_version','quality_policy_sha256','source_week_start','source_week_end_exclusive'))
        silver_ok += ' AND ' + ' AND '.join(f's.{c} IS NOT NULL' for c in AUDIT_TYPES)
        silver_ok += ' AND s.quality_issues IS NOT NULL AND s.quality_warnings IS NOT NULL'
        lineage_ok = ' AND '.join(f'(COALESCE(s.{c}=b.{c},FALSE) OR (s.{c} IS NULL AND b.{c} IS NULL))' for c in AUDIT_TYPES)
        return f"""_wanted AS ({self.wanted_sql()}),
_manifest_check AS (
 SELECT w.processing_key, COUNT(m.processing_key) AS n,
 SUM(CASE WHEN m.status='COMPLETE' AND m.last_successful_stage='COMPLETE' AND m.error_code IS NULL
  AND m.source_version_id=w.source_version_id AND m.source_file_name=w.source_file_name
  AND m.source_file_sha256=w.source_file_sha256 AND m.policy_json=w.policy_json
  AND m.bronze_rows=w.expected_rows AND m.silver_rows=w.expected_rows THEN 1 ELSE 0 END) AS good
 FROM _wanted w LEFT JOIN {self.targets.table('manifest')} m ON m.processing_key=w.processing_key GROUP BY w.processing_key),
_bronze_check AS (
 SELECT w.processing_key, COUNT(b.source_record_number) AS n, COUNT(DISTINCT b.source_record_number) AS unique_n,
 MIN(b.source_record_number) AS first_n, MAX(b.source_record_number) AS last_n,
 SUM(CASE WHEN {bronze_ok} THEN 0 ELSE 1 END) AS bad
 FROM _wanted w LEFT JOIN {self.targets.table('bronze')} b ON b.source_version_id=w.source_version_id GROUP BY w.processing_key),
_silver_check AS (
 SELECT w.processing_key, COUNT(s.source_record_number) AS n, COUNT(DISTINCT s.source_record_number) AS unique_n,
 MIN(s.source_record_number) AS first_n, MAX(s.source_record_number) AS last_n,
 SUM(CASE WHEN {silver_ok} AND s.quality_status IN ('HEADER','VALID','INVALID')
  AND (s.quality_status<>'VALID' OR (s.truck_id IS NOT NULL AND length(trim(s.truck_id))>0
   AND s.event_time_unzoned >= CAST(w.source_week_start AS TIMESTAMP_NTZ)
   AND s.event_time_unzoned < CAST(w.source_week_end_exclusive AS TIMESTAMP_NTZ)
   AND s.latitude BETWEEN -90 AND 90 AND s.longitude BETWEEN -180 AND 180
   AND s.plow_active IS NOT NULL AND s.spreader_active IS NOT NULL AND s.engine_active IS NOT NULL))
  AND ((s.quality_status='HEADER' AND s.is_repeated_header AND s.quality_issues='REPEATED_HEADER')
   OR (s.quality_status<>'HEADER' AND NOT s.is_repeated_header))
  THEN 0 ELSE 1 END) AS bad
 FROM _wanted w LEFT JOIN {self.targets.table('silver')} s ON s.processing_key=w.processing_key GROUP BY w.processing_key),
_lineage_check AS (SELECT w.processing_key, SUM(CASE WHEN {lineage_ok} THEN 0 ELSE 1 END) AS bad
 FROM _wanted w JOIN {self.targets.table('bronze')} b ON b.source_version_id=w.source_version_id
 JOIN {self.targets.table('silver')} s ON s.processing_key=w.processing_key AND s.source_record_number=b.source_record_number GROUP BY w.processing_key),
_frequencies AS (SELECT s.processing_key,s.record_sha256,COUNT(*) AS n
 FROM {self.targets.table('silver')} s JOIN _wanted w ON w.processing_key=s.processing_key GROUP BY s.processing_key,s.record_sha256),
_frequency_check AS (SELECT f.processing_key,SUM(CASE WHEN s.payload_occurrences=f.n
 AND s.has_repeated_payload=(f.n>1) THEN 0 ELSE 1 END) AS bad FROM _frequencies f
 JOIN {self.targets.table('silver')} s ON s.processing_key=f.processing_key AND s.record_sha256=f.record_sha256 GROUP BY f.processing_key),
_selection_gate AS (
 SELECT CASE WHEN COUNT(*)={len(self.selected)} AND SUM(CASE WHEN m.n=1 AND m.good=1
  AND b.n=w.expected_rows AND b.unique_n=w.expected_rows AND b.first_n=1 AND b.last_n=w.expected_rows AND b.bad=0
  AND s.n=w.expected_rows AND s.unique_n=w.expected_rows AND s.first_n=1 AND s.last_n=w.expected_rows AND s.bad=0
  AND l.bad=0 AND f.bad=0
  THEN 0 ELSE 1 END)=0 THEN 1 ELSE CAST(raise_error('V2 Gold selected COMPLETE scope or contract mismatch') AS INT) END AS ok
 FROM _wanted w JOIN _manifest_check m ON m.processing_key=w.processing_key
 JOIN _bronze_check b ON b.processing_key=w.processing_key JOIN _silver_check s ON s.processing_key=w.processing_key
 LEFT JOIN _lineage_check l ON l.processing_key=w.processing_key LEFT JOIN _frequency_check f ON f.processing_key=w.processing_key),
_selected AS (SELECT s.*, w.original_csv_volume_path, w.long_gap_seconds
 FROM {self.targets.table('silver')} s JOIN _wanted w ON s.processing_key=w.processing_key
 CROSS JOIN _selection_gate g WHERE g.ok=1),
_valid AS (SELECT *, {HOUR} AS source_local_naive_hour, CAST(event_time_unzoned AS DATE) AS source_local_naive_day,
 COUNT(*) OVER (PARTITION BY processing_key,record_sha256) AS valid_payload_occurrences
 FROM _selected WHERE quality_status='VALID')"""

    @staticmethod
    def activity():
        return """COUNT(*) AS observation_count,
 COUNT(CASE WHEN plow_active THEN 1 END) AS plow_active_observations,
 COUNT(CASE WHEN spreader_active THEN 1 END) AS spreader_active_observations,
 COUNT(CASE WHEN plow_active AND NOT spreader_active THEN 1 END) AS plow_only_observations,
 COUNT(CASE WHEN spreader_active AND NOT plow_active THEN 1 END) AS spreader_only_observations,
 COUNT(CASE WHEN plow_active AND spreader_active THEN 1 END) AS both_active_observations,
 COUNT(CASE WHEN NOT plow_active AND NOT spreader_active THEN 1 END) AS neither_active_observations,
 COUNT(CASE WHEN NOT engine_active THEN 1 END) AS engine_off_observations,
 COUNT(CASE WHEN NOT engine_active AND (plow_active OR spreader_active) THEN 1 END) AS engine_off_with_equipment_flag_observations,
 COUNT(CASE WHEN valid_payload_occurrences>1 THEN 1 END) AS repeated_valid_payload_observations,
 COUNT(DISTINCT truck_id) AS observed_identifier_count"""

    def product_ctes(self, published=False):
        dims = ', '.join(DIMENSIONS)
        if published:
            return ',\n'.join(f'_{p} AS (SELECT * FROM {self.view_name(p)})' for p in ('hourly','daily','weekly'))
        hourly = f"_hourly AS (SELECT {dims}, source_local_naive_hour, {self.activity()} FROM _valid GROUP BY {dims}, source_local_naive_hour)"
        daily = f"""_day_counts AS (SELECT {dims}, source_local_naive_day, {self.activity()},
 COUNT(DISTINCT source_local_naive_hour) AS hours_containing_telemetry FROM _valid GROUP BY {dims}, source_local_naive_day),
_day_peaks AS (SELECT processing_key,CAST(source_local_naive_hour AS DATE) AS day,MAX(observed_identifier_count) AS maximum_hourly_identifiers
 FROM _hourly GROUP BY processing_key,CAST(source_local_naive_hour AS DATE)),
_daily AS (SELECT a.*,p.maximum_hourly_identifiers FROM _day_counts a JOIN _day_peaks p
 ON a.processing_key=p.processing_key AND a.source_local_naive_day=p.day)"""
        weekly = f"""_times AS (SELECT processing_key, source_record_number, long_gap_seconds,
 {ntz_clock_index_sql('event_time_unzoned')} AS clock_us,
 LAG({ntz_clock_index_sql('event_time_unzoned')}) OVER (PARTITION BY processing_key,truck_id ORDER BY event_time_unzoned,source_record_number) AS prior_us FROM _valid),
_gaps AS (SELECT processing_key, COUNT(prior_us) AS consecutive_timestamp_pairs,
 COUNT(CASE WHEN clock_us=prior_us THEN 1 END) AS zero_gap_pairs,
 COUNT(CASE WHEN clock_us-prior_us>long_gap_seconds*1000000 THEN 1 END) AS long_gap_pairs,
 CAST(MAX(clock_us-prior_us) AS DOUBLE)/1000000 AS maximum_source_clock_gap_seconds FROM _times GROUP BY processing_key),
_payloads AS (SELECT processing_key,record_sha256,COUNT(*) AS n FROM _valid GROUP BY processing_key,record_sha256),
_duplicates AS (SELECT processing_key,COUNT(CASE WHEN n>1 THEN 1 END) AS repeated_valid_payload_groups,
 SUM(n-1) AS excess_valid_payload_observations FROM _payloads GROUP BY processing_key),
_valid_week AS (SELECT {dims}, {self.activity()}, COUNT(DISTINCT source_local_naive_hour) AS hours_containing_telemetry,
 COUNT(DISTINCT source_local_naive_day) AS days_containing_telemetry FROM _valid GROUP BY {dims}),
_quality AS (SELECT processing_key,COUNT(*) AS silver_rows,
 COUNT(CASE WHEN quality_status='HEADER' THEN 1 END) AS header_rows,
 COUNT(CASE WHEN quality_status='VALID' THEN 1 END) AS valid_rows,
 COUNT(CASE WHEN quality_status='INVALID' THEN 1 END) AS invalid_rows,
 COUNT(CASE WHEN quality_status<>'VALID' THEN 1 END) AS quarantine_rows,
 COUNT(CASE WHEN quality_status='INVALID' AND (quality_issues LIKE '%INVALID_LATITUDE%' OR quality_issues LIKE '%INVALID_LONGITUDE%') THEN 1 END) AS invalid_coordinate_rows,
 COUNT(CASE WHEN quality_status<>'HEADER' AND quality_warnings LIKE '%OUTSIDE_REVIEW_ENVELOPE%' THEN 1 END) AS outside_review_envelope_rows
 FROM _selected GROUP BY processing_key),
_week_peaks AS (SELECT processing_key,MAX(observed_identifier_count) AS peak FROM _hourly GROUP BY processing_key),
_weekly AS (SELECT {', '.join('w.'+d for d in DIMENSIONS)}, w.expected_rows AS bronze_rows,
 q.silver_rows,q.header_rows,q.valid_rows,q.invalid_rows,q.quarantine_rows,q.invalid_coordinate_rows,q.outside_review_envelope_rows,
 {', '.join('COALESCE(v.'+m+',0) AS '+m for m in (*ADDITIVE,'observed_identifier_count','hours_containing_telemetry','days_containing_telemetry'))},
 COALESCE(p.peak,0) AS maximum_hourly_identifiers,
 COALESCE(d.repeated_valid_payload_groups,0) AS repeated_valid_payload_groups,
 COALESCE(d.excess_valid_payload_observations,0) AS excess_valid_payload_observations,
 COALESCE(g.consecutive_timestamp_pairs,0) AS consecutive_timestamp_pairs, COALESCE(g.zero_gap_pairs,0) AS zero_gap_pairs,
 COALESCE(g.long_gap_pairs,0) AS long_gap_pairs,g.maximum_source_clock_gap_seconds
 FROM _wanted w CROSS JOIN _selection_gate gate JOIN _quality q ON q.processing_key=w.processing_key
 LEFT JOIN _valid_week v ON v.processing_key=w.processing_key LEFT JOIN _duplicates d ON d.processing_key=w.processing_key
 LEFT JOIN _gaps g ON g.processing_key=w.processing_key LEFT JOIN _week_peaks p ON p.processing_key=w.processing_key WHERE gate.ok=1)"""
        return ',\n'.join((hourly,daily,weekly))

    def query(self, product, *, ordered=True):
        if product not in ('hourly','daily','weekly'): raise ValueError('Unknown unified product')
        time = {'hourly': ', source_local_naive_hour','daily': ', source_local_naive_day','weekly': ''}[product]
        order = f' ORDER BY source_week_start{time}' if ordered else ''
        return f'WITH {self.source_ctes()},\n{self.product_ctes()}\nSELECT * FROM _{product}{order}'

    def selection_guard(self):
        return f'WITH {self.source_ctes()} SELECT assert_true(ok=1, \'Selected scope failed\') AS selection_check FROM _selection_gate'

    def reconcile(self, published=False):
        """Candidate hierarchy checks; published=True retains the legacy query.

        Use published_comparison(product) for bounded native postflight requests.
        """
        daily_bad = ' OR '.join(f'COALESCE(h.{m},0)<>d.{m}' for m in ADDITIVE)
        weekly_bad = ' OR '.join(f'COALESCE(h.{m},0)<>w.{m} OR COALESCE(d.{m},0)<>w.{m}' for m in ADDITIVE)
        sums = ', '.join(f'SUM({m}) AS {m}' for m in ADDITIVE)
        composition = "observation_count<>plow_only_observations+spreader_only_observations+both_active_observations+neither_active_observations OR plow_active_observations<>plow_only_observations+both_active_observations OR spreader_active_observations<>spreader_only_observations+both_active_observations"
        nonnegative = ' OR '.join(f'{m}<0 OR {m}>observation_count' for m in ADDITIVE[1:]) + ' OR observation_count<0 OR observed_identifier_count<0 OR observed_identifier_count>observation_count'
        comparison = ''
        compare_condition = ''
        if published:
            expected = self.product_ctes()
            for product in ('hourly','daily','weekly'):
                expected = expected.replace('_'+product, '_expected_'+product)
            comparison = expected + ',\n'
            for product in ('hourly','daily','weekly'):
                comparison += f'_{product}_missing AS (SELECT * FROM _expected_{product} EXCEPT ALL SELECT * FROM _{product}),\n'
                comparison += f'_{product}_extra AS (SELECT * FROM _{product} EXCEPT ALL SELECT * FROM _expected_{product}),\n'
                compare_condition += f' AND (SELECT COUNT(*) FROM _{product}_missing)=0 AND (SELECT COUNT(*) FROM _{product}_extra)=0 AND (SELECT COUNT(*) FROM _{product})=(SELECT COUNT(*) FROM _expected_{product})'
        return f"""WITH {self.source_ctes()}, {self.product_ctes(published)},
{comparison}
_hour_days AS (SELECT processing_key,CAST(source_local_naive_hour AS DATE) AS day,{sums} FROM _hourly GROUP BY processing_key,CAST(source_local_naive_hour AS DATE)),
_hour_weeks AS (SELECT processing_key,{sums} FROM _hourly GROUP BY processing_key),
_day_weeks AS (SELECT processing_key,{sums} FROM _daily GROUP BY processing_key),
_category_errors AS (SELECT processing_key FROM _hourly WHERE {composition} OR {nonnegative}
 UNION ALL SELECT processing_key FROM _daily WHERE {composition} OR {nonnegative} UNION ALL SELECT processing_key FROM _weekly WHERE {composition} OR {nonnegative}),
_day_errors AS (SELECT d.processing_key FROM _daily d LEFT JOIN _hour_days h ON h.processing_key=d.processing_key AND h.day=d.source_local_naive_day WHERE {daily_bad}),
_week_errors AS (SELECT w.processing_key FROM _weekly w LEFT JOIN _hour_weeks h ON h.processing_key=w.processing_key
 LEFT JOIN _day_weeks d ON d.processing_key=w.processing_key WHERE {weekly_bad}
 OR w.bronze_rows<>w.silver_rows OR w.silver_rows<>w.header_rows+w.valid_rows+w.invalid_rows
 OR w.quarantine_rows<>w.header_rows+w.invalid_rows OR w.observation_count<>w.valid_rows)
SELECT assert_true((SELECT ok FROM _selection_gate)=1 AND (SELECT COUNT(*) FROM _weekly)={len(self.selected)}
 AND (SELECT COUNT(*) FROM _category_errors)=0 AND (SELECT COUNT(*) FROM _day_errors)=0
 AND (SELECT COUNT(*) FROM _week_errors)=0{compare_condition},'V2 Gold reconciliation failed') AS reconciliation_check"""

    def publication(self):
        # Three non-atomic fail-if-exists operations; no replacement or legacy redirection.
        return tuple(f'CREATE VIEW {self.view_name(p)} AS\n{self.query(p,ordered=False)}' for p in ('hourly','daily','weekly'))

    def published_comparison(self, product):
        """One product per bounded request; full multiplicities and every column.

        The combined three-product verification exceeded the native 30-second
        wait. Rendering these SELECTs does not authorize a retry or execution.
        """
        if product not in ('hourly','daily','weekly'):
            raise ValueError('Unknown unified product')
        return f"""WITH {self.source_ctes()}, {self.product_ctes()},
_published AS (SELECT * FROM {self.view_name(product)}),
_missing AS (SELECT * FROM _{product} EXCEPT ALL SELECT * FROM _published),
_extra AS (SELECT * FROM _published EXCEPT ALL SELECT * FROM _{product})
SELECT assert_true((SELECT ok FROM _selection_gate)=1
 AND (SELECT COUNT(*) FROM _missing)=0 AND (SELECT COUNT(*) FROM _extra)=0
 AND (SELECT COUNT(*) FROM _published)=(SELECT COUNT(*) FROM _{product}),
 'Published {product} multiset differs from candidate') AS published_{product}_check,
 (SELECT COUNT(*) FROM _published) AS aggregate_rows"""

    def dashboard(self):
        weekly, daily, hourly = (self.view_name(p) for p in ('weekly','daily','hourly'))
        return {'three_week_comparison': f'SELECT * FROM {weekly} ORDER BY source_week_start LIMIT 12',
                'daily_equipment': f'SELECT * FROM {daily} ORDER BY source_week_start,source_local_naive_day LIMIT 84',
                'weekly_quality': f'SELECT source_week_start,source_version_id,processing_key,quality_policy_sha256,header_rows,invalid_rows,invalid_coordinate_rows,outside_review_envelope_rows,repeated_valid_payload_observations,long_gap_pairs FROM {weekly} ORDER BY source_week_start LIMIT 12',
                **{'hourly_'+s.source.covered_start: f"SELECT source_week_start,source_version_id,processing_key,quality_policy_sha256,source_local_naive_hour,observation_count,plow_active_observations,spreader_active_observations,observed_identifier_count FROM {hourly} WHERE processing_key='{s.processing_key}' ORDER BY source_local_naive_hour LIMIT 168" for s in self.selected}}


def validate_schemas(bronze, silver, manifest):
    for actual, expected in ((bronze,BRONZE_TYPES),(silver,SILVER_TYPES),(manifest,MANIFEST_TYPES)):
        if {k:str(v).upper() for k,v in actual.items()} != expected:
            raise ValueError('V2 native schema contract mismatch')


def load_selection(path):
    """A checked-in selection contains public identities only, never local paths/auth."""
    from pathlib import Path
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    selected = []
    for row in data['selected']:
        row = dict(row)
        if 'policy' in row:
            row['policy'] = QualityPolicy(**row['policy'])
        selected.append(SelectedVersion(**row))
    mixed = data.get('allow_mixed_policies', False)
    if type(mixed) is not bool:
        raise ValueError('Mixed-policy selection requires an explicit Boolean')
    return UnifiedGold(tuple(selected), allow_mixed_policies=mixed)
