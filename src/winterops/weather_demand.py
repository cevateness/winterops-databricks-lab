"""Private Silver -> coarse hourly demand -> returned-grid weather -> matches.

Pure planning/matching except the explicit acquire_demand entrypoint. No native
client, vehicle identifiers, raw-position exports, interpolation or forecasts.
"""
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import math
from pathlib import Path

from winterops.foundation import _timestamp
from winterops.unified_gold import UnifiedGold
from winterops.weather import (WeatherRequest, acquire_snapshot, canonical, digest,
                               finite, load_snapshot, require)
from winterops.weather_analysis import conditional_instant
from winterops.weather_footprint import coarse_footprint, collection_comparison

UTC = timezone.utc
HYPOTHESES = ('America/Toronto', 'UTC')
FIELDS = ('source_dataset', 'source_file_name', 'source_file_sha256', 'source_version_id',
          'pipeline_version', 'quality_policy_sha256', 'source_week_start', 'source_week_end_exclusive')
MEASUREMENTS = ('temperature_2m_c', 'precipitation_preceding_hour_mm', 'snowfall_preceding_hour_cm')


@dataclass(frozen=True)
class ActivityHour:
    processing_key: str
    source_version_id: str
    quality_policy_sha256: str
    spatial_bin: str
    representative_latitude: float
    representative_longitude: float
    source_local_hour: str
    observation_count: int
    boundary_context_observations: int = 0


