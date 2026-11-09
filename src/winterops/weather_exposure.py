"""Fixed-reference continuous retrospective exposure, independent of activity.

These two reference series are not vehicle/cell-matched February weather. North
is regional sensitivity, not a second Windsor neighbourhood or weather station.
"""
from collections import Counter,defaultdict
from datetime import datetime,timedelta,timezone
from pathlib import Path
from statistics import mean,correlation as _pearson,StatisticsError

from winterops.weather import WeatherRequest,acquire_snapshot,load_snapshot,canonical,digest,require
from winterops.weather_analysis import conditional_instant

UTC=timezone.utc
REFERENCES=(dict(reference_id='windsor_centre',latitude=42.3149,longitude=-83.0364,
                 definition='EXISTING_PUBLIC_FIXED_WINDSOR_REFERENCE_NOT_ACTIVITY_DERIVED'),
            dict(reference_id='regional_north',latitude=42.5,longitude=-83.,
                 definition='PREDECLARED_PUBLIC_QUARTER_DEGREE_REGIONAL_NORTH_SENSITIVITY_NOT_CITY_NEIGHBOURHOOD'))
PERIODS=(('2026-01-04','2026-02-03'),('2026-02-04','2026-02-23'))
START='2026-01-05';END='2026-02-23'


def correlation(x,y):
    if len(x)<3:return None
    try:return _pearson(x,y)
    except StatisticsError:return None


def collect(root):
    """Explicit opt-in four GETs; immutable reuse is inherited from weather.py."""
    for ref in REFERENCES:
        for start,end in PERIODS:
            acquire_snapshot(Path(root)/ref['reference_id']/start,
                             WeatherRequest(start,end,ref['latitude'],ref['longitude'],grid_only=True))


def load_references(root):
    facts={};refs=[];receipts=[]
    for ref in REFERENCES:
        expected_grid=None
        for start,end in PERIODS:
            metadata,rows=load_snapshot(Path(root)/ref['reference_id']/start)
            request=WeatherRequest(start,end,ref['latitude'],ref['longitude'],grid_only=True)
            require(metadata['request_id']==request.request_id,'EXPOSURE_FIXED_REFERENCE_REQUEST')
            grid=metadata['grid'];grid_id=digest(canonical(dict(provider='open-meteo',requested_model='era5',grid_only=True,**grid)))
            require(expected_grid in (None,grid_id),'EXPOSURE_REFERENCE_GRID_CHANGED');expected_grid=grid_id
            for row in rows:
                k=(grid_id,row['valid_time_utc']);values={m:row[m] for m in ('temperature_2m_c','precipitation_preceding_hour_mm','snowfall_preceding_hour_cm')}
                require(k not in facts or facts[k]==values,'EXPOSURE_DUPLICATE_FACT_CONFLICT');facts[k]=values
            receipts.append(dict(reference_id=ref['reference_id'],request_id=request.request_id,
                                 response_sha256=metadata['response_sha256'],response_bytes=metadata['response_bytes'],
                                 retrieved_at_utc=metadata['retrieved_at_utc'],rows=len(rows)))
        refs.append(dict(reference_id=ref['reference_id'],definition=ref['definition'],grid_id=expected_grid,
                         requested_lon_lat=[ref['longitude'],ref['latitude']],returned_centre_lon_lat=[grid['longitude'],grid['latitude']]))
    require(len(facts)==2448,'EXPOSURE_EXPECTED_DISTINCT_GRID_HOURS')
    return facts,refs,receipts


