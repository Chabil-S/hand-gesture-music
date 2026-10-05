import json, hashlib, argparse
from pathlib import Path
from collections import Counter
import statistics

parser=argparse.ArgumentParser(description='Analyze saved paired live trials without changing models or music')
parser.add_argument('--base',type=Path,default=Path(__file__).resolve().parents[1]/'outputs/data/live_comparison')
parser.add_argument('--out',type=Path,required=True)
args=parser.parse_args()
base=args.base
report={'sessions':[],'caveat':'Instructed intent is not verified frame-level truth. Settled windows exclude first 1s and last .25s of each hold/release. Delay is from cue, includes human response.'}
for directory in sorted(base.iterdir()):
    if not directory.is_dir() or not (directory/'session.json').exists():continue
    manifest=json.loads((directory/'session.json').read_text(encoding='utf-8'))
    session={'id':directory.name,'complete':manifest['complete'],'trials':[]}
    for trial in manifest['trials']:
        file=directory/trial['file']
        rows=[json.loads(line) for line in file.read_text(encoding='utf-8').splitlines()]
        out={k:trial[k] for k in ('trial','hand','pose','complete','frame_count')}
        out['sha256']=hashlib.sha256(file.read_bytes()).hexdigest()
        out['max_gap']=max(b['elapsed']-a['elapsed'] for a,b in zip(rows,rows[1:]))
        out['branches']={}
        for key in manifest['models']:
            events=[{'elapsed':round(r['elapsed'],4),'phase':r['phase'],'cycle':r['cycle'],'action':r['branches'][key]['command']} for r in rows if r['branches'][key]['command']]
            assert len(events)==trial['command_counts'][key]
            stats={}
            for phase in ('hold','release'):
                selected=[]
                for r in rows:
                    if r['phase']!=phase:continue
                    start=(3 if r['cycle']==1 else 10) if phase=='hold' else (7 if r['cycle']==1 else 14)
                    end=start+(4 if phase=='hold' else 3)
                    if start+1<=r['elapsed']<end-.25:selected.append(r)
                expected=trial['pose'] if phase=='hold' and trial['pose'] in ('toggle','next','previous') else 'neutral'
                labels=Counter(r['branches'][key]['label'] for r in selected)
                scores=[r['branches'][key]['score'] for r in selected]
                stats[phase]={'n':len(selected),'expected_intent':expected,'labels':dict(labels),
                    'matching_intent':labels[expected],'uncertain':labels['uncertain'],
                    'score_median':round(statistics.median(scores),4) if scores else None}
            out['branches'][key]={'events':events,'settled':stats}
        session['trials'].append(out)
    report['sessions'].append(session)
outpath=args.out
outpath.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
for session in report['sessions']:
    print('SESSION',session['id'],'complete',session['complete'])
    for trial in session['trials']:
        print('TRIAL',trial['trial'],trial['hand'],trial['pose'])
        for key,r in trial['branches'].items():
            print(key,'events',r['events'],'hold',r['settled']['hold'],'release',r['settled']['release'])
print(outpath)
