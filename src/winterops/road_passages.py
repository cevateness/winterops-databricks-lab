"""Conservative observed road correspondence. No routing solver or service label.

Point proximity, heading support and provider-node connectivity are distinct
evidence. A candidate passage needs >=3 timestamp groups (>=2 intervals), stable
state, a continuous reported sequence and >=20m projected progress. Thresholds
are descriptive assumptions, never calibrated probabilities.
"""
from collections import Counter,defaultdict
from dataclasses import dataclass,replace
from functools import lru_cache
import io
import math
import zipfile

from shapely.geometry import Point
from winterops.geospatial import TO_METRES,observation_interval,interval_reason


@dataclass(frozen=True)
class PassagePolicy:
    distance_m: float=30
    heading_degrees: float=30
    gap_seconds: int=60
    alternative_separation_m: float=10
    speed_kph: float=100
    minimum_heading_displacement_m: float=10
    maximum_stretch: float=1.5

    def __post_init__(self):
        if not (0<self.distance_m<=60 and 0<=self.heading_degrees<=90 and 0<self.gap_seconds<=120
                and 0<=self.alternative_separation_m<=30 and 0<self.speed_kph<=150
                and self.minimum_heading_displacement_m>=3 and self.maximum_stretch>=1):raise ValueError('PASSAGE_POLICY')


def sensitivity_policies():
    p=PassagePolicy()
    return dict(reference=p,distance_15=replace(p,distance_m=15),distance_60=replace(p,distance_m=60),
                heading_15=replace(p,heading_degrees=15),heading_45=replace(p,heading_degrees=45),
                gap_30=replace(p,gap_seconds=30),gap_120=replace(p,gap_seconds=120),
                separation_0=replace(p,alternative_separation_m=0),separation_20=replace(p,alternative_separation_m=20),
                speed_60=replace(p,speed_kph=60),speed_150=replace(p,speed_kph=150))


def legacy_nodes(path):
    """Join actual DBF node attributes by exact COMPKEY; no proximity transfer."""
    import shapefile
    with zipfile.ZipFile(path) as z:
        name=next(n for n in z.namelist() if n.endswith('.dbf'))
        r=shapefile.Reader(dbf=io.BytesIO(z.read(name)))
        result={}
        for row in r.records():
            a=row.as_dict();key=a['COMPKEY']
            if key in result:raise ValueError('PASSAGE_DUPLICATE_ROAD_KEY')
            result[key]=(a['START_NODE'],a['END_NODE'])
    return result


def angle_difference(a,b):
    """Unsigned road orientation: no undocumented legal direction inference."""
    return abs((a-b+90)%180-90)


