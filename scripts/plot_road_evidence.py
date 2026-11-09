"""Optional static study figure from actual public aggregates (matplotlib)."""
import argparse
from collections import Counter
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=ROOT/'dashboard/road_evidence.svg');a=p.parse_args()
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    r=json.loads((ROOT/'docs/ROAD_EVIDENCE_V31_RESULTS.json').read_text());counts=Counter()
    for x in r['scenarios']:counts[x['scenario']]+=x['passage_candidates']
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'svg.fonttype':'none'})
    fig,axes=plt.subplots(1,2,figsize=(11.5,4.5),layout='constrained');fig.patch.set_facecolor('#f2f6f5')
    labels=['Nearest-road control','Heading supported','Bounded topology'];values=[counts[s] for s in ['nearest','heading','topology']]
    axes[0].barh(labels,values,color=['#a5bbc0','#5c919d','#216879']);axes[0].invert_yaxis();axes[0].set_xlim(0,44000)
    for i,n in enumerate(values):axes[0].text(n+500,i,f'{n:,}',va='center')
    axes[0].set_title('Candidate fragments depend on correspondence rules',loc='left',fontweight='bold',fontsize=10)
    axes[0].set_xlabel('Fragment count · seven weeks · not complete road visits')
    groups=['January','February'];colors=['#216879','#dd5b30'];x=[0,1]
    for offset,zone,color in [(-.18,'America/Toronto',colors[0]),(.18,'UTC',colors[1])]:
        vals=[next(z['pearson_r'] for z in r['weather']['relationships'] if z['reference_id']=='windsor_centre' and z['timezone_hypothesis']==zone and z['processing_key']==c and z['variable']=='snowfall_activity_hour_cm') for c in ['january','february']]
        bars=axes[1].bar([v+offset for v in x],vals,width=.33,color=color,label=zone)
        for b,v in zip(bars,vals):axes[1].text(b.get_x()+b.get_width()/2,v+.015,f'{v:.3f}',ha='center')
    axes[1].set_xticks(x,['January (325 hours)','February (122 hours)']);axes[1].set_ylim(0,.7);axes[1].set_ylabel('Pearson r · occupied source-hour means')
    axes[1].set_title('Snowfall association is clock- and period-sensitive',loc='left',fontweight='bold',fontsize=10);axes[1].legend(frameon=False,loc='upper right')
    for ax in axes:
        ax.spines[['top','right']].set_visible(False);ax.set_facecolor('#f2f6f5')
    fig.suptitle('WinterOps V3.1 · Actual descriptive evidence, January 5–February 22, 2026',fontsize=13,fontweight='bold')
    fig.savefig(a.output,metadata={'Date':None,'Description':'Actual seven-week CSV analytics and fixed-reference ERA5-requested reanalysis. No independent service labels or causal interpretation.'});plt.close(fig)
