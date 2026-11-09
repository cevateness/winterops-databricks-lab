"""Source-scoped sensor diagnostics, never a sensor-accuracy certification."""
from collections import Counter,defaultdict
from datetime import datetime
from statistics import mean

from winterops.geospatial import GEOD,observation_interval,interval_reason
from winterops.operational_diagnostics import state,percentile


def conflict_review(events):
    conflicts=[];identifier_counts=Counter();combos=Counter();order=Counter();separation=[]
    fields=('conflicting_groups','observations_in_conflicting_groups','same_coordinate_conflicts','coordinates_separated_over_30m',
            'coordinates_separated_over_1000m','consecutive_source_ordinals','groups_with_repeated_payload_records',
            'whole_second_timestamps','previous_group_within_15s','next_group_within_15s','known_same_state_neighbours','known_different_state_neighbours',
            'known_different_state_neighbours_both_within_15s','known_same_state_neighbours_both_within_15s')
    counts=Counter({k:0 for k in fields});counts['timestamp_groups']=sum(map(len,events.values()))
    for identity,seq in events.items():
        for i,e in enumerate(seq):
            values=e['rows'];states={state(r) for r in values}
            if len(states)<2:continue
            counts['conflicting_groups']+=1;counts['observations_in_conflicting_groups']+=len(values)
            identifier_counts[identity]+=1;combos[' + '.join(sorted(states))]+=1
            coords={(r['longitude'],r['latitude']) for r in values}
            distance=max((GEOD.inv(*a,*b)[2] for a in coords for b in coords),default=0)
            separation.append(distance)
            counts['same_coordinate_conflicts']+=len(coords)==1
            counts['coordinates_separated_over_30m']+=distance>30
            counts['coordinates_separated_over_1000m']+=distance>1000
            ordinals=sorted(r['source_record_number'] for r in values)
            counts['consecutive_source_ordinals']+=all(b-a==1 for a,b in zip(ordinals,ordinals[1:]))
            counts['groups_with_repeated_payload_records']+=any(r['has_repeated_payload'] for r in values)
            counts['whole_second_timestamps']+=e['time'].microsecond==0
            ordered=[state(r) for r in sorted(values,key=lambda r:r['source_record_number'])]
            order[' → '.join(ordered)]+=1
            if i:
                counts['previous_group_within_15s']+=(e['time']-seq[i-1]['time']).total_seconds()<=15
            if i+1<len(seq):
                counts['next_group_within_15s']+=(seq[i+1]['time']-e['time']).total_seconds()<=15
            if 0<i<len(seq)-1:
                before,after=seq[i-1]['state'],seq[i+1]['state']
                counts['known_same_state_neighbours']+=before==after and not before.startswith('unknown')
                counts['known_different_state_neighbours']+=before!=after and 'unknown' not in before+after
                short=(e['time']-seq[i-1]['time']).total_seconds()<=15 and (seq[i+1]['time']-e['time']).total_seconds()<=15
                counts['known_different_state_neighbours_both_within_15s']+=short and before!=after and 'unknown' not in before+after
                counts['known_same_state_neighbours_both_within_15s']+=short and before==after and 'unknown' not in before
            conflicts.append(e)
    n=counts['conflicting_groups']
    return dict(**counts,source_identifier_scopes=len(events),scopes_with_conflicts=len(identifier_counts),
                largest_scope_conflicts=max(identifier_counts.values(),default=0),top_five_scope_conflicts=sum(v for _,v in identifier_counts.most_common(5)),
                state_combinations=dict(combos),source_ordinal_state_sequences=dict(order),
                coordinate_separation_m=dict(n=len(separation),p50=percentile(separation,.5),p95=percentile(separation,.95),maximum=max(separation,default=None))),conflicts


