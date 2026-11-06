"""Public map renderer: private detail is never an argument or embedded asset."""
from pathlib import Path
from winterops.arcgis_source import canonical


def render(public,context):
    if public.get('schema')!='winterops-geospatial-v3-public':raise ValueError('GEO_PUBLIC_SCHEMA')
    allowed={'schema','scopes','weekly','daily','cells','sensors','movement','requests','reporting','episodes','roads','weather','public_map','local_payload_sha256','local_payload_bytes','local_payload_encoding'}
    if set(public)-allowed:raise ValueError('GEO_PRIVATE_FIELDS_IN_PUBLIC_PAYLOAD')
    def check(value):
        if isinstance(value,dict):
            if set(value)&{'truck_id','source_record_ordinals','first_observed','last_observed','raw_record_json','latitude','longitude','coordinates'}:
                raise ValueError('GEO_PRIVATE_FIELDS_IN_PUBLIC_PAYLOAD')
            for v in value.values():check(v)
        elif isinstance(value,list):
            for v in value:check(v)
    check(public)
    for row in public['cells']:
        if set(row)!={'processing_key','spatial_bin','observation_count'} or row['observation_count']<20:
            raise ValueError('GEO_PUBLIC_DISPLAY_GRAIN')
    payload=dict(data=public,context=context)
    text=canonical(payload).decode().replace('<','\\u003c').replace('&','\\u0026')
    return (Path(__file__).parent/'templates/geospatial.html').read_text(encoding='utf-8').replace('__DATA__',text)
