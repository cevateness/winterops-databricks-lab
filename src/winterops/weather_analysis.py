"""Conditional historical daily joins; no prediction-time feature claims."""
from datetime import date, datetime, time, timedelta, timezone
import math
from zoneinfo import ZoneInfo

from winterops.weather import WeatherContractError, require

UTC = timezone.utc


def conditional_instant(naive, timezone_assumption):
    """Explicit hypothesis only. Reject ambiguous/nonexistent wall times."""
    require(isinstance(naive, datetime) and naive.tzinfo is None, 'ACTIVITY_NAIVE_TIME_REQUIRED')
    zone = ZoneInfo(timezone_assumption)
    possibilities = set()
    for fold in (0, 1):
        candidate = naive.replace(tzinfo=zone, fold=fold).astimezone(UTC)
        if candidate.astimezone(zone).replace(tzinfo=None) == naive:
            possibilities.add(candidate)
    require(len(possibilities) == 1, 'ACTIVITY_AMBIGUOUS_OR_NONEXISTENT_TIME')
    return possibilities.pop()


def daily_weather(rows, day, timezone_assumption):
    """Temperature at [start,end); accumulations ending in (start,end].

    Full weather calendar, including 23/25 hour days. Missing values or hours
    produce null totals/means, not partial daily estimates or imputed zeros.
    """
    day = date.fromisoformat(day)
    start = conditional_instant(datetime.combine(day, time()), timezone_assumption)
    end = conditional_instant(datetime.combine(day + timedelta(days=1), time()), timezone_assumption)
    require(rows and len({r['snapshot_id'] for r in rows}) == 1, 'WEATHER_SINGLE_SNAPSHOT_REQUIRED')
    lookup = {}
    for row in rows:
        t = datetime.fromisoformat(row['valid_time_utc'])
        require(t.utcoffset() == timedelta(0) and t.minute == t.second == t.microsecond == 0,
                'WEATHER_UTC_HOUR_REQUIRED')
        require(t not in lookup, 'WEATHER_DUPLICATE_JOIN_KEY')
        lookup[t] = row
    n = int((end - start).total_seconds() / 3600)
    require(n in (23, 24, 25), 'WEATHER_DAY_LENGTH')
    metrics = {}
    specs = (('temperature_2m_c', 'temperature_mean_c', 0),
             ('precipitation_preceding_hour_mm', 'precipitation_sum_mm', 1),
             ('snowfall_preceding_hour_cm', 'snowfall_sum_cm', 1))
    for column, result, offset in specs:
        values = [lookup.get(start + timedelta(hours=h + offset), {}).get(column) for h in range(n)]
        complete = all(v is not None for v in values)
        metrics[result] = (math.fsum(values) / n if offset == 0 else math.fsum(values)) if complete else None
        metrics[column + '_present_hours'] = sum(v is not None for v in values)
    return dict(day=day.isoformat(), timezone_assumption=timezone_assumption,
                alignment_status='CONDITIONAL_UNVERIFIED_ACTIVITY_TIMEZONE',
                weather_snapshot_id=rows[0]['snapshot_id'], expected_hours=n,
                window_start_utc=start.isoformat(), window_end_utc=end.isoformat(),
                retrospective_only=True, **metrics)


def join_daily_activity(activity, weather_rows, selected, *, timezone_assumption):
    """One explicitly selected processing scope/day; missing activity stays null.

    Retain only public aggregate counts and processing provenance. Prevent joins
    across duplicate source versions/policies or accidental many-to-many grains.
    """
    selected = tuple(selected)
    require(selected and len({s.processing_key for s in selected}) == len(selected)
            and len({s.source_file_name for s in selected}) == len(selected), 'ACTIVITY_SELECTION_AMBIGUOUS')
    ordered = sorted(selected, key=lambda s: s.source.covered_start)
    require(all(a.source.covered_end_exclusive <= b.source.covered_start for a, b in zip(ordered, ordered[1:])),
            'ACTIVITY_SELECTION_OVERLAP')
    scopes = {s.processing_key: s for s in selected}
    lookup = {}
    columns = ('observation_count', 'plow_active_observations', 'spreader_active_observations')
    for row in activity:
        require(row.get('processing_key') in scopes, 'ACTIVITY_UNSELECTED_SCOPE')
        scope = scopes[row['processing_key']]
        require(all(row.get(k) == v for k, v in scope.dimensions().items()), 'ACTIVITY_LINEAGE_MISMATCH')
        day = row['source_local_naive_day']
        require(scope.source.covered_start <= day < scope.source.covered_end_exclusive,
                'ACTIVITY_DATE_OUTSIDE_SCOPE')
        require(all(type(row.get(k)) is int and row[k] >= 0 for k in columns)
                and max(row[k] for k in columns[1:]) <= row['observation_count'], 'ACTIVITY_COUNT_CONTRACT')
        key = (scope.processing_key, day)
        require(key not in lookup, 'ACTIVITY_DUPLICATE_DAILY_GRAIN')
        lookup[key] = row
    result = []
    for scope in selected:
        day = date.fromisoformat(scope.source.covered_start)
        end = date.fromisoformat(scope.source.covered_end_exclusive)
        while day < end:
            actual = lookup.get((scope.processing_key, day.isoformat()))
            result.append(dict(daily_weather(weather_rows, day.isoformat(), timezone_assumption),
                               processing_key=scope.processing_key, source_version_id=scope.source_version_id,
                               quality_policy_sha256=scope.policy.policy_sha256,
                               activity_present=actual is not None,
                               **{k: actual[k] if actual is not None else None for k in columns}))
            day += timedelta(days=1)
    return result