def exposure_calendar(facts,refs,hourly,reporting,start=START,end=END):
    """Create all clock hours first, then left join activity and fixed weather."""
    activity={}
    for row in hourly:
        key=row['source_local_naive_hour']
        require(key not in activity,'EXPOSURE_SOURCE_HOUR_OVERLAP');activity[key]=row
    reporting_hours=defaultdict(list)
    for row in reporting:
        if row['bucket_minutes']==5:reporting_hours[row['source_local_bucket'][:13]+':00:00'].append(row['reporting_ids'])
    result=[];stamp=datetime.fromisoformat(start);stop=datetime.fromisoformat(end)
    while stamp<stop:
        text=stamp.isoformat(' ');a=activity.get(text)
        for zone in ('America/Toronto','UTC'):
            instant=conditional_instant(stamp,zone)
            for ref in refs:
                grid=ref['grid_id']
                def fact(offset):return facts.get((grid,(instant+timedelta(hours=offset)).isoformat()),{})
                t,p= fact(0),fact(1)
                def antecedent(field):
                    values=[fact(i).get(field) for i in (-1,0)]
                    return sum(values) if all(v is not None for v in values) else None
                row=dict(source_local_hour=text,valid_time_utc=instant.isoformat(),timezone_hypothesis=zone,
                         reference_id=ref['reference_id'],grid_id=grid,
                         telemetry_status='RECORDED' if a else 'MISSING_TELEMETRY_ACTIVITY_UNKNOWN',
                         observation_count=a['observation_count'] if a else None,
                         processing_key=a['processing_key'] if a else None,
                         plow_active_observations=a['plow_active_observations'] if a else None,
                         spreader_active_observations=a['spreader_active_observations'] if a else None,
                         mean_reporting_ids_5m=mean(reporting_hours[text]) if text in reporting_hours else a.get('mean_reporting_ids_5m') if a else None,
                         quality_mean_reporting_ids_5m=a.get('quality_mean_reporting_ids_5m') if a else None,
                         temperature_2m_c=t.get('temperature_2m_c'),
                         precipitation_activity_hour_mm=p.get('precipitation_preceding_hour_mm'),
                         snowfall_activity_hour_cm=p.get('snowfall_preceding_hour_cm'),
                         precipitation_antecedent_mm=antecedent('precipitation_preceding_hour_mm'),
                         snowfall_antecedent_cm=antecedent('snowfall_preceding_hour_cm'))
                row['missing_weather']=any(row[f] is None for f in ('temperature_2m_c','precipitation_activity_hour_mm','snowfall_activity_hour_cm','precipitation_antecedent_mm','snowfall_antecedent_cm'))
                result.append(row)
        stamp+=timedelta(hours=1)
    require(len({(r['reference_id'],r['timezone_hypothesis'],r['source_local_hour']) for r in result})==len(result),'EXPOSURE_UNIQUE_KEYS')
    return result