class PassageMatcher:
    def __init__(self,index,nodes,maximum_candidates=24):
        self.index=index;self.maximum_candidates=maximum_candidates
        self.connections=defaultdict(list);ends=defaultdict(list)
        for i,line in enumerate(index.lines):
            key=index.records[i]['road_key']
            for end,node in enumerate(nodes.get(key,(0,0))):
                if node:
                    point=Point(line.coords[0 if end==0 else -1]);ends[node].append((i,0. if end==0 else line.length,point))
        bad=good=0
        for node,group in ends.items():
            for i,along,p in group:
                for j,other,q in group:
                    if i>=j or index.records[i]['road_key']==index.records[j]['road_key']:continue
                    gap=p.distance(q)
                    if gap<=5:
                        self.connections[(i,j)].append((along,other,gap,node));self.connections[(j,i)].append((other,along,gap,node));good+=1
                    else:bad+=1
        self.topology_audit=dict(provider_nodes=len(ends),connected_feature_pairs=good,node_geometry_mismatch_pairs=bad,
                                 rule='SHARED_NONZERO_PROVIDER_NODE_AND_ENDPOINT_DISTANCE_LE_5M_MAX_TWO_ROAD_FEATURES',legal_turns_verified=False)

    @lru_cache(maxsize=450000)
    def point(self,lon,lat):
        if not (-84<=lon<=-81 and 41<=lat<=44):return ()
        p=Point(*TO_METRES.transform(lon,lat));values=[]
        for raw in self.index.tree.query(p,predicate='dwithin',distance=60):
            i=int(raw);line=self.index.lines[i];along=line.project(p)
            a=line.interpolate(max(0,along-5));b=line.interpolate(min(line.length,along+5))
            heading=math.degrees(math.atan2(b.y-a.y,b.x-a.x))%180
            values.append((p.distance(line),i,along,heading))
        by_key={}
        for value in sorted(values):by_key.setdefault(self.index.records[value[1]]['road_key'],value)
        return tuple(sorted(by_key.values()))

    def alternatives(self,e):
        """Precompute geometry once; threshold experiments reuse these alternatives."""
        if e['p'] is None or e['q'] is None:return dict(overflow=False,paths=[],nearest=None)
        a=self.point(*e['p']);b=self.point(*e['q'])
        if len(a)>self.maximum_candidates or len(b)>self.maximum_candidates:return dict(overflow=True,paths=[],nearest=None)
        x1,y1=TO_METRES.transform(*e['p']);x2,y2=TO_METRES.transform(*e['q'])
        bearing=math.degrees(math.atan2(y2-y1,x2-x1))%360
        heading=bearing%180;direction=int((bearing+45)//90)%4;paths=[]
        nearest=(a[0][1],b[0][1],max(a[0][0],b[0][0])) if a and b else None
        for da,i,pa,ha in a:
            for db,j,pb,hb in b:
                error=max(angle_difference(heading,ha),angle_difference(heading,hb));distance=max(da,db)
                if i==j:
                    paths.append(dict(indices=(i,),distance=distance,heading=error,length=abs(pb-pa),direction=direction,
                                      progress=abs(pb-pa),topology=False))
                elif (i,j) in self.connections:
                    for ea,eb,gap,node in self.connections[(i,j)]:
                        la,lb=abs(ea-pa),abs(pb-eb)
                        if min(la,lb)<5:continue
                        paths.append(dict(indices=(i,j),distance=distance,heading=error,length=la+gap+lb,direction=direction,
                                          progress=la+lb,topology=True))
        return dict(overflow=False,paths=paths,nearest=nearest)

    def match(self,e,alternatives,policy,method='topology'):
        reason=interval_reason(e,policy.gap_seconds,policy.speed_kph)
        if reason!='accepted':return dict(tier=0,reason=reason,path=None,alternatives=0)
        if e['distance_m']<policy.minimum_heading_displacement_m:return dict(tier=3,reason='heading_displacement_too_short',path=None,alternatives=0)
        if alternatives['overflow']:return dict(tier=3,reason='candidate_limit_unknown',path=None,alternatives=0)
        if method=='nearest':
            n=alternatives['nearest']
            paths=[p for p in alternatives['paths'] if n and n[0]==n[1] and p['indices']==(n[0],) and p['distance']<=policy.distance_m]
        else:
            paths=[p for p in alternatives['paths'] if p['distance']<=policy.distance_m and p['heading']<=policy.heading_degrees
                   and p['length']<=policy.maximum_stretch*e['distance_m']+10 and (method=='topology' or not p['topology'])]
        paths.sort(key=lambda p:(p['distance'],p['heading'],p['indices']))
        # One route alternative per ordered road-feature path; duplicates from
        # coincident provider nodes must not manufacture extra confidence.
        unique={}
        for p in paths:unique.setdefault(p['indices'],p)
        paths=list(unique.values())
        if not paths:return dict(tier=3,reason='no_supported_road_path',path=None,alternatives=0)
        if method!='nearest' and len(paths)>1 and paths[1]['distance']-paths[0]['distance']<=policy.alternative_separation_m:
            return dict(tier=3,reason='road_alternative_ambiguous',path=None,alternatives=len(paths))
        return dict(tier=3,reason='pair_supported_sequence_required',path=paths[0],alternatives=len(paths))


def passage_runs(intervals,matches,index,connections=None):
    """Coalesce supported consecutive intervals by source/ID/corridor/state.

    No passage across a missing/rejected interval, reversing projected direction
    or a different corridor. A junction between different names is context only.
    """
    runs=[];current=[];current_key=None
    def finish():
        nonlocal current
        if len(current)>=2:
            progress=sum(matches[i]['path']['progress'] for i in current)
            if progress>=20:
                first,last=intervals[current[0]],intervals[current[-1]]
                observations={n for i in current for n in intervals[i]['ordinals']}
                runs.append(dict(indices=list(current),road_name=current_key[2],start=first['start'],end=last['end'],
                                 interval_count=len(current),observation_count=len(observations),state=first['before'],
                                 direction=current_key[4],topology_steps=sum(matches[i]['path']['topology'] for i in current)))
        current=[]
    for i,(e,m) in enumerate(zip(intervals,matches)):
        path=m['path'];names={index.records[j]['road_name'] for j in path['indices']} if path else set()
        if len(names)!=1 or not next(iter(names),None):finish();current_key=None;continue
        name=next(iter(names));direction=path['direction']
        key=(e['processing_key'],e['truck_id'],name,e['before'],direction)
        compatible=key==current_key
        if current:
            previous=matches[current[-1]]['path']['indices']
            connected=bool(set(previous)&set(path['indices'])) or any((a,b) in (connections or {}) for a in previous for b in path['indices'])
            compatible=compatible and connected
        if current and (not compatible or e['start']!=intervals[current[-1]]['end']):finish()
        if not current:current_key=key
        current.append(i)
    finish();return runs
