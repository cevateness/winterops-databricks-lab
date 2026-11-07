"""WGS84 display, NAD83 / UTM 17N metre distances, conservative observations.

Optional geo dependencies are local analytics only. No road routing, snapping,
service completion, or source-record deletion occurs here.
"""
from collections import Counter
from datetime import datetime
from functools import lru_cache
import io
import math
import zipfile

from pyproj import Geod, Transformer
from shapely.geometry import LineString, MultiLineString, Point, Polygon, mapping
from shapely.strtree import STRtree

from winterops.operational_diagnostics import timestamp_events, state
from winterops.weather_analysis import conditional_instant

GEOD = Geod(ellps='WGS84')
TO_METRES = Transformer.from_crs(4326, 26917, always_xy=True)


def legacy_roads(path, expected_sha256):
    """Explicit official LL84 shapefile contract. No unsafe archive extraction.

    Preserve provider road-class codes; no undocumented code-to-priority mapping.
    Legacy OBJECTID is zero-filled, so COMPKEY is required unique within this file.
    """
    from pyproj import CRS
    import shapefile
    from winterops.sources import fingerprint
    if fingerprint(path)!=expected_sha256:raise ValueError('GEO_LEGACY_ROAD_BYTES')
    with zipfile.ZipFile(path) as z:
        if sum(i.file_size for i in z.infolist())>64_000_000:raise ValueError('GEO_ARCHIVE_SIZE')
        def member(ext):
            names=[n for n in z.namelist() if n.endswith('.'+ext)]
            if len(names)!=1:raise ValueError('GEO_ARCHIVE_MEMBERS')
            return z.read(names[0])
        if not CRS.from_wkt(member('prj').decode()).equals(CRS.from_epsg(4326),ignore_axis_order=True):
            raise ValueError('GEO_LEGACY_CRS')
        reader=shapefile.Reader(shp=io.BytesIO(member('shp')),shx=io.BytesIO(member('shx')),dbf=io.BytesIO(member('dbf')))
        required={'COMPKEY','FULL_NAME','RD_CLASS','SERV_STAT'}
        if reader.shapeType!=3 or not required<={f[0] for f in reader.fields[1:]}:raise ValueError('GEO_LEGACY_SCHEMA')
        features=[];keys=set()
        for i,sr in enumerate(reader.iterShapeRecords()):
            a=sr.record.as_dict();key=a['COMPKEY']
            if key in keys or not isinstance(key,int) or key<=0:raise ValueError('GEO_LEGACY_ROAD_KEY')
            keys.add(key);points=[list(p[:2]) for p in sr.shape.points];offsets=list(sr.shape.parts)+[len(points)]
            paths=[points[a:b] for a,b in zip(offsets,offsets[1:])]
            g=dict(paths=paths);geometry(g)
            features.append(dict(attributes=dict(OBJECTID=i+1,street_compkey=key,street_name=a['FULL_NAME'],
                                                 functional_classification=a['RD_CLASS'],service_status=a['SERV_STAT']),geometry=g))
    return dict(source=dict(provider='city_of_windsor',city='windsor_on',source='legacy_street_centreline_ll84',
                            source_sha256=expected_sha256,catalogue_posted='2025-01-14'),
                schema=dict(source_crs=4326,key='COMPKEY_UNIQUE_WITHIN_FILE',road_class='RD_CLASS_PROVIDER_CODE'),features=features)


def geometry(value):
    """ArcGIS outSR=4326 geometries; preserve multipart rings and holes."""
    if 'paths' in value:
        result = MultiLineString(value['paths'])
    elif 'rings' in value:
        # XOR implements ArcGIS nested rings independent of ring orientation.
        result = Polygon()
        for ring in value['rings']:
            part = Polygon(ring)
            if not part.is_valid:raise ValueError('GEO_INVALID_RING')
            result = result.symmetric_difference(part)
    elif 'x' in value and 'y' in value:
        result = Point(value['x'], value['y'])
    else:raise ValueError('GEO_UNSUPPORTED_GEOMETRY')
    if result.is_empty or not result.is_valid:raise ValueError('GEO_INVALID_GEOMETRY')
    if not (-180<=result.bounds[0]<=result.bounds[2]<=180 and -90<=result.bounds[1]<=result.bounds[3]<=90):
        raise ValueError('GEO_NOT_WGS84_LON_LAT')
    return result


