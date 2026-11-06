"""Relocate the private replay package outside Git; no downloads or overwrites.

The package contains relative CSV bytes and original receipt metadata. Re-adopt
each CSV through LocalStager to bind its local path on Windows/Linux while
preserving its exact source identity and hash. No native COMPLETE claim is made.
"""
import argparse
import json
from pathlib import Path
import shutil
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from winterops.sources import LocalStager,SourceVersion,outside_git


def restore(package,output):
    package,output=map(outside_git,(package,output))
    if output.exists():raise ValueError('V3_RESTORE_TARGET_EXISTS')
    output.mkdir(parents=True);stager=LocalStager(output/'csv')
    for sidecar in sorted((package/'inputs/csv/raw').glob('*/*/*.version.json')):
        old=SourceVersion.from_dict(json.loads(sidecar.read_text(encoding='utf-8')))
        # Sidecars are NAME.version.json, while raw bytes are NAME.csv.
        source=sidecar.parent/old.source.source_file_name
        new,_=stager.adopt(old.source,source)
        if new.source_file_sha256!=old.source_file_sha256:raise ValueError('V3_RESTORE_SOURCE_HASH')
    inputs=package/'inputs'
    for p in inputs.iterdir():
        if p.name=='csv':continue
        target=output/p.name
        if p.is_dir():shutil.copytree(p,target)
        else:shutil.copyfile(p,target)
    return dict(status='RESTORED_PRIVATE_INPUTS_NO_NETWORK',csv_versions=len(list((output/'csv/raw').glob('*/*/*.version.json'))))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--package',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    a=p.parse_args();print(json.dumps(restore(a.package,a.output)))
