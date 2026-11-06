"""Opt-in bounded public re-acquisition of the recorded V3 source scopes.

No weather downloads. A changed snapshot is retained but rejected for exact
replay; use the private replay package when a public source has been revised.
"""
import argparse
from pathlib import Path
import json
import sys
from urllib.request import build_opener
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from winterops.arcgis_source import ArcGISSource,PublicClient,snapshot,canonical,semantic_fingerprint
from winterops.sources import LocalStager,WeeklySource,NoRedirect,outside_git,fingerprint,utc_now

ROOT=Path(__file__).resolve().parents[1]


def prepare(output):
    output=outside_git(output)
    if output.exists():raise ValueError('V3_ACQUISITION_TARGET_EXISTS')
    output.mkdir(parents=True);config=json.loads((ROOT/'docs/GEOSPATIAL_V3_SOURCES.json').read_text())
    stage=LocalStager(output/'csv')
    for item in config['weekly_csvs']:
        v,_=stage.download(WeeklySource(**item['source']))
        if v.source_file_sha256!=item['source_file_sha256'] or v.byte_count!=item['byte_count']:
            raise ValueError('V3_WEEKLY_REVISION_DETECTED')
    pin=config['legacy_roads'];target=output/'roads_legacy.zip'
    with build_opener(NoRedirect()).open(pin['url'],timeout=45) as r:
        if r.status!=200 or r.url!=pin['url']:raise ValueError('V3_ROAD_DOWNLOAD_RESPONSE')
        b=r.read(16_000_001)
        if len(b)>16_000_000:raise ValueError('V3_ROAD_DOWNLOAD_BOUND')
    with target.open('xb') as out:out.write(b)
    if len(b)!=pin['bytes'] or fingerprint(target)!=pin['sha256']:raise ValueError('V3_LEGACY_ROAD_REVISION')
    (output/'roads_legacy.receipt.json').write_bytes(canonical(dict(pin,retrieved_at_utc=utc_now())))
    client=PublicClient(output/'http',max_requests=120,max_bytes=40_000_000)
    for scope in config['arcgis_scopes']:
        payload,receipt=snapshot(ArcGISSource(**scope['source']),client,output/scope['name'],scope['where'],scope['max_records'],
                           expected_schema=scope['schema_sha256'],fields=tuple(scope['fields']) if scope['fields'] else None)
        (output/(scope['name']+'_receipt.json')).write_bytes(canonical(receipt))
        if semantic_fingerprint(payload)!=scope['semantic_sha256']:raise ValueError('V3_ARCGIS_REVISION_DETECTED_USE_PRIVATE_REPLAY')
    return dict(status='SEMANTIC_PUBLIC_SCOPES_REACQUIRED_NOT_RAW_BYTE_REPLAY',arcgis_requests=client.requests,arcgis_bytes=client.bytes,
                weekly_downloads=len(config['weekly_csvs']),legacy_road_downloads=1,weather_requests=0,native_requests=0)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True,type=Path)
    a=p.parse_args();print(json.dumps(prepare(a.output)))