def february_case(rows,events,road_index):
    """Private scope table plus public concentration/category aggregates.

    Scope labels are local rank labels, not actual truck IDs or stable vehicle
    identities. Public projection removes even those labels and per-scope times.
    """
    private=[];categories=Counter();points=Counter();stationary_total=0
    for ordinal,(identity,seq) in enumerate(events.items()):
        observations=[r for e in seq for r in e['rows']];stationary=0;longest=run=1
        for a,b in zip(seq,seq[1:]):
            reason=interval_reason(observation_interval(a,b))
            stationary+=reason=='stationary'
            if reason=='stationary':run+=1
            else:longest=max(longest,run);run=1
        longest=max(longest,run);stationary_total+=stationary
        own_categories=Counter()
        for row in observations:
            m=road_index.match(row['longitude'],row['latitude']);near=m['distance_m'] is not None and m['distance_m']<=30
            category=('inside_city' if m['in_city'] else 'outside_city')+('_within_30m' if near else '_not_within_30m')
            own_categories[category]+=1;categories[category]+=1;points[(row['longitude'],row['latitude'])]+=1
        own_points=Counter((r['longitude'],r['latitude']) for r in observations)
        private.append(dict(private_scope_label='S'+str(ordinal+1).zfill(3),observations=len(observations),timestamp_groups=len(seq),
                            consecutive_intervals=max(0,len(seq)-1),stationary_intervals=stationary,longest_stationary_timestamp_run=longest,
                            distinct_reported_coordinates=len(own_points),dominant_coordinate_observations=max(own_points.values()),categories=dict(own_categories)))
    counts=sorted((p['observations'] for p in private),reverse=True)
    dominant=points.most_common(1)[0][0]
    scopes=[]
    for identity,seq in events.items():
        own=[e['time'] for e in seq if any((r['longitude'],r['latitude'])==dominant for r in e['rows'])]
        if own:scopes.append((min(own),max(own)))
    overlap=sum(max(a[0],b[0])<=min(a[1],b[1]) for i,a in enumerate(scopes) for b in scopes[i+1:])
    return dict(observations=len(rows),identifier_scopes=len(events),stationary_intervals=stationary_total,
                categories=dict(categories),distinct_reported_coordinates=len(points),
                dominant_coordinate_observations=max(points.values()),dominant_coordinate_identifier_scopes=len(scopes),
                dominant_coordinate_scope_span_overlap_pairs=overlap,dominant_coordinate_scope_pairs=len(scopes)*(len(scopes)-1)//2,
                top_five_coordinate_observations=sum(n for _,n in points.most_common(5)),
                largest_scope_observations=max(counts),top_five_scope_observations=sum(counts[:5]),
                scopes_all_observations_at_one_coordinate=sum(p['distinct_reported_coordinates']==1 for p in private),
                longest_stationary_timestamp_run=max(p['longest_stationary_timestamp_run'] for p in private)),private


def scope_patterns(events):
    """Lifecycle clues, not stable vehicle IDs or inferred engine sessions."""
    spans=[];cadence=[];inversions=0;comparisons=0
    for seq in events.values():
        spans.append((seq[-1]['time']-seq[0]['time']).total_seconds())
        cadence.extend((b['time']-a['time']).total_seconds() for a,b in zip(seq,seq[1:]))
        original=sorted((r for e in seq for r in e['rows']),key=lambda r:r['source_record_number'])
        for a,b in zip(original,original[1:]):
            inversions+=a['event_time_unzoned']>b['event_time_unzoned'];comparisons+=1
    return dict(identifier_scopes=len(spans),scopes_span_le_four_hours=sum(s<=14400 for s in spans),
                scopes_span_3h55_to_4h=sum(14100<=s<=14400 for s in spans),
                apparent_scope_span_seconds=dict(p50=percentile(spans,.5),p95=percentile(spans,.95),maximum=max(spans,default=None)),
                consecutive_timestamp_intervals=len(cadence),intervals_le_15s=sum(s<=15 for s in cadence),
                interval_seconds_p50=percentile(cadence,.5),interval_seconds_p95=percentile(cadence,.95),
                within_identifier_source_ordinal_pairs=comparisons,source_order_time_inversions=inversions,
                interpretation='SOURCE_IDENTIFIER_LIFECYCLE_UNDOCUMENTED_NOT_VERIFIED_PHYSICAL_VEHICLE_OR_ENGINE_SESSION')


def identifier_continuity(scope_ids):
    counts=Counter(identity for identities in scope_ids for identity in identities)
    return dict(distinct_reported_identifier_strings=len(counts),source_identifier_scopes=sum(counts.values()),
                strings_in_multiple_source_weeks=sum(n>1 for n in counts.values()),
                source_week_frequency_histogram=dict(Counter(counts.values())),
                conclusion='REPEATED_IDENTIFIER_STRINGS_NOT_VERIFIED_CROSS_WEEK_PHYSICAL_VEHICLE_IDENTITIES')
