"""Public map renderer: private detail is never an argument or embedded asset."""
from pathlib import Path
import base64
import gzip
from winterops.arcgis_source import canonical


def render(public,context):
    if public.get('schema')!='winterops-geospatial-v3-public':raise ValueError('GEO_PUBLIC_SCHEMA')
    allowed={'schema','scopes','weekly','daily','cells','sensors','movement','requests','reporting','episodes','roads','weather','public_map','local_payload_sha256','local_payload_bytes','local_payload_encoding','local_payloads','investigation'}
    if set(public)-allowed:raise ValueError('GEO_PRIVATE_FIELDS_IN_PUBLIC_PAYLOAD')
    def check(value):
        if isinstance(value,dict):
            if set(value)&{'truck_id','source_record_ordinals','first_observed','last_observed','raw_record_json','latitude','longitude','coordinates',
                           'evidence31','segment_marks','segments','passages','quality_cells','rejected_intervals','private_february_scopes','road_names',
                           'private_scope_label','source_record_number','ordinals','provider_attributes'}:
                raise ValueError('GEO_PRIVATE_FIELDS_IN_PUBLIC_PAYLOAD')
            for v in value.values():check(v)
        elif isinstance(value,list):
            for v in value:check(v)
    check(public)
    if 'investigation' in public:
        i=public['investigation']
        allowed_evidence={'schema','evidence','contracts','corridor_rankings','identifier_continuity','observation_support','observations',
                          'point_evidence','pooled_corridors','reference_weekly','sample_windows','scenarios','source_diagnostics',
                          'source_hour_activity','topology','weather','weather_provenance'}
        if i.get('schema')!='winterops-evidence-v31-public' or set(i)-allowed_evidence:raise ValueError('GEO_INVESTIGATION_PROJECTION')
        for road in i['pooled_corridors']:
            if set(road)!={'road_name','passage_candidates','supported_intervals','source_weeks_present'} or road['passage_candidates']<20 or road['source_weeks_present']<4:
                raise ValueError('GEO_PUBLIC_ROAD_GRAIN')
    for row in public['cells']:
        if set(row)!={'processing_key','spatial_bin','observation_count'} or row['observation_count']<20:
            raise ValueError('GEO_PUBLIC_DISPLAY_GRAIN')
    payload=dict(data=public,context=context)
    # Lossless public transport only: not an access-control or privacy mechanism.
    text=base64.b64encode(gzip.compress(canonical(payload),mtime=0)).decode('ascii')
    return (Path(__file__).parent/'templates/geospatial.html').read_text(encoding='utf-8').replace('__DATA__',text)
