"""Descriptive reporting windows and heuristic observed episodes; never work time.

Identifiers and episode timelines are private inputs/outputs. Public summaries are
explicit allowlists of city-level distributions and pooled relationship tables.
"""
from collections import Counter, defaultdict
from datetime import datetime, timedelta
import math
from statistics import mean

from winterops.weather import require
from winterops.weather_analysis import conditional_instant

STATES = ('neither', 'plow_only', 'spreader_only', 'both')


def state(row):
    require(type(row['plow_active']) is bool and type(row['spreader_active']) is bool, 'DIAG_BOOLEAN_STATE')
    return STATES[int(row['plow_active']) + 2 * int(row['spreader_active'])]


def cell(row):
    return f"q25:{math.floor(row['latitude']*4)}:{math.floor(row['longitude']*4)}"


def percentile(values, p):
    """Linear interpolation on occupied reporting windows/observed episodes only."""
    if not values:
        return None
    values = sorted(values)
    pos = (len(values)-1)*p
    lo = math.floor(pos)
    return values[lo] + (values[math.ceil(pos)]-values[lo])*(pos-lo)


def distribution(values):
    return dict(n=len(values), mean=mean(values) if values else None, p50=percentile(values,.5),
                p95=percentile(values,.95), maximum=max(values) if values else None)


def validated_rows(rows, scope):
    """No reclassification or deduplication; consume established typed Silver."""
    result = []
    seen = set()
    for row in rows:
        require(row['processing_key'] == scope.processing_key and row['source_version_id'] == scope.source_version_id
                and row['quality_policy_sha256'] == scope.policy.policy_sha256, 'DIAG_SOURCE_SCOPE')
        require(row['source_record_number'] not in seen, 'DIAG_RECORD_ORDINAL')
        seen.add(row['source_record_number'])
        if row['quality_status'] != 'VALID':
            continue
        t = datetime.fromisoformat(row['event_time_unzoned'])
        require(t.tzinfo is None and scope.source.covered_start <= t.date().isoformat() < scope.source.covered_end_exclusive,
                'DIAG_SOURCE_NTZ_SCOPE')
        state(row)
        result.append(row)
    return result


