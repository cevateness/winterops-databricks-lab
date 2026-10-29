"""Offline SQL renderer; no credentials, networking or execution capability."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from winterops.unified_gold import load_selection


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--selection',type=Path,required=True)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--publication',action='store_true',help='Render create-only DDL, never execute it')
    args=parser.parse_args()
    plan=load_selection(args.selection)
    sections=[('COMPLETE SELECTION GUARD',plan.selection_guard()),('CANDIDATE RECONCILIATION',plan.reconcile())]
    sections += [('CREATE VIEW '+str(i+1),sql) for i,sql in enumerate(plan.publication())] if args.publication else [(p,plan.query(p)) for p in ('hourly','daily','weekly')]
    sections += list(plan.dashboard().items())
    text='-- OFFLINE RENDER ONLY. Native execution requires separate exact approval.\n\n'+'\n\n'.join('-- '+name+'\n'+sql+';' for name,sql in sections)+'\n'
    if args.output:args.output.write_text(text,encoding='utf-8')
    else:print(text,end='')


if __name__=='__main__':main()
