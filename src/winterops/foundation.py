"""V2 portable observation-preserving Bronze/Silver and aggregate diagnostics."""
from __future__ import annotations

from collections import Counter, defaultdict
import csv
from dataclasses import asdict, dataclass
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import re

from winterops.sources import SourceVersion

SOURCE_COLUMNS = ('Latitude','Longitude','Date time','Plow status','Spreader status','Engine status','Truck')
PIPELINE_VERSION = 'windsor-foundation-v2.1'
TIMESTAMP_PATTERN = r'[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}(?:[.][0-9]{1,6})?'
NUMBER_PATTERN = r'[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)([eE][+-]?[0-9]+)?'


def canonical(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


@dataclass(frozen=True)
class QualityPolicy:
    # An intentionally broad review envelope, NOT a City boundary/geofence.
    review_lat_min: float = 42.1
    review_lat_max: float = 42.5
    review_lon_min: float = -83.3
    review_lon_max: float = -82.6
    nominal_interval_seconds: int = 15
    long_gap_seconds: int = 1800
    dense_hour_observations: int = 1000

    def __post_init__(self):
        bounds = (self.review_lat_min,self.review_lat_max,self.review_lon_min,self.review_lon_max)
        if any(type(v) not in (int,float) or not math.isfinite(v) for v in bounds):
            raise ValueError('Review bounds must be finite numbers')
        if not (-90 <= bounds[0] < bounds[1] <= 90 and -180 <= bounds[2] < bounds[3] <= 180):
            raise ValueError('Invalid review envelope')
        for key in ('nominal_interval_seconds','long_gap_seconds','dense_hour_observations'):
            if type(getattr(self,key)) is not int or not 1 <= getattr(self,key) <= 1000000:
                raise ValueError('Invalid diagnostic threshold')
        if self.long_gap_seconds < self.nominal_interval_seconds:
            raise ValueError('Gap threshold precedes nominal interval')

    @property
    def policy_sha256(self):
        return hashlib.sha256(canonical(asdict(self)).encode()).hexdigest()


def processing_key(version, policy):
    return hashlib.sha256('\0'.join((version.version_id, PIPELINE_VERSION, policy.policy_sha256)).encode()).hexdigest()


def read_bronze(version: SourceVersion, max_records=500000):
    """One row per parsed record after the outer header, including blanks/headers.

    csv.reader record ordinal and physical ending line are retained, including
    quoted multiline fields. Malformed widths remain rows; broken quoting/UTF-8
    fails the whole attempt before publication. Extra/missing columns fail closed.
    """
    if type(max_records) is not int or max_records < 1:
        raise ValueError('Invalid record bound')
    version.verify()
    with Path(version.local_path).open(encoding='utf-8-sig', newline='') as raw:
        reader = csv.reader(raw, strict=True)
        columns = next(reader, None)
        if not columns or len(columns) != len(set(columns)) or set(columns) != set(SOURCE_COLUMNS):
            raise ValueError('SOURCE_SCHEMA_DRIFT')
        for number, values in enumerate(reader, 1):
            if number > max_records:
                raise ValueError('SOURCE_RECORD_BOUND_EXCEEDED')
            payload = {key:values[i] if i < len(values) else None for i,key in enumerate(columns)}
            text = canonical(payload)
            yield dict(source_version_id=version.version_id, source_dataset=version.source.source_dataset,
                source_file_name=version.source.source_file_name, source_url=version.source.source_url,
                source_file_path=version.local_path, source_file_sha256=version.source_file_sha256,
                source_week_start=version.source.covered_start, source_week_end_exclusive=version.source.covered_end_exclusive,
                retrieved_at_utc=version.retrieved_at_utc, ingested_at_utc=version.retrieved_at_utc,
                source_record_number=number, source_line_end=reader.line_num,
                csv_parse_issues='' if len(values)==len(columns) else 'CSV_WIDTH_MISMATCH',
                raw_values_json=canonical(values), raw_record_json=text,
                record_sha256=hashlib.sha256(text.encode()).hexdigest())
    version.verify()


def _timestamp(value):
    if not isinstance(value,str) or not re.fullmatch(TIMESTAMP_PATTERN,value.strip(' ')):
        return None
    try:
        return datetime.fromisoformat(value.strip(' '))
    except ValueError:
        return None


def _number(value):
    if not isinstance(value,str) or not re.fullmatch(NUMBER_PATTERN,value.strip(' ')):
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (ValueError,TypeError):
        return None


def _boolean(value):
    text = value.strip(' ').upper() if isinstance(value,str) else ''
    return {'TRUE':True,'FALSE':False}.get(text)


def silver_rows(bronze, version: SourceVersion, policy=QualityPolicy()):
    frequencies = Counter(row['record_sha256'] for row in bronze)
    start, end = datetime.fromisoformat(version.source.covered_start), datetime.fromisoformat(version.source.covered_end_exclusive)
    result = []
    for row in bronze:
        if row['source_version_id'] != version.version_id:
            raise ValueError('MIXED_SOURCE_VERSIONS')
        payload = json.loads(row['raw_record_json'])
        header = all(isinstance(payload.get(key),str) and payload[key].strip(' ').upper()==key.upper()
                     for key in ('Latitude','Longitude','Date time','Truck'))
        truck = payload.get('Truck')
        event = _timestamp(payload.get('Date time'))
        lat, lon = _number(payload.get('Latitude')), _number(payload.get('Longitude'))
        p,s,e = (_boolean(payload.get(key)) for key in ('Plow status','Spreader status','Engine status'))
        issues = []
        if row['csv_parse_issues']:
            issues.append(row['csv_parse_issues'])
        if truck is None or not truck.strip(' '): issues.append('MISSING_TRUCK')
        if lat is None or not -90 <= lat <= 90: issues.append('INVALID_LATITUDE')
        if lon is None or not -180 <= lon <= 180: issues.append('INVALID_LONGITUDE')
        if event is None: issues.append('INVALID_TIMESTAMP')
        elif not start <= event < end: issues.append('TIMESTAMP_OUTSIDE_SOURCE_WEEK')
        for key,value in (('PLOW',p),('SPREADER',s),('ENGINE',e)):
            if value is None: issues.append('INVALID_'+key+'_STATUS')
        warnings = []
        coordinate_valid = lat is not None and lon is not None and -90<=lat<=90 and -180<=lon<=180
        if not header and coordinate_valid and not (policy.review_lat_min<=lat<=policy.review_lat_max and policy.review_lon_min<=lon<=policy.review_lon_max):
            warnings.append('OUTSIDE_REVIEW_ENVELOPE')
        if not header and truck is not None and truck != truck.strip(' '): warnings.append('TRUCK_WHITESPACE')
        if not header and e is False and (p is True or s is True): warnings.append('ENGINE_OFF_EQUIPMENT_FLAG')
        typed = {key:value for key,value in row.items() if key not in ('raw_values_json','raw_record_json')}
        typed.update(processing_key=processing_key(version,policy), pipeline_version=PIPELINE_VERSION,
            quality_policy_sha256=policy.policy_sha256, truck_id=truck,
            event_time_unzoned=event.isoformat(sep=' ') if event else None, latitude=lat, longitude=lon,
            plow_active=p, spreader_active=s, engine_active=e, payload_occurrences=frequencies[row['record_sha256']],
            has_repeated_payload=frequencies[row['record_sha256']]>1, is_repeated_header=header,
            quality_status='HEADER' if header else 'INVALID' if issues else 'VALID',
            quality_issues='REPEATED_HEADER' if header else ';'.join(issues), quality_warnings=';'.join(warnings))
        result.append(typed)
    return result


def aggregate_quality(bronze, silver, version, policy=QualityPolicy()):
    """Only aggregates leave this function. Never return raw IDs or coordinates."""
    if len(bronze) != len(silver) or not bronze:
        raise ValueError('BRONZE_SILVER_COUNT_MISMATCH_OR_EMPTY')
    if [r['source_record_number'] for r in bronze] != [r['source_record_number'] for r in silver]:
        raise ValueError('OBSERVATION_IDENTITY_MISMATCH')
    classes = Counter(row['quality_status'] for row in silver)
    if set(classes)-{'HEADER','VALID','INVALID'} or any(
            a['record_sha256']!=b['record_sha256'] or a['source_version_id']!=version.version_id
            or b['source_version_id']!=version.version_id for a,b in zip(bronze,silver)):
        raise ValueError('SILVER_CLASSIFICATION_OR_LINEAGE_MISMATCH')
    valid = [row for row in silver if row['quality_status']=='VALID']
    by_id, by_hour, by_day = defaultdict(list), defaultdict(set), defaultdict(set)
    ties, payloads = defaultdict(set), defaultdict(list)
    for row in valid:
        stamp=datetime.fromisoformat(row['event_time_unzoned'])
        by_id[row['truck_id']].append(stamp)
        by_hour[stamp.replace(minute=0,second=0,microsecond=0).isoformat(sep=' ')].add(row['truck_id'])
        by_day[stamp.date().isoformat()].add(row['truck_id'])
        ties[(row['truck_id'],stamp)].add(row['record_sha256'])
        payloads[row['record_sha256']].append(row)
    gaps, days, dense_hours = [], Counter(), 0
    for identifier,times in by_id.items():
        ordered=sorted(times)
        days[len({t.date() for t in ordered})]+=1
        for a,b in zip(ordered,ordered[1:]):
            gaps.append((b-a).total_seconds())
        dense_hours+=sum(n>policy.dense_hour_observations for n in Counter(t.replace(minute=0,second=0,microsecond=0) for t in times).values())
    missing=Counter()
    for row in bronze:
        if silver[row['source_record_number']-1]['quality_status']=='HEADER': continue
        for key,value in json.loads(row['raw_record_json']).items():
            if value is None or not value.strip(' '): missing[key]+=1
    return dict(source_file_name=version.source.source_file_name, source_url=version.source.source_url,
        source_file_sha256=version.source_file_sha256, source_version_id=version.version_id,
        covered_start=version.source.covered_start, covered_end_exclusive=version.source.covered_end_exclusive,
        retrieved_at_utc=version.retrieved_at_utc, source_bytes=version.byte_count,
        processing_key=processing_key(version,policy), pipeline_version=PIPELINE_VERSION,
        quality_policy=asdict(policy), quality_policy_sha256=policy.policy_sha256,
        bronze_rows=len(bronze), silver_rows=len(silver), header_rows=classes['HEADER'], valid_rows=classes['VALID'], invalid_rows=classes['INVALID'],
        csv_width_mismatch_rows=sum(bool(row['csv_parse_issues']) for row in bronze),
        required_source_columns=list(SOURCE_COLUMNS),
        missing_values_excluding_headers=dict(sorted(missing.items())),
        invalid_issue_counts=dict(sorted(Counter(issue for row in silver if row['quality_status']=='INVALID' for issue in row['quality_issues'].split(';')).items())),
        warning_counts=dict(sorted(Counter(w for row in silver for w in row['quality_warnings'].split(';') if w).items())),
        status_counts_excluding_headers={key:{label:sum(row[key] is value for row in silver if row['quality_status']!='HEADER') for label,value in [('true',True),('false',False),('unknown',None)]} for key in ('plow_active','spreader_active','engine_active')},
        distinct_valid_identifiers=len(by_id), hourly_buckets=len(by_hour),
        minimum_hourly_identifiers=min(map(len,by_hour.values()),default=0), maximum_hourly_identifiers=max(map(len,by_hour.values()),default=0),
        daily_identifier_counts=[dict(source_local_naive_day=day,observed_identifier_count=len(ids)) for day,ids in sorted(by_day.items())],
        identifier_reporting_days=[dict(days_with_observations=day,identifier_count=count) for day,count in sorted(days.items())],
        valid_identifier_format_counts={'digits_only':sum(str(k).isdigit() for k in by_id),'other':sum(not str(k).isdigit() for k in by_id)},
        first_valid_source_time=min((row['event_time_unzoned'] for row in valid),default=None),
        last_valid_source_time=max((row['event_time_unzoned'] for row in valid),default=None),
        repeated_valid_payload_groups=sum(len(rows)>1 for rows in payloads.values()),
        repeated_valid_payload_observations=sum(len(rows) for rows in payloads.values() if len(rows)>1),
        excess_valid_payload_observations=sum(len(rows)-1 for rows in payloads.values()),
        conflicting_identifier_timestamp_groups=sum(len(hashes)>1 for hashes in ties.values()),
        consecutive_valid_timestamp_pairs=len(gaps), zero_gap_pairs=sum(g==0 for g in gaps),
        positive_below_nominal_pairs=sum(0<g<policy.nominal_interval_seconds for g in gaps),
        nominal_interval_pairs=sum(g==policy.nominal_interval_seconds for g in gaps),
        above_nominal_within_threshold_pairs=sum(policy.nominal_interval_seconds<g<=policy.long_gap_seconds for g in gaps),
        long_gap_pairs=sum(g>policy.long_gap_seconds for g in gaps),
        minimum_positive_source_clock_gap_seconds=min((g for g in gaps if g>0),default=None),
        maximum_source_clock_gap_seconds=max(gaps,default=None), dense_identifier_hours=dense_hours,
        reconciliation='PASS', timestamp_semantics='source-local/naive; timezone unverified')