def context_geojson(snapshot, kind):
    """Only official non-telemetry reference geometry is eligible for publication."""
    fields = {'roads':('street_compkey','street_name','functional_classification','service_status'),
              'wards':('ward_number',), 'boundary':('city_name',)}[kind]
    return dict(type='FeatureCollection', snapshot_id=__import__('winterops.arcgis_source',fromlist=['digest']).digest(snapshot),
                features=[dict(type='Feature',geometry=mapping(geometry(f['geometry'])),
                               properties={k:f['attributes'].get(k) for k in fields}) for f in snapshot['features']])


class RoadIndex:
    def __init__(self, snapshot, wards=None, boundary=None):
        self.records=[];self.lines=[]
        for f in snapshot['features']:
            a=f['attributes']
            for path in f['geometry']['paths']:
                line=LineString([TO_METRES.transform(*p[:2]) for p in path])
                if line.is_empty or not line.is_valid:raise ValueError('GEO_INVALID_ROAD')
                self.lines.append(line)
                self.records.append(dict(road_key=a['street_compkey'] if a['street_compkey'] is not None else 'snapshot_oid:'+str(a['OBJECTID']),road_name=a['street_name'],
                                         road_class=a['functional_classification']))
        self.tree=STRtree(self.lines)
        self.wards=[(f['attributes']['ward_number'],geometry(f['geometry'])) for f in (wards or {}).get('features',[])]
        self.boundaries=[geometry(f['geometry']) for f in (boundary or {}).get('features',[])]

    @lru_cache(maxsize=500_000)
    def match(self, lon, lat):
        if not (-84<=lon<=-81 and 41<=lat<=44):
            return dict(distance_m=None,road_key=None,road_class=None,road_name=None,ward=None,
                        in_city=False,status='OUTSIDE_LOCAL_PROJECTION_SCOPE',ambiguous=False)
        point=Point(*TO_METRES.transform(lon,lat))
        # Distances beyond 200m are intentionally censored; no nearest-city-road
        # claim for observations in another municipality or absent reference roads.
        candidates=self.tree.query(point.buffer(200))
        by_road={}
        for i in candidates:
            distance=point.distance(self.lines[i]);key=self.records[i]['road_key']
            if distance<=200 and (key not in by_road or distance<by_road[key][0]):by_road[key]=(distance,int(i))
        ordered=sorted(by_road.values())
        p=Point(lon,lat);wards=[n for n,g in self.wards if g.covers(p)]
        result=dict(ward=wards[0] if len(wards)==1 else None,ward_ambiguous=len(wards)>1,
                    in_city=any(g.covers(p) for g in self.boundaries),
                    distance_m=None,second_distance_m=None,road_key=None,road_name=None,road_class=None,
                    ambiguous=False,status='NO_ROAD_WITHIN_200M_REFERENCE_INCOMPLETE_OUTSIDE_CITY')
        if ordered:
            d,i=ordered[0];second=ordered[1][0] if len(ordered)>1 else None
            result.update(self.records[i],distance_m=d,second_distance_m=second,
                          ambiguous=d<=30 and second is not None and second-d<=10,
                          status='CANDIDATE_PROXIMITY_ONLY')
        return result


def observation_interval(a,b,timezone_hypothesis='America/Toronto'):
    """Reported endpoints and conditional elapsed time, independent of thresholds."""
    if timezone_hypothesis not in ('America/Toronto','UTC'):raise ValueError('GEO_CLOCK_HYPOTHESIS')
    try:seconds=(conditional_instant(b['time'],timezone_hypothesis)-conditional_instant(a['time'],timezone_hypothesis)).total_seconds()
    except ValueError:return dict(clock_status='clock_ambiguous_or_nonexistent',seconds=None,p=None,q=None,distance_m=None,speed_kph=None)
    ca={(r['longitude'],r['latitude']) for r in a['rows']};cb={(r['longitude'],r['latitude']) for r in b['rows']}
    p=next(iter(ca)) if len(ca)==1 else None;q=next(iter(cb)) if len(cb)==1 else None
    distance=GEOD.inv(*p,*q)[2] if p is not None and q is not None else None
    return dict(clock_status='known' if seconds>0 else 'nonpositive_elapsed_time',seconds=seconds,p=p,q=q,
                before=a['state'],after=b['state'],distance_m=distance,
                speed_kph=distance/seconds*3.6 if distance is not None and seconds>0 else None)