def aggregate_activity(rows, selected, *, minimum_observations=5, geographic_margin_degrees=0.0):
    """Consume a private typed Silver projection; emit only coarse bin/hour counts.

    Bins are 0.25-degree candidates, NOT assumed ERA5 cells or City boundaries.
    Exclude coordinates outside the selected policy's broad review envelope;
    report exclusions without changing Silver classifications. Suppress sparse
    bin/hours locally. This is data minimization, not an anonymity guarantee.
    """
    selected = tuple(selected)
    UnifiedGold(selected)  # Reuse nonoverlap/version/policy ambiguity guards.
    require(type(minimum_observations) is int and 1 <= minimum_observations <= 100,
            'DEMAND_MINIMUM_OBSERVATIONS')
    require(finite(geographic_margin_degrees) and 0 <= geographic_margin_degrees <= 1.0,
            'DEMAND_GEOGRAPHIC_MARGIN_BOUND')
    scopes = {s.processing_key: s for s in selected}
    dimensions = {key: scope.dimensions() for key, scope in scopes.items()}
    counts, context_counts, seen = Counter(), Counter(), set()
    audit = Counter(input_rows=0, excluded_quality_rows=0, outside_review_rows=0,
                    outside_near_review_rows=0, outside_selected_review_rows=0, included_boundary_context_rows=0,
                    eligible_observations=0, suppressed_observations=0, retained_observations=0)
    for row in rows:
        audit['input_rows'] += 1
        require(audit['input_rows'] <= 500000, 'DEMAND_INPUT_ROW_BOUND')
        scope = scopes.get(row.get('processing_key'))
        require(scope is not None and all(row.get(k) == dimensions[scope.processing_key][k] for k in FIELDS),
                'DEMAND_SELECTED_SILVER_LINEAGE')
        number = row.get('source_record_number')
        require(type(number) is int and 1 <= number <= scope.expected_rows, 'DEMAND_RECORD_ID_REQUIRED')
        key = (scope.processing_key, number)
        require(key not in seen, 'DEMAND_DUPLICATE_SOURCE_OBSERVATION')
        seen.add(key)
        require(row.get('quality_status') in ('VALID', 'INVALID', 'HEADER'), 'DEMAND_QUALITY_CONTRACT')
        if row['quality_status'] != 'VALID':
            audit['excluded_quality_rows'] += 1
            continue
        lat, lon = row.get('latitude'), row.get('longitude')
        stamp = _timestamp(row.get('event_time_unzoned'))
        require(finite(lat) and finite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180,
                'DEMAND_VALID_COORDINATES_REQUIRED')
        require(stamp is not None and scope.source.covered_start <= stamp.date().isoformat()
                < scope.source.covered_end_exclusive, 'DEMAND_VALID_NAIVE_TIME_REQUIRED')
        p = scope.policy
        outside_original = not (p.review_lat_min <= lat <= p.review_lat_max and p.review_lon_min <= lon <= p.review_lon_max)
        if outside_original:
            audit['outside_selected_review_rows'] += 1
            # Diagnostic only: an angular band, not a distance/geofence or a
            # reason to silently enlarge the selected geographic policy.
            if (p.review_lat_min - .01 <= lat <= p.review_lat_max + .01
                    and p.review_lon_min - .01 <= lon <= p.review_lon_max + .01):
                audit['outside_near_review_rows'] += 1
        margin = geographic_margin_degrees
        if not (p.review_lat_min - margin <= lat <= p.review_lat_max + margin
                and p.review_lon_min - margin <= lon <= p.review_lon_max + margin):
            audit['outside_review_rows'] += 1
            continue
        audit['included_boundary_context_rows'] += int(outside_original)
        require(42.1 - margin <= lat <= 42.5 + margin and -83.3 - margin <= lon <= -82.6 + margin,
                'DEMAND_WINDSOR_PROTOTYPE_BOUND')
        # Floor rather than truncation is essential for negative longitudes.
        y, x = math.floor(lat * 4), math.floor(lon * 4)
        hour = stamp.replace(minute=0, second=0, microsecond=0).isoformat(sep=' ')
        counts[(scope.processing_key, y, x, hour)] += 1
        context_counts[(scope.processing_key, y, x, hour)] += int(outside_original)
        audit['eligible_observations'] += 1
    result = []
    for (key, y, x, hour), count in sorted(counts.items()):
        if count < minimum_observations:
            audit['suppressed_observations'] += count
            continue
        s = scopes[key]
        result.append(ActivityHour(key, s.source_version_id, s.policy.policy_sha256,
                                   f'q25:{y}:{x}', (y + .5) / 4, (x + .5) / 4, hour, count,
                                   context_counts[(key, y, x, hour)]))
        audit['retained_observations'] += count
    eligible_bins = {f'q25:{y}:{x}' for _, y, x, _ in counts}
    require(audit['input_rows'] == audit['excluded_quality_rows'] + audit['outside_review_rows']
            + audit['eligible_observations'] and audit['eligible_observations']
            == audit['suppressed_observations'] + audit['retained_observations'], 'DEMAND_OBSERVATION_ACCOUNTING')
    return tuple(result), dict(audit, minimum_observations=minimum_observations,
                               weather_geographic_margin_degrees=geographic_margin_degrees,
                               eligible_coarse_footprint=coarse_footprint(eligible_bins),
                               coverage_accounting=dict(all_input_rows_accounted_for=True,
                                   hull_or_bbox_clipped_rows=0, outside_review_band_degrees=.01,
                                   geographic_status='REVIEW_EXCLUDED_COORDINATES' if audit['outside_review_rows'] else 'NO_GEOGRAPHIC_EXCLUSIONS',
                                   sparse_status='SPARSE_BUCKETS_EXCLUDED' if audit['suppressed_observations'] else 'NO_SPARSE_EXCLUSIONS'),
                               input_completeness='NOT_ASSERTED_BY_THIS_LOCAL_PROJECTION')


def _validate_hours(hours):
    seen = set()
    for a in hours:
        require(isinstance(a, ActivityHour) and type(a.observation_count) is int and a.observation_count > 0,
                'DEMAND_ACTIVITY_HOUR_REQUIRED')
        require(type(a.boundary_context_observations) is int
                and 0 <= a.boundary_context_observations <= a.observation_count, 'DEMAND_BOUNDARY_CONTEXT_COUNT')
        try:
            prefix, y, x = a.spatial_bin.split(':')
            y, x = int(y), int(x)
        except (ValueError, AttributeError):
            require(False, 'DEMAND_SPATIAL_BIN')
        require(prefix == 'q25' and a.spatial_bin == f'q25:{y}:{x}'
                and a.representative_latitude == (y + .5) / 4
                and a.representative_longitude == (x + .5) / 4, 'DEMAND_SPATIAL_REPRESENTATIVE')
        WeatherRequest(latitude=a.representative_latitude, longitude=a.representative_longitude, grid_only=True)
        stamp = _timestamp(a.source_local_hour)
        require(stamp is not None and stamp.minute == stamp.second == stamp.microsecond == 0,
                'DEMAND_SOURCE_HOUR_REQUIRED')
        key = (a.processing_key, a.spatial_bin, a.source_local_hour)
        require(key not in seen, 'DEMAND_DUPLICATE_ACTIVITY_HOUR')
        seen.add(key)


