"""Operational Analytics V1: explicit grains, additive counts, sampled weather.

Public outputs contain city/hour and coarse cell/week aggregates. Cell/hour and
matched-grid detail stay in an optional private artifact outside Git.
"""
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import datetime, timedelta
import math

from winterops.temporal_review import review_clock, summarize_matches
from winterops.unified_gold import ADDITIVE, DIMENSIONS
from winterops.weather import ATTRIBUTION, canonical, digest, require
from winterops.weather_demand import ActivityHour, DemandPlan, matched_projection

SCHEMA = 'winterops-operational-analytics-v1'
METRICS = {
    'observation_count': 'Number of VALID source observations, including repeated payloads.',
    'observed_identifier_count': 'Distinct identifiers recomputed within this grain; never additive or fleet capacity.',
    'hours_containing_telemetry': 'Distinct occupied source-local hour buckets; not service hours.',
    'missing_telemetry': 'No recorded VALID observation in that source-local bucket; activity unknown.',
    'equipment_composition': 'Mutually exclusive plow-only, spreader-only, both-active, neither-active flags.',
    'weather': 'Unweighted distinct returned-grid/time samples during recorded activity; retrospective ERA5-requested reanalysis.',
}
GRAINS = {
    'weekly': ['processing_key'], 'daily': ['processing_key', 'source_local_naive_day'],
    'hourly': ['processing_key', 'source_local_naive_hour'],
    'cell_hour': ['processing_key', 'spatial_bin', 'source_local_naive_hour'],
    'cell_weather': ['processing_key', 'spatial_bin', 'source_local_hour', 'timezone_hypothesis'],
    'weather_facts': ['weather_snapshot_id', 'grid_id', 'valid_time_utc'],
    'public_cells': ['processing_key', 'spatial_bin'],
    'public_weather_hourly': ['processing_key', 'source_local_hour', 'timezone_hypothesis'],
}


def validate_products(products, plan):
    scopes = {s.processing_key: s for s in plan.selected}
    for product in ('weekly', 'daily', 'hourly', 'cell_hour'):
        keys = set()
        for row in products[product]:
            scope = scopes.get(row['processing_key'])
            require(scope is not None and all(row.get(k) == v for k, v in scope.dimensions().items()),
                    'ANALYTICS_PRODUCT_LINEAGE')
            key = tuple(row[k] for k in GRAINS[product])
            require(key not in keys, 'ANALYTICS_DUPLICATE_PRODUCT_KEY')
            keys.add(key)
            for metric in ADDITIVE:
                require(type(row[metric]) is int and 0 <= row[metric] <= row['observation_count'],
                        'ANALYTICS_ADDITIVE_DOMAIN')
            require(row['observation_count'] == sum(row[k] for k in
                    ('plow_only_observations', 'spreader_only_observations', 'both_active_observations', 'neither_active_observations'))
                    and row['plow_active_observations'] == row['plow_only_observations'] + row['both_active_observations']
                    and row['spreader_active_observations'] == row['spreader_only_observations'] + row['both_active_observations'],
                    'ANALYTICS_EQUIPMENT_COMPOSITION')
            require(0 < row['observed_identifier_count'] <= row['observation_count'], 'ANALYTICS_IDENTIFIER_DOMAIN')
            stamp = row.get('source_local_naive_hour', row.get('source_local_naive_day'))
            if stamp:
                t = datetime.fromisoformat(stamp)
                require(t.tzinfo is None and scope.source.covered_start <= stamp[:10] < scope.source.covered_end_exclusive,
                        'ANALYTICS_SOURCE_TIME_SCOPE')
    require({r['processing_key'] for r in products['weekly']} == set(scopes), 'ANALYTICS_WEEK_SCOPE')
    def sums(rows, key):
        result = defaultdict(Counter)
        for r in rows:
            result[key(r)].update({m: r[m] for m in ADDITIVE})
        return dict(result)
    # Same grand total cannot conceal a shifted hour, day or equipment state.
    require(sums(products['cell_hour'], lambda r: (r['processing_key'], r['source_local_naive_hour'])) ==
            sums(products['hourly'], lambda r: (r['processing_key'], r['source_local_naive_hour'])), 'ANALYTICS_CELL_HOUR_RECONCILIATION')
    require(sums(products['hourly'], lambda r: (r['processing_key'], r['source_local_naive_hour'][:10])) ==
            sums(products['daily'], lambda r: (r['processing_key'], r['source_local_naive_day'])), 'ANALYTICS_DAY_RECONCILIATION')
    require(sums(products['daily'], lambda r: r['processing_key']) == sums(products['weekly'], lambda r: r['processing_key']),
            'ANALYTICS_WEEK_RECONCILIATION')
    for row in products['weekly']:
        key = row['processing_key']
        require(row['silver_rows'] == row['bronze_rows'] == scopes[key].expected_rows and
                row['silver_rows'] == row['valid_rows'] + row['header_rows'] + row['invalid_rows'] and
                row['valid_rows'] == row['observation_count'], 'ANALYTICS_QUALITY_ACCOUNTING')
        require(row['hours_containing_telemetry'] == sum(r['processing_key'] == key for r in products['hourly']) and
                row['days_containing_telemetry'] == sum(r['processing_key'] == key for r in products['daily']),
                'ANALYTICS_OBSERVED_PERIOD_COUNT')
    return dict(status='PASS_LOCAL_ANALYTICAL_RECONCILIATION',
                rows={p: len(products[p]) for p in ('weekly', 'daily', 'hourly', 'cell_hour')},
                totals={m: sum(r[m] for r in products['weekly']) for m in ADDITIVE})


