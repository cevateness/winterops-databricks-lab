"""Explicit bounded public layer extraction, outside Git. No native platform calls."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from winterops.arcgis_source import ArcGISSource,PublicClient,snapshot,canonical


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--layer-url',required=True);p.add_argument('--provider',required=True)
    p.add_argument('--city',required=True);p.add_argument('--source',required=True)
    p.add_argument('--where',required=True);p.add_argument('--max-records',required=True,type=int)
    p.add_argument('--output',required=True,type=Path);p.add_argument('--fields')
    p.add_argument('--schema-sha256');p.add_argument('--max-requests',type=int,default=120)
    a=p.parse_args();c=PublicClient(a.output/'http',max_requests=a.max_requests)
    _,r=snapshot(ArcGISSource(a.provider,a.city,a.source,a.layer_url),c,a.output/'snapshots',a.where,a.max_records,
                 expected_schema=a.schema_sha256,fields=tuple(a.fields.split(',')) if a.fields else None)
    print(json.dumps(dict(state=r['state'],snapshot_id=r['snapshot_id'],records=r['records'],
                          schema_sha256=r['schema_sha256'],requests=c.requests,bytes=c.bytes)))

if __name__=='__main__':main()
