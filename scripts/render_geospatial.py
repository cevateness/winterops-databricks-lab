"""Rebuild the offline public map; optionally pin a separate private file.

The renderer never accepts private observations. Only SHA-256 and byte size of a
local payload enter public output. Default replay needs no private files/network.
"""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from winterops.geospatial_dashboard import render
from winterops.sources import fingerprint,outside_git
from winterops.arcgis_source import canonical

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--public',type=Path,default=ROOT/'dashboard/geospatial.json')
    p.add_argument('--context',type=Path,default=ROOT/'dashboard/context')
    p.add_argument('--private-payload',type=Path)
    p.add_argument('--investigation',type=Path,default=ROOT/'docs/ROAD_EVIDENCE_V31_RESULTS.json',help='Vetted V3.1 aggregate results, never private detail')
    p.add_argument('--baseline-only',action='store_true',help='Render original V3 aggregates without the V3.1 extension')
    p.add_argument('--output',type=Path,required=True);p.add_argument('--save-public',type=Path)
    a=p.parse_args();public=json.loads(a.public.read_text(encoding='utf-8'))
    if not a.baseline_only:
        public['investigation']=json.loads(a.investigation.read_text(encoding='utf-8'))
        receipt=json.loads((ROOT/'docs/ROAD_EVIDENCE_V31_EXECUTION.json').read_text(encoding='utf-8'))
        public['local_payloads']=public.get('local_payloads',[dict(sha256=public['local_payload_sha256'],bytes=public['local_payload_bytes'],encoding=public['local_payload_encoding'])])
        pin=dict(sha256=receipt['private_payload_sha256'],bytes=receipt['private_payload_bytes'],encoding='gzip')
        if pin not in public['local_payloads']:public['local_payloads'].append(pin)
    if a.private_payload:
        detail=outside_git(a.private_payload)
        pins=public.get('local_payloads',[dict(sha256=public['local_payload_sha256'],bytes=public['local_payload_bytes'],encoding=public['local_payload_encoding'])])
        pin=dict(sha256=fingerprint(detail),bytes=detail.stat().st_size,encoding='gzip' if detail.suffix=='.gz' else 'utf-8-json')
        if pin not in pins:pins.append(pin)
        public['local_payloads']=pins
    context={name:json.loads((a.context/(name+'.geojson')).read_text(encoding='utf-8')) for name in ('roads','wards','boundary')}
    a.output.write_text(render(public,context),encoding='utf-8')
    if a.save_public:a.save_public.write_bytes(canonical(public)+b'\n')
    print(json.dumps(dict(evidence='PUBLIC_AGGREGATE_RENDER_ONLY',private_embedded=False,roads=len(context['roads']['features']),output_bytes=a.output.stat().st_size)))

if __name__=='__main__':main()