def match_cached_weather(products, catalog, archived_matches):
    """Rebuild existing matches using the existing demand/matching implementation."""
    hours = []
    for row in products['cell_hour']:
        _, y, x = row['spatial_bin'].split(':')
        hours.append(ActivityHour(row['processing_key'], row['source_version_id'], row['quality_policy_sha256'],
                                  row['spatial_bin'], (int(y) + .5) / 4, (int(x) + .5) / 4,
                                  row['source_local_naive_hour'], row['observation_count'],
                                  row['outside_source_review_observations']))
    rebuilt = matched_projection(DemandPlan(tuple(hours), 2), catalog)['matches']
    require(Counter(canonical(r) for r in rebuilt) == Counter(canonical(r) for r in archived_matches),
            'ANALYTICS_SAVED_MATCH_RECONCILIATION')
    summarize_matches(rebuilt)  # Existing paired-grain, count and weather-fact checks.
    cells = {(r['processing_key'], r['spatial_bin'], r['source_local_naive_hour']): r for r in products['cell_hour']}
    return [{**cells[(r['processing_key'], r['spatial_bin'], r['source_local_hour'])], **r} for r in rebuilt]


def weather_summary(matches):
    """One row per processing/source-hour/hypothesis; no accumulation spatial sums."""
    require(matches and len({r['weather_snapshot_id'] for r in matches}) == 1,
            'ANALYTICS_SINGLE_WEATHER_SNAPSHOT')
    groups = defaultdict(list)
    for row in matches:
        groups[(row['processing_key'], row['source_local_hour'], row['timezone_hypothesis'])].append(row)
    result = []
    variables = ('temperature_2m_c', 'precipitation_activity_hour_mm', 'snowfall_activity_hour_cm',
                 'precipitation_antecedent_mm', 'snowfall_antecedent_cm')
    for (key, hour, zone), rows in sorted(groups.items()):
        facts = {}
        for row in rows:
            fact_key = (row['weather_snapshot_id'], row['grid_id'], row['temperature_valid_time_utc'], row['accumulation_valid_time_utc'])
            values = tuple(row[v] for v in variables)
            require(all(v is None or type(v) in (float, int) and math.isfinite(v) for v in values), 'ANALYTICS_WEATHER_VALUE')
            require(all(v is None or v >= 0 for v in values[1:]), 'ANALYTICS_NEGATIVE_ACCUMULATION')
            require(fact_key not in facts or facts[fact_key] == values, 'ANALYTICS_WEATHER_FACT_CONFLICT')
            facts[fact_key] = values
        record = dict(processing_key=key, source_local_hour=hour, timezone_hypothesis=zone,
                      weather_snapshot_id=rows[0]['weather_snapshot_id'], sampled_grid_hours=len(facts),
                      observation_count=sum(r['observation_count'] for r in rows))
        for i, name in enumerate(variables):
            values = [v[i] for v in facts.values() if v[i] is not None]
            record.update({name + '_mean': math.fsum(values) / len(values) if values else None,
                           name + '_min': min(values) if values else None,
                           name + '_max': max(values) if values else None,
                           name + '_present_samples': len(values)})
        result.append(record)
    return result


