"""Prepare private local approval material. Does not connect to Databricks."""
import argparse,hashlib,json,os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from winterops.sources import outside_git
from winterops.threeweek_plan import prepare


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(os.environ.get('LOCALAPPDATA',Path.home()))/'WinterOps/foundation_v2')
    parser.add_argument('--selection',type=Path,default=Path('docs/THREE_WEEK_SELECTION.json'))
    parser.add_argument('--prior-native',type=Path,default=Path('docs/DATA_FOUNDATION_V2_NATIVE_RESULTS.json'))
    parser.add_argument('--legacy-summary',type=Path,default=Path('data/fixtures/windsor_week_2026_01_12_18_summary.json'))
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();output=outside_git(args.output)
    data=prepare(args.root,args.selection,args.prior_native,args.legacy_summary)
    text=json.dumps(data,indent=2)+'\n';output.parent.mkdir(parents=True,exist_ok=True)
    # Never overwrite reviewed approval material silently.
    if output.exists() and output.read_text(encoding='utf-8')!=text:raise ValueError('Existing plan differs; use a new reviewed output path')
    if not output.exists():
        with output.open('x',encoding='utf-8',newline='\n') as handle:handle.write(text)
    print(json.dumps(dict(status=data['status'],statements=data['sql_statements'],uploads=len(data['uploads']),upload_bytes=sum(u['bytes'] for u in data['uploads']),plan_sha256=hashlib.sha256(output.read_bytes()).hexdigest())))


if __name__=='__main__':main()