def required_epochs(activity, hypothesis, lookback_hours):
    require(hypothesis in HYPOTHESES, 'DEMAND_TIMEZONE_HYPOTHESIS')
    start = conditional_instant(datetime.fromisoformat(activity.source_local_hour), hypothesis)
    end = conditional_instant(datetime.fromisoformat(activity.source_local_hour) + timedelta(hours=1), hypothesis)
    require(end - start == timedelta(hours=1), 'DEMAND_UNSUPPORTED_CLOCK_HOUR')
    t = int(start.timestamp())
    # Instant at start, current-hour accumulation at end, and antecedent sums
    # ending at start, start-1h, ... (lookback=0 omits antecedent sums).
    return t, t + 3600, tuple(t - h * 3600 for h in range(lookback_hours))


@dataclass(frozen=True)
class DemandPlan:
    activity: tuple[ActivityHour, ...]
    lookback_hours: int = 2

    def __post_init__(self):
        require(type(self.activity) is tuple and len(self.activity) <= 10000, 'DEMAND_ACTIVITY_BOUND')
        require(type(self.lookback_hours) is int and 0 <= self.lookback_hours <= 6, 'DEMAND_LOOKBACK_BOUND')
        _validate_hours(self.activity)
        for activity in self.activity:
            for hypothesis in HYPOTHESES:
                required_epochs(activity, hypothesis, self.lookback_hours)
        require(len(self.requests) <= 24 and sum(len(r.epochs) for r in self.requests) <= 8192,
                'DEMAND_REQUEST_BUDGET')

    @property
    def needed(self):
        result = {}
        for a in self.activity:
            hours = result.setdefault(a.spatial_bin, set())
            for hypothesis in HYPOTHESES:
                start, end, antecedent = required_epochs(a, hypothesis, self.lookback_hours)
                hours.update((start, end, *antecedent))
        return result

    @property
    def requests(self):
        representatives = {a.spatial_bin: (a.representative_latitude, a.representative_longitude) for a in self.activity}
        result = []
        for spatial_bin, epochs in sorted(self.needed.items()):
            days = sorted({datetime.fromtimestamp(t, UTC).date() for t in epochs})
            windows = []
            for day in days:
                if windows and day == windows[-1][-1] + timedelta(days=1) and (day - windows[-1][0]).days < 31:
                    windows[-1].append(day)
                else:
                    windows.append([day])
            lat, lon = representatives[spatial_bin]
            result.extend(WeatherRequest(w[0].isoformat(), w[-1].isoformat(), lat, lon, grid_only=True) for w in windows)
        return tuple(result)

    def public_contract(self):
        """Only coarse representatives and API date windows, never raw positions."""
        requests = self.requests
        footprint = coarse_footprint(self.needed)
        dates = {datetime.fromtimestamp(t, UTC).date().isoformat() for r in requests for t in r.epochs}
        api_hours = sum(len(r.epochs) for r in requests)
        return dict(contract='activity-weather-demand-v1', activity_hours=len(self.activity),
                    spatial_bins=len(self.needed), lookback_hours=self.lookback_hours,
                    hypotheses=list(HYPOTHESES), request_count=len(self.requests),
                    requested_api_hours=api_hours, retained_coarse_footprint=footprint,
                    requested_hourly_location_records=api_hours,
                    requested_measurement_values=api_hours * len(MEASUREMENTS),
                    collection_size_unit='HOURLY_LOCATION_RECORDS_NOT_EXECUTION_HOURS',
                    estimated_runtime_seconds=None,
                    request_budget=24, hourly_location_record_budget=8192,
                    regional_collection_comparison=collection_comparison(footprint, utc_dates=dates,
                                                                          activity_api_hours=api_hours),
                    required_bin_hours=sum(len(v) for v in self.needed.values()),
                    requests=[dict(request_id=r.request_id, parameters=r.parameters) for r in requests])