def reporting_buckets(rows, minutes):
    require(type(minutes) is int and 1 <= minutes <= 60 and 60 % minutes == 0, 'DIAG_BUCKET_WIDTH')
    groups = defaultdict(list)
    for row in rows:
        t = datetime.fromisoformat(row['event_time_unzoned'])
        t = t.replace(minute=t.minute//minutes*minutes,second=0,microsecond=0)
        groups[(row['processing_key'],t.isoformat(' '))].append(row)
    result = []
    for (key, time), group in sorted(groups.items()):
        ids = {r['truck_id'] for r in group}
        plow = {r['truck_id'] for r in group if r['plow_active']}
        spread = {r['truck_id'] for r in group if r['spreader_active']}
        both_ping = {r['truck_id'] for r in group if r['plow_active'] and r['spreader_active']}
        result.append(dict(processing_key=key,source_local_bucket=time,bucket_minutes=minutes,
                           observation_count=len(group),reporting_ids=len(ids),plow_reporting_ids=len(plow),
                           spreader_reporting_ids=len(spread),both_same_observation_ids=len(both_ping),
                           both_any_observations_ids=len(plow & spread),
                           plow_exclusive_ids=len(plow-spread),spreader_exclusive_ids=len(spread-plow),
                           neither_flag_ids=len(ids-(plow|spread))))
    return result


def timestamp_events(rows):
    by_id = defaultdict(list)
    for row in rows:
        by_id[(row['processing_key'],row['truck_id'])].append(row)
    result = {}
    for key, group in sorted(by_id.items()):
        times = defaultdict(list)
        for row in sorted(group,key=lambda r:(datetime.fromisoformat(r['event_time_unzoned']),r['source_record_number'])):
            times[row['event_time_unzoned']].append(row)
        # Normalize textual fractional-second variants into actual naive datetime keys.
        normalized = defaultdict(list)
        for time, values in times.items():normalized[datetime.fromisoformat(time)].extend(values)
        result[key] = []
        for t, values in sorted(normalized.items()):
            values.sort(key=lambda r:r['source_record_number'])
            states = {state(r) for r in values}
            cells = {cell(r) for r in values}
            result[key].append(dict(time=t,rows=values,state=next(iter(states)) if len(states)==1 else 'unknown_conflicting_tie',
                                    first_cell=next(iter(cells)) if len(cells)==1 else None))
    return result


def episodes(events, gap_minutes, scope):
    require(type(gap_minutes) is int and 1 <= gap_minutes <= 1440, 'DIAG_EPISODE_GAP')
    result = []
    for (key, truck), sequence in events.items():
        require(key == scope.processing_key, 'DIAG_EPISODE_SCOPE')
        groups = []
        for event in sequence:
            if not groups or (event['time']-groups[-1][-1]['time']).total_seconds() > gap_minutes*60:
                groups.append([])
            groups[-1].append(event)
        for index, group in enumerate(groups):
            rows = [r for e in group for r in e['rows']]
            gaps = [(b['time']-a['time']).total_seconds() for a,b in zip(group,group[1:])]
            first,last = group[0]['time'],group[-1]['time']
            known=[(a['state'],b['state']) for a,b in zip(group,group[1:]) if (b['time']-a['time']).total_seconds()<=60 and 'unknown' not in a['state']+b['state']]
            result.append(dict(known_state_changes_60s=sum(a!=b for a,b in known),known_intervals_60s=len(known),processing_key=key,source_version_id=scope.source_version_id,
                               quality_policy_sha256=scope.policy.policy_sha256,truck_id=truck,gap_minutes=gap_minutes,
                               first_observed=first.isoformat(' '),last_observed=last.isoformat(' '),
                               source_record_ordinals=[r['source_record_number'] for r in rows],
                               observation_count=len(rows),apparent_span_seconds=(last-first).total_seconds(),
                               state_counts=dict(Counter(state(r) for r in rows)),first_observed_cell=group[0]['first_cell'],
                               first_state=group[0]['state'],conflicting_timestamp_groups=sum(e['state'].startswith('unknown') for e in group),
                               recording_intervals=len(gaps),maximum_recording_gap_seconds=max(gaps,default=None),
                               intervals_above_nominal=sum(g>scope.policy.nominal_interval_seconds for g in gaps),
                               left_censored=True,right_censored=True,
                               entry_reason='NO_PRIOR_OBSERVATION_IN_SOURCE_SCOPE' if index==0 else 'AFTER_RECORDING_GAP',
                               near_source_left_edge=(first-datetime.fromisoformat(scope.source.covered_start)).total_seconds()<=gap_minutes*60,
                               near_source_right_edge=(datetime.fromisoformat(scope.source.covered_end_exclusive)-last).total_seconds()<=gap_minutes*60))
    return result


def transitions(events, maximum_gap_seconds=60):
    require(type(maximum_gap_seconds) is int and maximum_gap_seconds > 0, 'DIAG_TRANSITION_GAP')
    counts = Counter()
    for (key,_), sequence in events.items():
        for index,current in enumerate(sequence):
            previous = sequence[index-1] if index else None
            dt = (current['time']-previous['time']).total_seconds() if previous else None
            reason = ('source_boundary_unknown' if previous is None else 'gap_unknown' if dt>maximum_gap_seconds else
                      'conflicting_tie_unknown' if 'unknown' in current['state'] or 'unknown' in previous['state'] else 'known')
            before = previous['state'] if reason=='known' else 'unknown'
            after = current['state'] if reason=='known' else 'unknown'
            counts[(key,current['time'].hour,reason,before,after)] += 1
    return [dict(processing_key=k,source_local_hour_of_day=h,maximum_gap_seconds=maximum_gap_seconds,
                 status=reason,previous_state=a,current_state=b,intervals=n,
                 plow_activation_intervals=n if reason=='known' and a in ('neither','spreader_only') and b in ('plow_only','both') else 0,
                 spreader_activation_intervals=n if reason=='known' and a in ('neither','plow_only') and b in ('spreader_only','both') else 0)
            for (k,h,reason,a,b),n in sorted(counts.items())]


def bucket_summaries(buckets):
    groups = defaultdict(list)
    for row in buckets:
        for grain,value in [('week','all'),('day',row['source_local_bucket'][:10]),('hour_of_day',row['source_local_bucket'][11:13]),('weekday',str(datetime.fromisoformat(row['source_local_bucket']).weekday()))]:
            groups[(row['processing_key'],row['bucket_minutes'],grain,value)].append(row)
    output = []
    for (key,width,grain,value), rows in sorted(groups.items()):
        stats = distribution([r['reporting_ids'] for r in rows])
        output.append(dict(processing_key=key,bucket_minutes=width,grain=grain,period=value,
                           occupied_windows=len(rows),observations=sum(r['observation_count'] for r in rows),
                           reporting_ids=stats,
                           composition_mean={v:mean(r[v] for r in rows) for v in
                                             ('plow_exclusive_ids','spreader_exclusive_ids','both_any_observations_ids','neither_flag_ids','both_same_observation_ids')},
                           equipment_distributions={v:distribution([r[v] for r in rows]) for v in ('plow_reporting_ids','spreader_reporting_ids','both_same_observation_ids')} if grain=='week' else {},
                           histogram=[dict(reporting_ids=k,windows=n) for k,n in sorted(Counter(r['reporting_ids'] for r in rows).items())] if grain=='week' else [],
                           peaks=[{k:r[k] for k in ('source_local_bucket','reporting_ids','observation_count')} for r in
                                  sorted(rows,key=lambda r:(-r['reporting_ids'],r['source_local_bucket']))[:3]] if grain=='week' else []))
    return output


def episode_summaries(episodes):
    groups = defaultdict(list)
    for r in episodes:groups[(r['processing_key'],r['gap_minutes'])].append(r)
    return [dict(processing_key=k,gap_minutes=gap,observed_episodes=len(rows),observations=sum(r['observation_count'] for r in rows),
                 apparent_span_seconds=distribution([r['apparent_span_seconds'] for r in rows]),
                 one_timestamp_episodes=sum(r['apparent_span_seconds']==0 for r in rows),
                 after_gap=sum(r['entry_reason']=='AFTER_RECORDING_GAP' for r in rows),
                 source_first=sum(r['entry_reason']=='NO_PRIOR_OBSERVATION_IN_SOURCE_SCOPE' for r in rows),
                 ambiguous_first_cell=sum(r['first_observed_cell'] is None for r in rows),
                 known_state_changes_60s=sum(r['known_state_changes_60s'] for r in rows),
                 conflicting_timestamp_groups=sum(r['conflicting_timestamp_groups'] for r in rows))
            for (k,gap),rows in sorted(groups.items())]


def weather_category(value, kind):
    if value is None:return 'missing'
    require(type(value) in (int,float) and math.isfinite(value),'DIAG_WEATHER_VALUE')
    if kind=='temperature':return 'below_-10C' if value < -10 else '-10_to_below_0C' if value < 0 else '0C_or_warmer'
    require(value>=0,'DIAG_NEGATIVE_WEATHER')
    return 'zero' if value==0 else 'positive'


def weather_fact_keys(row, variable):
    if row is None or row[variable] is None:return set()
    start=datetime.fromisoformat(row['temperature_valid_time_utc'])
    if 'antecedent' in variable:times=[start,start-timedelta(hours=1)]
    elif variable=='temperature_2m_c':times=[start]
    else:times=[datetime.fromisoformat(row['accumulation_valid_time_utc'])]
    return {(row['weather_snapshot_id'],row['grid_id'],t.isoformat()) for t in times}


def weather_relationships(matches, all_episodes, buckets):
    require(len({r['weather_snapshot_id'] for r in matches})==1,'DIAG_SINGLE_WEATHER_SNAPSHOT')
    lookup = {}
    for r in matches:
        k=(r['processing_key'],r['spatial_bin'],r['source_local_hour'],r['timezone_hypothesis'])
        require(k not in lookup,'DIAG_DUPLICATE_WEATHER_MATCH')
        lookup[k]=r
    specs = [('temperature_2m_c','temperature'),('precipitation_activity_hour_mm','wet'),
             ('snowfall_activity_hour_cm','snow'),('precipitation_antecedent_mm','wet'),('snowfall_antecedent_cm','snow')]
    grouped = defaultdict(list)
    for row in matches:
        for variable,kind in specs:
            grouped[(row['processing_key'],row['timezone_hypothesis'],variable,weather_category(row[variable],kind))].append(row)
    cell_tables = []
    for (key,zone,var,category),rows in sorted(grouped.items()):
        facts = {(r['grid_id'],r['temperature_valid_time_utc']) for r in rows}
        obs=sum(r['observation_count'] for r in rows)
        cell_tables.append(dict(processing_key=key,timezone_hypothesis=zone,variable=var,category=category,
                                cell_hours=len(rows),recorded_source_hours=len({r['source_local_hour'] for r in rows}),
                                distinct_grid_windows=len(facts),distinct_weather_facts=len(set().union(*(weather_fact_keys(r,var) for r in rows))),observations=obs,
                                plow_observations=sum(r['plow_active_observations'] for r in rows),
                                spreader_observations=sum(r['spreader_active_observations'] for r in rows),
                                both_observations=sum(r['both_active_observations'] for r in rows),
                                mean_cell_hour_observations=mean(r['observation_count'] for r in rows),
                                mean_cell_hour_spreader_fraction=mean(r['spreader_active_observations']/r['observation_count'] for r in rows)))
    onset_groups = defaultdict(list)
    for ep in all_episodes:
        hour=datetime.fromisoformat(ep['first_observed']).replace(minute=0,second=0,microsecond=0).isoformat(' ')
        for zone in ('America/Toronto','UTC'):
            r=lookup.get((ep['processing_key'],ep['first_observed_cell'],hour,zone))
            ep.setdefault('weather_at_containing_hour_start',{})[zone]=None if r is None else {
                k:r[k] for k in ('grid_id','weather_snapshot_id','temperature_valid_time_utc','temperature_2m_c',
                                'precipitation_antecedent_mm','snowfall_antecedent_cm')}
            for var,kind in (('precipitation_antecedent_mm','wet'),('snowfall_antecedent_cm','snow')):
                value=r[var] if r else None
                onset_groups[(ep['processing_key'],ep['gap_minutes'],zone,var,weather_category(value,kind))].append((ep,r))
    onset_tables=[]
    for (key,gap,zone,var,category),rows in sorted(onset_groups.items()):
        onset_tables.append(dict(processing_key=key,gap_minutes=gap,timezone_hypothesis=zone,variable=var,category=category,
                                 first_observed_episodes=len(rows),episodes_with_weather=sum(r is not None and r[var] is not None for _,r in rows),
                                 distinct_weather_facts=len(set().union(*(weather_fact_keys(r,var) for _,r in rows))),
                                 distinct_grid_windows=len({(r['grid_id'],r['temperature_valid_time_utc']) for _,r in rows if r}),
                                 recorded_source_hours=len({ep['first_observed'][:13] for ep,_ in rows})))
    # Reporting/weather associations use one mean reporting-window count per source
    # hour, never multiply a city count by each cell or individual weather ping.
    from winterops.operational_analytics import weather_summary
    hourly=weather_summary(matches)
    windows=defaultdict(list)
    for r in buckets:windows[(r['processing_key'],r['bucket_minutes'],r['source_local_bucket'][:13])].append(r['reporting_ids'])
    report_groups=defaultdict(list)
    for r in hourly:
        for width in (1,5,15):
            values=windows.get((r['processing_key'],width,r['source_local_hour'][:13]),[])
            for var,kind in specs[:3]:
                category=weather_category(r[var+'_mean'],kind)
                report_groups[(r['processing_key'],width,r['timezone_hypothesis'],var,category)].append((r,values))
    reporting_tables=[]
    for (key,width,zone,var,category),rows in sorted(report_groups.items()):
        reporting_tables.append(dict(processing_key=key,bucket_minutes=width,timezone_hypothesis=zone,variable=var,category=category,
                                     source_hours=len(rows),occupied_reporting_windows=sum(len(v) for _,v in rows),
                                     sampled_grid_hours=sum(r['sampled_grid_hours'] for r,_ in rows),
                                     mean_hourly_reporting_ids=mean(mean(v) for _,v in rows if v)))
    continuous=[]
    for r in hourly:
        continuous.append(dict(processing_key=r['processing_key'],source_local_hour=r['source_local_hour'],
                               timezone_hypothesis=r['timezone_hypothesis'],sampled_grid_hours=r['sampled_grid_hours'],
                               **{v:r[v+'_mean'] for v,_ in specs},
                               **{f'reporting_ids_{width}':mean(windows[(r['processing_key'],width,r['source_local_hour'][:13])]) for width in (1,5,15)}))
    return dict(cell_hour=cell_tables,episode_onsets=onset_tables,reporting_hours=reporting_tables,continuous=continuous)
