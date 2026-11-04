"""Offline clock corroboration and retrospective summaries of saved matches.

This module never changes the source NTZ contract or promotes a hypothesis to a
verified exporter timezone. No network, native deployment or predictive features.
"""
from collections import defaultdict
from datetime import datetime, timezone
import math

from winterops.weather import require
from winterops.weather_analysis import conditional_instant


def _hour(value):
    stamp = datetime.fromisoformat(value)
    require(stamp.tzinfo is None and stamp.minute == stamp.second == stamp.microsecond == 0,
            'REVIEW_SOURCE_NAIVE_HOUR_REQUIRED')
    return stamp


def review_clock(evidence):
    """Cross-check the recorded MapServer profile and timestamp-only samples.

    A truncated full profile fails; a deliberately limited first/last timestamp
    sample may legitimately have exceededTransferLimit=true. Aggregate MIN/MAX
    epochs and scraper/browser timezone metadata are deliberately not inputs.
    """
    response = evidence['published_profile_response']
    require('error' not in response and not response.get('exceededTransferLimit', False),
            'REVIEW_INCOMPLETE_PUBLISHED_PROFILE')
    start = datetime.fromisoformat(evidence['scope_start'])
    end = datetime.fromisoformat(evidence['scope_end_exclusive'])
    require(start < end, 'REVIEW_SCOPE_REQUIRED')
    profile = {}
    for feature in response['features']:
        attrs = feature['attributes']
        parts = [attrs[f'Expr{i}'] for i in range(1, 5)]
        require(all(type(v) in (int, float) and math.isfinite(v) and int(v) == v for v in parts),
                'REVIEW_PUBLISHED_DATE_PARTS')
        stamp = datetime(*map(int, parts))
        key = stamp.isoformat(' ')
        count = attrs['observation_count']
        require(type(count) is int and count > 0 and start <= stamp < end,
                'REVIEW_PUBLISHED_PROFILE_VALUE')
        require(key not in profile, 'REVIEW_DUPLICATE_PUBLISHED_HOUR')
        profile[key] = count
    local = evidence['local_source_hour_profile']
    require(local and all(type(n) is int and n > 0 and start <= _hour(k) < end
                          for k, n in local.items()), 'REVIEW_LOCAL_PROFILE_VALUE')
    differences = sum(profile.get(k) != local.get(k) for k in set(profile) | set(local))
    metadata = evidence['layer_metadata_projection']
    eastern = (metadata.get('dateFieldsTimeReference') ==
               dict(timeZone='Eastern Standard Time', respectsDaylightSaving=True)
               and metadata.get('datesInUnknownTimezone') is False
               and evidence.get('date_field') == dict(name='record_date', type='esriFieldTypeDate'))
    expected = {}
    for hour in sorted(local):
        week = ((datetime.fromisoformat(hour) - start).days // 7)
        expected.setdefault(week, []).append(hour)
    endpoints = {(hours[0], 'first') for hours in expected.values()} | {
        (hours[-1], 'last') for hours in expected.values()}
    samples = evidence['datetime_only_samples_projection']
    seen = set()
    agreements = {'America/Toronto': 0, 'UTC': 0}
    for sample in samples:
        key = (sample['local_source_hour'], sample['edge'])
        require(sample.get('datetime_only_sample') is True and key in endpoints and key not in seen,
                'REVIEW_ENDPOINT_SAMPLE_CONTRACT')
        seen.add(key)
        ms = sample['published_utc_epoch_ms']
        require(type(ms) is int, 'REVIEW_EPOCH_MILLISECONDS_REQUIRED')
        published = datetime.fromtimestamp(ms / 1000, timezone.utc).replace(minute=0, second=0, microsecond=0)
        for zone in agreements:
            agreements[zone] += published == conditional_instant(_hour(key[0]), zone)
    require(seen == endpoints, 'REVIEW_ENDPOINT_SAMPLES_INCOMPLETE')
    supported = eastern and differences == 0 and agreements['America/Toronto'] == len(endpoints)
    return dict(status='CORROBORATED_FOR_PINNED_SCOPES' if supported else 'INCONCLUSIVE_OR_CONTRADICTORY',
                working_hypothesis='America/Toronto' if supported else None,
                original_csv_export_timezone_confirmed=False,
                original_ntz_contract_changed=False, retrospective_only=True,
                matched_source_hours=len(local), observation_count=sum(local.values()),
                differing_profile_hours=differences, endpoint_samples=len(samples),
                endpoint_hour_agreements=agreements, published_layer_eastern_dst_metadata=eastern,
                scope_start=evidence['scope_start'], scope_end_exclusive=evidence['scope_end_exclusive'],
                excluded_clock_evidence=['date MIN/MAX statistics', 'scraper/browser timezone metadata'])


def summarize_matches(matches):
    """City-day counts and weather ranges at sampled grid/hours, per hypothesis.

    Never sum precipitation across locations or manufacture unobserved days.
    Multiple bins mapped to one weather fact count that fact once. Observation
    counts are additive within a hypothesis; hypotheses are alternatives.
    """
    require(matches, 'REVIEW_MATCHES_REQUIRED')
    paired = defaultdict(dict)
    days = defaultdict(list)
    snapshots = set()
    identity = ('processing_key', 'source_version_id', 'quality_policy_sha256',
                'spatial_bin', 'source_local_hour')
    for row in matches:
        zone = row['timezone_hypothesis']
        require(zone in ('America/Toronto', 'UTC'), 'REVIEW_UNKNOWN_HYPOTHESIS')
        stamp = _hour(row['source_local_hour'])
        key = tuple(row[k] for k in identity)
        require(zone not in paired[key], 'REVIEW_DUPLICATE_MATCH_GRAIN')
        for name in ('observation_count', 'outside_source_review_observations'):
            require(type(row[name]) is int and row[name] >= 0, 'REVIEW_OBSERVATION_COUNT')
        require(0 < row['observation_count'] and row['outside_source_review_observations'] <= row['observation_count'],
                'REVIEW_OBSERVATION_COUNT')
        require(row['retrospective_only'] is True, 'REVIEW_RETROSPECTIVE_REQUIRED')
        paired[key][zone] = row
        snapshots.add(row['weather_snapshot_id'])
        days[(stamp.date().isoformat(), zone)].append(row)
    require(len(snapshots) == 1, 'REVIEW_SINGLE_SNAPSHOT_REQUIRED')
    for pair in paired.values():
        require(set(pair) == {'America/Toronto', 'UTC'}, 'REVIEW_PAIRED_HYPOTHESES_REQUIRED')
        a, b = pair.values()
        require(all(a[k] == b[k] for k in ('observation_count', 'outside_source_review_observations')),
                'REVIEW_PAIRED_COUNTS_DIFFER')
    output = []
    measures = ('temperature_2m_c', 'precipitation_activity_hour_mm', 'snowfall_activity_hour_cm')
    for (day, zone), rows in sorted(days.items()):
        facts = {}
        for row in rows:
            key = (row['grid_id'], row['temperature_valid_time_utc'], row['accumulation_valid_time_utc'])
            values = tuple(row[k] for k in measures)
            require(all(v is None or (type(v) in (int, float) and math.isfinite(v)) for v in values),
                    'REVIEW_WEATHER_VALUE')
            require(all(v is None or v >= 0 for v in values[1:]), 'REVIEW_NEGATIVE_ACCUMULATION')
            require(key not in facts or facts[key] == values, 'REVIEW_CONFLICTING_WEATHER_FACT')
            facts[key] = values
        temperatures = [v[0] for v in facts.values() if v[0] is not None]
        output.append(dict(source_local_day=day, timezone_hypothesis=zone,
                           observation_count=sum(r['observation_count'] for r in rows),
                           outside_source_review_observations=sum(r['outside_source_review_observations'] for r in rows),
                           observed_source_hours=len({r['source_local_hour'] for r in rows}),
                           matched_cell_hours=len(rows), sampled_grid_hours=len(facts),
                           sampled_temperature_min_c=min(temperatures) if temperatures else None,
                           sampled_temperature_max_c=max(temperatures) if temperatures else None,
                           wet_sampled_grid_hours=sum(v[1] is not None and v[1] > 0 for v in facts.values()),
                           snowy_sampled_grid_hours=sum(v[2] is not None and v[2] > 0 for v in facts.values()),
                           missing_measurements=sum(v is None for vs in facts.values() for v in vs)))
    return dict(grain='source_local_day / timezone_hypothesis',
                interpretation='Weather sampled at activity grid/hours; not calendar-day weather or service effort.',
                alignment_status='CONDITIONAL_UNVERIFIED_ACTIVITY_TIMEZONE', retrospective_only=True,
                weather_snapshot_id=next(iter(snapshots)),
                hypothesis_totals={z: sum(r['observation_count'] for r in output if r['timezone_hypothesis'] == z)
                                   for z in ('America/Toronto', 'UTC')}, days=output)