def acquire_demand(plan, directory, *, acquire=acquire_snapshot):
    """Explicit bounded acquisition; each request is cached/reused by identity.

    No retries. On failure earlier complete bundles remain; no automatic cleanup.
    Only coarse representatives cross the network, never activity rows/counts.
    """
    require(isinstance(plan, DemandPlan), 'DEMAND_PLAN_REQUIRED')
    return tuple(acquire(Path(directory) / r.request_id, r) for r in plan.requests)


def load_demand(plan, directory):
    return tuple(load_snapshot(Path(directory) / r.request_id) for r in plan.requests)


def weather_catalog(plan, snapshots):
    """Bind single-point response identity to returned grids; deduplicate facts.

    Exact overlapping grid/hour values must agree, including nulls. Conflicting
    revisions or grid assignments block instead of choosing a response silently.
    """
    snapshots = tuple(snapshots)
    requests = {r.request_id: r for r in plan.requests}
    needed = plan.needed
    bin_by_point = {(a.representative_latitude, a.representative_longitude): a.spatial_bin for a in plan.activity}
    grids, bindings, facts, received = {}, {}, {}, set()
    source_ids = sorted(m['snapshot_id'] for m, _ in snapshots)
    snapshot_id = digest(canonical(dict(contract='activity-weather-facts-v1', raw_snapshots=source_ids)))
    for metadata, rows in snapshots:
        request_id = metadata['request_id']
        r = requests.get(request_id)
        require(r is not None and request_id not in received, 'DEMAND_UNEXPECTED_OR_DUPLICATE_RESPONSE')
        received.add(request_id)
        require(metadata.get('request_url') == r.url and metadata.get('weather_kind') == 'historical_reanalysis'
                and metadata.get('model_attestation') == 'REQUEST_PARAMETER_ONLY', 'DEMAND_RESPONSE_CONTRACT')
        grid = {k: metadata['grid'][k] for k in ('latitude', 'longitude', 'elevation')}
        require(all(finite(v) for v in grid.values()), 'DEMAND_RETURNED_GRID_METADATA')
        require(abs(grid['latitude'] - r.latitude) <= 1 and abs(grid['longitude'] - r.longitude) <= 1,
                'DEMAND_RETURNED_GRID_OUTSIDE_REQUEST_BOUND')
        grid = {k: float(v) for k, v in grid.items()}
        grid_id = digest(canonical(dict(provider='open-meteo', requested_model='era5', grid_only=True, **grid)))
        grids[grid_id] = grid
        spatial_bin = bin_by_point[(r.latitude, r.longitude)]
        require(spatial_bin not in bindings or bindings[spatial_bin] == grid_id, 'DEMAND_GRID_ASSIGNMENT_CHANGED')
        bindings[spatial_bin] = grid_id
        require(len(rows) == len(r.epochs)
                and tuple(int(datetime.fromisoformat(row['valid_time_utc']).timestamp()) for row in rows) == r.epochs,
                'DEMAND_RESPONSE_HOUR_GRID')
        for row in rows:
            require(row['snapshot_id'] == metadata['snapshot_id'], 'DEMAND_RAW_SNAPSHOT_MISMATCH')
            stamp = datetime.fromisoformat(row['valid_time_utc'])
            require(stamp.utcoffset() == timedelta(0)
                    and datetime.fromisoformat(row['accumulation_start_utc']) == stamp - timedelta(hours=1),
                    'DEMAND_RESPONSE_INTERVAL')
            epoch = int(stamp.timestamp())
            if epoch not in needed[spatial_bin]:
                continue
            key = (grid_id, row['valid_time_utc'])
            values = {k: row[k] for k in MEASUREMENTS}
            require(all(v is None or finite(v) for v in values.values()), 'DEMAND_WEATHER_NUMERIC_CONTRACT')
            require(all(values[k] is None or values[k] >= 0 for k in MEASUREMENTS[1:]),
                    'DEMAND_NEGATIVE_ACCUMULATION')
            require(key not in facts or all(facts[key][k] == v for k, v in values.items()), 'DEMAND_GRID_HOUR_CONFLICT')
            source = dict(raw_snapshot_id=metadata['snapshot_id'], request_id=request_id, response_location_index=0)
            if key in facts:
                facts[key]['sources'].append(source)
            else:
                facts[key] = dict(weather_snapshot_id=snapshot_id, grid_id=grid_id,
                                  valid_time_utc=row['valid_time_utc'], accumulation_start_utc=row['accumulation_start_utc'],
                                  **values, sources=[source])
    return dict(weather_snapshot_id=snapshot_id, weather_kind='historical_reanalysis',
                requested_model='era5', model_attestation='REQUEST_PARAMETER_ONLY',
                grids=grids, bin_to_grid=bindings,
                received_requests=len(received), planned_requests=len(requests),
                facts=[facts[k] for k in sorted(facts)])


