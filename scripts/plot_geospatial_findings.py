"""Optional static report figure. pip install matplotlib; consumes public results."""
import json
from pathlib import Path
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
d=json.loads((ROOT/'docs/GEOSPATIAL_V3_RESULTS.json').read_text(encoding='utf-8'))
labels=[s['week'][5:] for s in d['sensors']]
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none','svg.hashsalt':'winterops-geospatial-v3'})
fig,axes=plt.subplots(1,2,figsize=(11,4.1),layout='constrained')
colors=['#8bb3bc','#216879','#dd714c']
for limit,color in zip([15,30,60],colors):
    axes[0].plot(labels,[100*r['within_road_metres'][str(limit)]/r['observations'] for r in d['sensors']],marker='o',label=f'Within {limit}m',color=color)
axes[0].set(title='Candidate road proximity is week-sensitive',ylabel='% of VALID observations',xlabel='Source week start · 2026',ylim=(0,100));axes[0].legend(frameon=False,ncol=3,fontsize=8,loc='lower center')
for gap,color in zip([15,30,60],colors):
    axes[1].plot(labels,[next(e['observed_episodes'] for e in d['episodes'] if e['processing_key']==s['processing_key'] and e['gap_minutes']==gap) for s in d['sensors']],marker='o',label=f'{gap}m gap',color=color)
axes[1].set(title='Observed episodes depend on the recording-gap rule',ylabel='Heuristic episode count',xlabel='Source week start · 2026');axes[1].legend(frameon=False,ncol=3,fontsize=8)
for ax in axes:ax.grid(axis='y',alpha=.16);ax.tick_params(axis='x',rotation=30)
fig.suptitle('WinterOps V3 · actual seven-week telemetry diagnostics',fontweight='bold',fontsize=13)
fig.savefig(ROOT/'docs/images/geospatial-v3-quality.svg',metadata={'Date':None})

p=ROOT/'docs/images/geospatial-v3-quality.svg'
p.write_text('\n'.join(line.rstrip() for line in p.read_text(encoding='utf-8').splitlines())+'\n',encoding='utf-8')
