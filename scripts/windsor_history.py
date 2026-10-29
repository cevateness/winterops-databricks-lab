"""Discover/stage/process Windsor weeks locally. Never authenticates to Databricks."""
import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import sys
from urllib.request import build_opener

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from winterops.foundation import QualityPolicy, processing_key
from winterops.ingestion import LocalManifest, export_bronze, process_local
from winterops.sources import CATALOGUE_URL, LocalStager, NoRedirect, WeeklySource, discover_weekly
from winterops.spark_ingestion import DevelopmentTargets, silver_sql, sql_version_plan


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(os.environ.get('LOCALAPPDATA',str(Path.home()/'.local/share')))/'WinterOps/foundation_v2')
    sub=parser.add_subparsers(dest='command',required=True)
    discover=sub.add_parser('discover');discover.add_argument('--catalogue-file',type=Path)
    stage=sub.add_parser('stage');stage.add_argument('--url',required=True);stage.add_argument('--file',type=Path)
    for command in ('process','plan'):
        child=sub.add_parser(command)
        child.add_argument('--filename',required=True);child.add_argument('--sha256',required=True)
        child.add_argument('--policy',type=Path)
        if command=='process':
            child.add_argument('--repair',action='store_true')
            child.add_argument('--export-bronze',action='store_true')
            child.add_argument('--artifact-compression',choices=('none','gzip'),default='none')
        else:
            child.add_argument('--artifact-volume-path')
            child.add_argument('--artifact-sha256')
    sub.add_parser('report')
    args=parser.parse_args()
    manifest=None
    try:
        if args.command=='discover':
            if args.catalogue_file:
                html=args.catalogue_file.read_text(encoding='utf-8')
            else:
                with build_opener(NoRedirect()).open(CATALOGUE_URL,timeout=30) as response:
                    data=response.read(1024*1024+1)
                    if len(data)>1024*1024: raise ValueError('CATALOGUE_TOO_LARGE')
                    html=data.decode('utf-8')
            print(json.dumps([asdict(s) for s in discover_weekly(html)],indent=2));return
        stager=LocalStager(args.root)
        manifest=LocalManifest(args.root/'manifest.sqlite')
        if args.command=='stage':
            source=WeeklySource.from_url(args.url)
            version,action=stager.adopt(source,args.file) if args.file else stager.download(source)
            with manifest.writer_lock(): version,discovery=manifest.register(version)
            print(json.dumps(dict(action=action,discovery=discovery,version=version.to_dict()),indent=2));return
        if args.command=='report':
            print(json.dumps([dict(processing_key=row[0],status=row[1],last_successful_stage=row[2],attempts=row[3],error_code=row[4],report=json.loads(row[5]) if row[5] else None)
                for row in manifest.db.execute('SELECT processing_key,status,last_successful_stage,attempts,error_code,report_json FROM runs ORDER BY processing_key')],indent=2));return
        version=manifest.select_version(args.filename,args.sha256)
        policy=QualityPolicy(**json.loads(args.policy.read_text())) if args.policy else QualityPolicy()
        if args.command=='plan':
            targets=DevelopmentTargets()
            print('-- REVIEW ONLY. Separate bounded development-table approval required.\n')
            for statement in targets.creation_sql(): print(statement+';\n')
            if args.artifact_volume_path or args.artifact_sha256:
                if not args.artifact_volume_path or not args.artifact_sha256:
                    raise ValueError('Both exact artifact parameters are required')
                run=manifest.run(processing_key(version,policy))
                if not run or run['status']!='COMPLETE': raise ValueError('Require locally reconciled source version')
                for label,statement in sql_version_plan(version,args.artifact_volume_path,args.artifact_sha256,run['bronze_rows'],targets=targets,policy=policy).items():
                    print('-- '+label+'\n'+statement+';\n')
            else:
                print(silver_sql(targets,version,policy)+';')
            return
        result=process_local(manifest,version,policy,repair=args.repair)
        if args.export_bronze:
            result['artifact']=export_bronze(manifest,version,args.root/'artifacts',
                compression=None if args.artifact_compression=='none' else args.artifact_compression)
        print(json.dumps(result,indent=2))
    except Exception as error:
        # Do not echo exception text that might include source values or URLs.
        print(json.dumps(dict(status='FAILED',error_type=type(error).__name__,details='Inspect local manifest and staged bytes; no automatic retry')),file=sys.stderr)
        return 2
    finally:
        if manifest: manifest.close()
    return 0


if __name__=='__main__':
    raise SystemExit(main())