def validate_weather_join(products, matches, plan, snapshot_id):
    cells = {(r['processing_key'], r['spatial_bin'], r['source_local_naive_hour']): r for r in products['cell_hour']}
    scopes = {s.processing_key: s for s in plan.selected}
    seen = set()
    for row in matches:
        key = (row['processing_key'], row['spatial_bin'], row['source_local_hour'])
        zone = row['timezone_hypothesis']
        require(key in cells and zone in ('America/Toronto', 'UTC') and (key, zone) not in seen,
                'ANALYTICS_WEATHER_JOIN_CARDINALITY')
        seen.add((key, zone))
        require(row['observation_count'] == cells[key]['observation_count'] and
                row['weather_snapshot_id'] == snapshot_id and row['retrospective_only'] is True and
                all(row.get(k) == v for k, v in scopes[key[0]].dimensions().items()
                    if k in ('source_version_id', 'quality_policy_sha256')),
                'ANALYTICS_WEATHER_JOIN_LINEAGE_OR_COUNT')
    require(len(seen) == len(cells) * 2, 'ANALYTICS_WEATHER_JOIN_INCOMPLETE')


def calendar_hours(products, plan):
    lookup = {(r['processing_key'], r['source_local_naive_hour']): r for r in products['hourly']}
    result = []
    for scope in plan.selected:
        stamp = datetime.fromisoformat(scope.source.covered_start)
        end = datetime.fromisoformat(scope.source.covered_end_exclusive)
        while stamp < end:
            hour = stamp.isoformat(' ')
            actual = lookup.get((scope.processing_key, hour))
            result.append(dict(processing_key=scope.processing_key, source_local_naive_hour=hour,
                               telemetry_status='RECORDED' if actual else 'MISSING_TELEMETRY_ACTIVITY_UNKNOWN',
                               observation_count=actual['observation_count'] if actual else None))
            stamp += timedelta(hours=1)
    return result


def public_bundle(products, plan, matches, *, evidence, clock_evidence, weather_provenance):
    validation = validate_products(products, plan)
    validate_weather_join(products, matches, plan, weather_provenance['weather_snapshot_id'])
    weeks = {s.processing_key: s for s in plan.selected}
    # Public cell/week totals contain no time-of-day detail or identifier counts.
    grouped = defaultdict(Counter)
    for row in products['cell_hour']:
        c = grouped[(row['processing_key'], row['spatial_bin'])]
        c.update({k: row[k] for k in (*ADDITIVE, 'outside_source_review_observations')})
        c['observed_cell_hours'] += 1
    public_cells = []
    suppressed = Counter()
    for (key, cell), counts in sorted(grouped.items()):
        # Presentation-only suppression; complete private products remain intact.
        if counts['observation_count'] < 20:
            suppressed[key] += counts['observation_count']
            continue
        _, y, x = cell.split(':')
        public_cells.append(dict(processing_key=key, spatial_bin=cell, **counts,
                                 cell_south=int(y)/4, cell_west=int(x)/4, cell_size_degrees=.25))
    # An allowlist, not a blacklist: future detailed columns cannot leak into HTML.
    def project(rows, fields):
        return [{k: row[k] for k in fields} for row in rows]
    base = ['processing_key', *ADDITIVE]
    weekly_fields = base + ['observed_identifier_count', 'hours_containing_telemetry', 'days_containing_telemetry',
                            'bronze_rows', 'silver_rows', 'valid_rows', 'header_rows', 'invalid_rows',
                            'outside_review_envelope_rows', 'long_gap_pairs', 'repeated_valid_payload_groups',
                            'excess_valid_payload_observations']
    output = dict(schema=SCHEMA, evidence=evidence, native_execution=False, validation=validation,
                  contracts=dict(grains=GRAINS, metrics=METRICS, timezone='SOURCE_LOCAL_NAIVE_TIMESTAMP_NTZ',
                                 weather_alignment='CONDITIONAL_UNVERIFIED_ACTIVITY_TIMEZONE',
                                 working_hypothesis='America/Toronto', sensitivity_hypothesis='UTC',
                                 retrospective_only=True, predictive_features_allowed=False,
                                 weather_antecedent_hours=2, public_cell_minimum_observations=20),
                  clock=review_clock(clock_evidence), weather_provenance=weather_provenance,
                  scopes=[s.dimensions() for s in weeks.values()],
                  attribution=dict(municipal='Contains information licensed under the Open Government Licence — The Corporation of the City of Windsor.',
                                   weather=ATTRIBUTION),
                  weekly=project(products['weekly'], weekly_fields),
                  daily=project(products['daily'], base + ['source_local_naive_day', 'hours_containing_telemetry', 'observed_identifier_count']),
                  hourly=project(products['hourly'], base + ['source_local_naive_hour', 'observed_identifier_count']),
                  calendar=calendar_hours(products, plan), cells=public_cells,
                  suppressed_map_observations=dict(suppressed), weather_hourly=weather_summary(matches))
    output['content_sha256'] = digest(canonical(output))
    return output
