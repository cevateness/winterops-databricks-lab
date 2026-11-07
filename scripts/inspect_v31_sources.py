"""Optional bounded recollection of the published V3.1 source windows.

Default development/CI uses private cached snapshots instead. New snapshots may
contain revisions; never overwrite an accepted one or assume stable OBJECTIDs.
"""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from winterops.arcgis_source import ArcGISSource,PublicClient,snapshot,canonical
from winterops.sources import outside_git

ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    out=outside_git(a.output)
    if out.exists():raise ValueError('SOURCE_INSPECTION_OUTPUT_EXISTS')
    out.mkdir(parents=True);public=json.loads((ROOT/'docs/ROAD_EVIDENCE_V31_SOURCE_REVIEW.json').read_text());windows=public['samples']
    where=' OR '.join("(record_date >= TIMESTAMP '%s' AND record_date < TIMESTAMP '%s')"%(w['start'],w['end']) for w in windows)
    client=PublicClient(out/'http',max_requests=50,max_bytes=6500000)
    base='https://mappmycity.ca/arcgis/rest/services/open_data_services/'
    metadata={name:client.get(base+layer) for name,layer in [('roads','transportation/MapServer/23'),('major_roads','transportation/MapServer/13'),('county_roads','transportation/MapServer/10'),('requests','governmentservices/MapServer/58')]}
    (out/'metadata.json').write_bytes(canonical(metadata))
    (out/'road_nonnull_count.json').write_bytes(canonical(client.get(base+'transportation/MapServer/23/query',where='street_name IS NOT NULL',returnCountOnly='true')))
    data,receipt=snapshot(ArcGISSource('city_of_windsor','windsor_on','stratified_v31','https://mappmycity.ca/arcgis/rest/services/open_data_services/governmentservices/MapServer/62'),client,out/'telemetry',where,10000,batch_size=200,expected_schema=public['schema_sha256'])
    (out/'ledger.json').write_bytes(canonical(dict(requests=client.requests,response_bytes=client.bytes,automatic_retries=sum(r['attempt']>0 for r in client.receipts))))
    (out/'receipt.json').write_bytes(canonical(receipt));(out/'strata.json').write_bytes(canonical([dict(scope=next(i for i,s in enumerate(json.loads((ROOT/'dashboard/geospatial.json').read_text())['scopes']) if s['source_week_start']==w['week']),start=w['start'],end=w['end'],kind=w['kind']) for w in windows]))
    print(dict(state=receipt['state'],records=receipt['records'],requests=client.requests,response_bytes=client.bytes))
