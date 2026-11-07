"""Replay the bounded V3.1 portal comparison. No network; private inputs only.

Never append overlap, publish identifiers, or imply independent sensor evidence.
"""
import argparse
from collections import Counter
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from run_evidence_investigation import source_rows,read,ROOT
from winterops.arcgis_source import windsor_observation,canonical
from winterops.sources import outside_git
from winterops.source_overlap import compare,key
from winterops.operational_diagnostics import timestamp_events
from winterops.sensor_investigation import conflict_review
from winterops.weather import require


def review(inputs,source_root):
    source_root=outside_git(source_root);receipt=read(source_root/'receipt.json')
    snapshot=read(source_root/'telemetry'/(receipt['snapshot_id']+'.snapshot.json'))
    from winterops.arcgis_source import digest
    require(digest(snapshot)==receipt['snapshot_id'],'SOURCE_REVIEW_SNAPSHOT_ID')
    require(receipt['state']=='COMPLETE','SOURCE_REVIEW_INCOMPLETE')
    require(snapshot['schema']['date_reference']==dict(respectsDaylightSaving=True,timeZone='Eastern Standard Time'),'SOURCE_REVIEW_DATE_CONTRACT')
    require(snapshot['schema']['dates_unknown'] is False,'SOURCE_REVIEW_UNKNOWN_CLOCK')
    portal=[windsor_observation(f,receipt['snapshot_id'],i+1) for i,f in enumerate(snapshot['features'])]
    windows=read(source_root/'strata.json');results=[]
    require(len(portal)==receipt['records']==7036,'SOURCE_REVIEW_COUNT')
    for si,scope,rows in source_rows(inputs,read(ROOT/'dashboard/geospatial.json')):
        for w in windows:
            if w['scope']!=si:continue
            a=[r for r in rows if w['start']<=r['event_time_unzoned']<w['end']]
            b=[r for r in portal if w['start']<=r['event_time_unzoned']<w['end']]
            result=compare(a,b);ac,bc=Counter(key(r) for r in a),Counter(key(r) for r in b)
            # No per-identifier output, even when only one record is in a stratum.
            conflicts,_=conflict_review(timestamp_events(a))
            states={}
            for r in b:states.setdefault((r['truck_id'],r['event_time_unzoned']),set()).add((r['plow_active'],r['spreader_active']))
            result.pop('csv_hour_counts');result.pop('portal_hour_counts')
            results.append(dict(week=scope.source.covered_start,start=w['start'],end=w['end'],kind=w['kind'],
                                **result,csv_conflicting_timestamp_groups=conflicts['conflicting_groups'],
                                portal_conflicting_timestamp_groups=sum(len(v)>1 for v in states.values()),
                                portal_payload_multiplicity_histogram=dict(Counter(bc.values())),
                                portal_exactly_twice_csv_multiset=bc==Counter({k:n*2 for k,n in ac.items()}),
                                additional_existing_payload_copies=sum((bc-ac)[k] for k in ac)))
    require(sum(r['portal_records'] for r in results)==len(portal),'SOURCE_REVIEW_WINDOW_RECONCILIATION')
    meta=read(source_root/'metadata.json');ledger=read(source_root/'ledger.json')
    # PublicClient has .json receipts; use the exact accepted snapshot receipt
    # and separately stored ledger total, not estimated per-page counts.
    return dict(status='EXECUTED_PINNED_SNAPSHOT_OFFLINE_REPLAY',snapshot_id=receipt['snapshot_id'],
                schema_sha256=receipt['schema_sha256'],comparison_scope='SEVEN_STRATA_SIX_SOURCE_WEEKS_NOT_FULL_HISTORY_EQUALITY',
                csv_records=sum(r['csv_records'] for r in results),portal_records=len(portal),
                exact_matches=sum(r['exact_matches'] for r in results),
                extra_portal_records=sum(r['portal_unmatched'] for r in results),samples=results,
                retrieval=dict(total_http_requests=ledger['requests'],total_response_bytes=ledger['response_bytes'],automatic_retries=ledger['automatic_retries'],
                               telemetry_snapshot_requests=len(receipt['response_receipts']),
                               telemetry_snapshot_bytes=sum(r['bytes'] for r in receipt['response_receipts'])),
                roads=dict(current_layer=23,geometry_count_previously_verified=6312,
                           nonnull_street_name_count=read(source_root/'road_nonnull_count.json')['count'],
                           advertised_fields=[f['name'] for f in meta['roads']['fields']],
                           metadata_does_not_repair_null_attributes=True,legacy_attribute_join='EXACT_COMPKEY_ONLY_NEVER_PROXIMITY'),
                request_fields=[f['name'] for f in meta['requests']['fields']],
                request_fulfillment_fields_found=False,append_decision='DO_NOT_APPEND_ANY_OVERLAP',
                independent_corroboration=False)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--inputs',required=True,type=Path);p.add_argument('--source-root',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    a=p.parse_args();out=review(a.inputs,a.source_root);a.output.write_bytes(canonical(out)+b'\n');print({k:out[k] for k in ('csv_records','portal_records','exact_matches','extra_portal_records')})