def matched_projection(plan, catalog):
    """One row per activity processing/bin/local-hour/hypothesis, not a calendar."""
    facts = {(r['grid_id'], r['valid_time_utc']): r for r in catalog['facts']}
    require(len(facts) == len(catalog['facts']), 'DEMAND_DUPLICATE_WEATHER_FACT')
    require(all(r['weather_snapshot_id'] == catalog['weather_snapshot_id'] for r in facts.values()),
            'DEMAND_MIXED_WEATHER_SNAPSHOTS')
    result, used = [], set()
    for a in plan.activity:
        grid_id = catalog['bin_to_grid'].get(a.spatial_bin)
        for hypothesis in HYPOTHESES:
            start, end, antecedent = required_epochs(a, hypothesis, plan.lookback_hours)
            def weather(epoch):
                instant = datetime.fromtimestamp(epoch, UTC).isoformat()
                row = facts.get((grid_id, instant))
                if row is not None:
                    used.add((catalog['weather_snapshot_id'], grid_id, instant))
                return row or {}
            instant, interval = weather(start), weather(end)
            previous = [weather(t) for t in antecedent]
            temp = instant.get('temperature_2m_c')
            rain = interval.get('precipitation_preceding_hour_mm')
            snow = interval.get('snowfall_preceding_hour_cm')
            rain_lag = [v.get('precipitation_preceding_hour_mm') for v in previous]
            snow_lag = [v.get('snowfall_preceding_hour_cm') for v in previous]
            complete = temp is not None and rain is not None and snow is not None
            result.append(dict(processing_key=a.processing_key, source_version_id=a.source_version_id,
                               quality_policy_sha256=a.quality_policy_sha256, spatial_bin=a.spatial_bin,
                               source_local_hour=a.source_local_hour, observation_count=a.observation_count,
                               outside_source_review_observations=a.boundary_context_observations,
                               timezone_hypothesis=hypothesis, grid_id=grid_id,
                               weather_snapshot_id=catalog['weather_snapshot_id'],
                               temperature_valid_time_utc=datetime.fromtimestamp(start, UTC).isoformat(),
                               accumulation_valid_time_utc=datetime.fromtimestamp(end, UTC).isoformat(),
                               temperature_2m_c=temp, precipitation_activity_hour_mm=rain, snowfall_activity_hour_cm=snow,
                               lookback_hours=plan.lookback_hours,
                               precipitation_antecedent_mm=math.fsum(rain_lag) if rain_lag and all(v is not None for v in rain_lag) else None,
                               snowfall_antecedent_cm=math.fsum(snow_lag) if snow_lag and all(v is not None for v in snow_lag) else None,
                               antecedent_present_hours=sum(v is not None and w is not None for v, w in zip(rain_lag, snow_lag)),
                               antecedent_coverage='NOT_REQUESTED' if not previous else 'COMPLETE' if all(v is not None for v in rain_lag + snow_lag) else 'MISSING_OR_NULL',
                               current_variables_present=sum(v is not None for v in (temp, rain, snow)),
                               weather_coverage='COMPLETE' if complete else 'MISSING_GRID_OR_HOUR' if not instant or not interval else 'NULL_MEASUREMENT',
                               alignment_status='CONDITIONAL_UNVERIFIED_ACTIVITY_TIMEZONE', retrospective_only=True))
    return dict(matches=result, matched_weather_keys=[list(k) for k in sorted(used)],
                evidence_status='MATCHED_SUPPLIED_INPUTS_NOT_NATIVE_VERIFIED')