def exposure_summary(calendar,dry_hours=6):
    require(dry_hours in (3,6,12),'EXPOSURE_EVENT_DRY_GAP')
    groups=defaultdict(list)
    for row in calendar:groups[(row['reference_id'],row['timezone_hypothesis'])].append(row)
    summary=[];relationships=[];events=[]
    for (ref,zone),rows in groups.items():
        recorded=[r for r in rows if r['telemetry_status']=='RECORDED']
        summary.append(dict(reference_id=ref,timezone_hypothesis=zone,hours=len(rows),recorded_hours=len(recorded),
                            missing_telemetry_hours=len(rows)-len(recorded),missing_weather_hours=sum(r['missing_weather'] for r in rows),
                            snowy_recorded_hours=sum(r['snowfall_activity_hour_cm'] is not None and r['snowfall_activity_hour_cm']>=.1 for r in recorded),
                            snowy_unrecorded_hours=sum(r['telemetry_status']!='RECORDED' and r['snowfall_activity_hour_cm'] is not None and r['snowfall_activity_hour_cm']>=.1 for r in rows)))
        cohorts=defaultdict(list)
        cohorts['all']=recorded
        cohorts['january']=[r for r in recorded if r['source_local_hour']<'2026-02-02']
        cohorts['february']=[r for r in recorded if r['source_local_hour']>='2026-02-02']
        cohorts['without_feb09']=[r for r in recorded if not '2026-02-09'<=r['source_local_hour']<'2026-02-16']
        for r in recorded:cohorts[r['processing_key']].append(r)
        for key,values in cohorts.items():
            for variable in ('temperature_2m_c','snowfall_activity_hour_cm','snowfall_antecedent_cm','precipitation_activity_hour_mm','precipitation_antecedent_mm'):
                pairs=[(r[variable],r['mean_reporting_ids_5m']) for r in values if r[variable] is not None and r['mean_reporting_ids_5m'] is not None]
                relationships.append(dict(reference_id=ref,timezone_hypothesis=zone,processing_key=key,variable=variable,
                                          occupied_source_hours=len(pairs),pearson_r=correlation([a for a,b in pairs],[b for a,b in pairs]),
                                          quality_filtered_hours=sum(r[variable] is not None and r.get('quality_mean_reporting_ids_5m') is not None for r in values),
                                          quality_filtered_pearson_r=correlation([r[variable] for r in values if r[variable] is not None and r.get('quality_mean_reporting_ids_5m') is not None],
                                                                              [r['quality_mean_reporting_ids_5m'] for r in values if r[variable] is not None and r.get('quality_mean_reporting_ids_5m') is not None])))
        # Snow events are defined by weather alone, including all unrecorded hours.
        wet=[r for r in rows if r['snowfall_activity_hour_cm'] is not None and r['snowfall_activity_hour_cm']>=.1]
        clusters=[]
        for row in wet:
            if not clusters or datetime.fromisoformat(row['valid_time_utc'])-datetime.fromisoformat(clusters[-1][-1]['valid_time_utc'])>=timedelta(hours=dry_hours+1):clusters.append([])
            clusters[-1].append(row)
        for i,event in enumerate(clusters):
            lo,hi=event[0]['source_local_hour'],event[-1]['source_local_hour']
            span=[r for r in rows if lo<=r['source_local_hour']<=hi]
            events.append(dict(reference_id=ref,timezone_hypothesis=zone,event_ordinal=i+1,start_source_local=lo,
                               end_source_local_exclusive=(datetime.fromisoformat(hi)+timedelta(hours=1)).isoformat(' '),
                               hours=len(span),snowy_hours=len(event),recorded_hours=sum(r['telemetry_status']=='RECORDED' for r in span),
                               snowfall_cm=sum(r['snowfall_activity_hour_cm'] for r in span) if all(r['snowfall_activity_hour_cm'] is not None for r in span) else None,
                               missing_weather_hours=sum(r['missing_weather'] for r in span),
                               boundary_context_incomplete=(datetime.fromisoformat(lo)-datetime.fromisoformat(rows[0]['source_local_hour'])<timedelta(hours=dry_hours)
                                                            or datetime.fromisoformat(rows[-1]['source_local_hour'])-datetime.fromisoformat(hi)<timedelta(hours=dry_hours)),
                               mean_reporting_ids_in_recorded_hours=mean([r['mean_reporting_ids_5m'] for r in span if r['mean_reporting_ids_5m'] is not None]) if any(r['mean_reporting_ids_5m'] is not None for r in span) else None))
    return dict(calendar=summary,relationships=relationships,weather_defined_events=events,
                event_rule=f'SNOWFALL_GE_0_1CM_PER_HOUR_SEPARATED_BY_AT_LEAST_{dry_hours}_DRY_HOURS',
                interpretation='NO_TELEMETRY_IS_UNKNOWN_DEPLOYMENT_NOT_ZERO_DEPLOYMENT_REFERENCE_WEATHER_NOT_ALL_POSITION_MATCHED')


def reference_weekly(calendar,scopes):
    result=[]
    fields=('temperature_2m_c','precipitation_activity_hour_mm','snowfall_activity_hour_cm','precipitation_antecedent_mm','snowfall_antecedent_cm')
    for s in scopes:
        groups=defaultdict(list)
        for r in calendar:
            if s['source_week_start']<=r['source_local_hour']<s['source_week_end_exclusive']:
                groups[(r['reference_id'],r['timezone_hypothesis'])].append(r)
        for (ref,zone),rows in groups.items():
            result.append(dict(week=s['source_week_start'],reference_id=ref,timezone_hypothesis=zone,hours=len(rows),
                               missing_weather_hours=sum(r['missing_weather'] for r in rows),
                               means={f:mean([r[f] for r in rows if r[f] is not None]) if any(r[f] is not None for r in rows) else None for f in fields}))
    return result
