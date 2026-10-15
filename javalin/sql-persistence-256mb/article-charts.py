#!/usr/bin/env python3
"""Generate publication charts from curated data. Requires matplotlib."""
import argparse,csv,json,math
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
out=p.parse_args().output;out.mkdir(parents=True,exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.facecolor':'#111914','figure.facecolor':'#0b100d','text.color':'#e4eee7','axes.labelcolor':'#c6d4ca','xtick.color':'#c6d4ca','ytick.color':'#c6d4ca','axes.edgecolor':'#526459','svg.fonttype':'path','svg.hashsalt':'persistence-256mb'})
runs=[('Jdbi','run-20261008T235523Z-javalin-jdbi3','#66d58b'),('MyBatis','run-20261009T011153Z-javalin-mybatis','#6caaff'),('jOOQ (original)','run-20261009T015612Z-javalin-jooq','#efb864')]
fig,axs=plt.subplots(2,1,figsize=(9,6.8),sharex=True,layout='constrained')
for name,run,color in runs:
 phases={p['phase']:p['epoch'] for p in json.loads((ROOT/'results'/run/'phases.json').read_text())}
 rows=[{k:float(v) for k,v in r.items()} for r in csv.DictReader((ROOT/'results'/run/'guest/os.csv').open())]
 rows=[r for r in rows if phases['idle']<=r['epoch']<phases['measurement-cutoff']]
 x=[(r['epoch']-phases['workload'])/60 for r in rows]
 axs[0].plot(x,[r['java_rss_kib']/1024 for r in rows],label=name,color=color,lw=2)
 axs[1].plot(x,[r['swap_used_kib']/1024 for r in rows],label=name,color=color,lw=2)
axs[0].set_title('Similar resident memory, different swap occupancy',loc='left',weight='bold',pad=16)
axs[0].set_ylabel('Java RSS (MiB)');axs[0].set_ylim(0,140)
axs[1].set_ylabel('Guest swap used (MiB)');axs[1].set_ylim(0,85)
for ax in axs:
 ax.axvspan(0,5,color='#527796',alpha=.16);ax.axvline(0,color='#7c9183',lw=.8,ls='--');ax.axvline(5,color='#7c9183',lw=.8,ls='--');ax.grid(axis='y',alpha=.18);ax.set_xlim(-3,7)
axs[0].legend(frameon=False,labelcolor='#e4eee7',ncol=3,loc='lower right',fontsize=10)
for x,name in [(-1.5,'Idle'),(2.5,'Workload'),(6,'Recovery')]:axs[1].text(x,79,name,ha='center',color='#c6d4ca',fontsize=10)
axs[1].set_xlabel('Minutes relative to each run’s workload start')
fig.savefig(out/'memory-pressure.svg',metadata={'Date':None});plt.close(fig)
fig,ax=plt.subplots(figsize=(9,4.2),layout='constrained')
for name,run,color in runs:
 events=[json.loads(line) for line in (ROOT/'results'/run/'http.jsonl').read_text().splitlines()]
 values=[]
 for minute in range(5):
  latencies=sorted(e['latency_ms'] for e in events if minute*300<=e['index']<(minute+1)*300)
  assert len(latencies)==300
  values.append(latencies[math.ceil(len(latencies)*.95)-1])
 ax.plot(range(1,6),values,color=color,marker='o',lw=2,label=name)
ax.set_title('External HTTP p95 by workload minute',loc='left',weight='bold',pad=16)
ax.set_xlabel('Workload minute (300 scheduled requests)');ax.set_ylabel('HTTP p95 (ms)');ax.set_xticks(range(1,6));ax.set_ylim(0,20);ax.grid(axis='y',alpha=.18);ax.legend(frameon=False,labelcolor='#e4eee7')
fig.savefig(out/'request-latency.svg',metadata={'Date':None});plt.close(fig)
print('Generated memory-pressure.svg and request-latency.svg from the three archived runs')