def interval_reason(interval,gap_seconds=60,speed_limit_kph=100,stationary_metres=3):
    """Shared conservative rule; order of unknown/rejection reasons is explicit."""
    e=interval
    if e['clock_status']!='known':return e['clock_status']
    if e['seconds']>gap_seconds:return 'recording_gap'
    if e['p'] is None or e['q'] is None:return 'coordinate_tie_unknown'
    if 'unknown' in e['before']+e['after']:return 'conflicting_state_unknown'
    if e['speed_kph']>speed_limit_kph:return 'questionable_speed'
    if e['distance_m']<=stationary_metres:return 'stationary'
    if e['before']!=e['after']:return 'equipment_state_change'
    return 'accepted'


def observed_fragments(rows, gap_seconds=60, speed_limit_kph=100, stationary_metres=3, timezone_hypothesis='America/Toronto'):
    """Private line segments between unambiguous consecutive timestamp groups.

    Every adjacent interval is accounted for once. Equal-time conflicts are not
    ordered into a path. State changes and stationary intervals are retained as
    diagnostics but excluded from same-state movement fragments.
    """
    if gap_seconds<=0 or speed_limit_kph<=0 or stationary_metres<0 or timezone_hypothesis not in ('America/Toronto','UTC'):raise ValueError('GEO_THRESHOLDS')
    events=timestamp_events(rows);segments=[];counts=Counter();speeds=[];spans=[]
    for (key,truck),seq in events.items():
        for a,b in zip(seq,seq[1:]):
            evidence=observation_interval(a,b,timezone_hypothesis)
            seconds,distance,speed=evidence['seconds'],evidence['distance_m'],evidence['speed_kph']
            reason=interval_reason(evidence,gap_seconds,speed_limit_kph,stationary_metres)
            if reason in ('accepted','questionable_speed','stationary','equipment_state_change'):
                speeds.append(speed);spans.append(seconds)
            counts[reason]+=1
            if reason=='accepted':
                segments.append(dict(processing_key=key,truck_id=truck,start=a['time'].isoformat(' '),end=b['time'].isoformat(' '),
                                     coordinates=[list(evidence['p']),list(evidence['q'])],state=a['state'],
                                     distance_m=distance,apparent_speed_kph=speed,
                                     source_record_ordinals=[[r['source_record_number'] for r in e['rows']] for e in (a,b)]))
    return dict(segments=segments,intervals=dict(counts),timestamp_groups=sum(map(len,events.values())),
                contradictory_groups=sum(e['state'].startswith('unknown') for seq in events.values() for e in seq),
                coordinate_conflict_groups=sum(len({(r['longitude'],r['latitude']) for r in e['rows']})>1 for seq in events.values() for e in seq),
                speed_support=len(speeds),speed_over_60=sum(v>60 for v in speeds),speed_over_100=sum(v>100 for v in speeds),
                speed_over_150=sum(v>150 for v in speeds),source_identifier_scopes=len(events))


def sensor_summary(rows, roads):
    counts=Counter();classes=Counter();ward_counts=Counter();proximity=Counter()
    previous_by_id={};order_reversals=0
    for r in sorted(rows,key=lambda r:r['source_record_number']):
        key=(r['processing_key'],r['truck_id']);t=datetime.fromisoformat(r['event_time_unzoned'])
        if key in previous_by_id and t<previous_by_id[key]:order_reversals+=1
        previous_by_id[key]=t
        m=roads.match(r['longitude'],r['latitude'])
        counts['observations']+=1;counts['inside_current_city_boundary']+=int(m['in_city'])
        counts['road_ambiguous_at_30m']+=int(m['ambiguous']);counts['no_road_within_200m']+=int(m['distance_m'] is None)
        for limit in (15,30,60):proximity[str(limit)]+=int(m['distance_m'] is not None and m['distance_m']<=limit)
        if m['distance_m'] is not None and m['distance_m']<=30:classes[m['road_class'] or 'unclassified']+=1
        ward_counts[str(m['ward']) if m['ward'] is not None else 'outside_or_ambiguous']+=1
        counts['repeated_payload_observations']+=int(r['has_repeated_payload'])
        counts['engine_off_with_equipment']+=int(not r['engine_active'] and (r['plow_active'] or r['spreader_active']))
    return dict(**counts,source_record_time_reversals=order_reversals,within_road_metres=dict(proximity),
                candidate_road_class_30m=dict(classes),current_ward_observations=dict(ward_counts))
