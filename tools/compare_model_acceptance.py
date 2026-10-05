"""Read-only model comparison on previously collected data; never activates a model."""
import sys, json, csv, hashlib, argparse
from pathlib import Path
import numpy as np
import joblib

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--base', type=Path, default=Path(__file__).resolve().parents[1]/'outputs')
parser.add_argument('--out', type=Path, required=True, help='Local diagnostic JSON; do not commit per-frame data')
args = parser.parse_args()
BASE = args.base.resolve()
sys.path.insert(0, str(BASE))
from gesture_features import GestureGate

old_dir = BASE/'models/20261004_171415'
new_dir = BASE/'models/20261004_221121'
data = np.load(new_dir/'derived_features.npz')
X, y, hands, splits, kinds = [data[k] for k in ('X','y','hand','split','kind')]
config = json.loads((new_dir/'selection_frozen.json').read_text(encoding='utf-8'))
rows = []
for entry in config['inputs']:
    p = BASE/entry['file']
    assert hashlib.sha256(p.read_bytes()).hexdigest() == entry['sha256']
    with p.open(encoding='utf-8', newline='') as f:
        for row in csv.DictReader(f):
            rows.append((p.parent.name+':'+row['clip_id'], float(row['elapsed_seconds'])))
assert len(rows) == len(X)
groups = np.array([r[0] for r in rows]); times = np.array([r[1] for r in rows])
report = {'scope':'diagnostic replay of already collected/evaluated data, not fresh live evaluation', 'variants':{}}
for name, directory, threshold in [('old_060',old_dir,.6),('new_060',new_dir,.6),('new_070',new_dir,.7),('new_080',new_dir,.8)]:
    model = joblib.load(directory/'gesture_model.joblib')
    probabilities = model.predict_proba(X)
    predicted = model.classes_[probabilities.argmax(axis=1)]
    scores = probabilities.max(axis=1)
    runtime = np.where(scores>=threshold,predicted,'uncertain')
    result = {'threshold':threshold, 'frames':[], 'clips':[]}
    for split in ('validation','test'):
        for hand in ('left','right'):
            for label in ('toggle','next','previous','neutral','three_finger'):
                mask = (splits==split)&(hands==hand)
                mask &= (kinds=='three_finger_negative') if label=='three_finger' else ((kinds=='base_four_classes')&(y==label))
                if not mask.any(): continue
                result['frames'].append({'split':split,'hand':hand,'actual':label,'n':int(mask.sum()),
                    'correct_raw':int(np.sum(predicted[mask]==y[mask])),
                    'correct_accepted':int(np.sum(runtime[mask]==y[mask])),
                    'uncertain':int(np.sum(runtime[mask]=='uncertain')),
                    'wrong_accepted':int(np.sum((runtime[mask]!='uncertain')&(runtime[mask]!=y[mask]))),
                    'correct_score_quantiles':np.quantile(scores[mask & (predicted==y)],[0,.1,.5,.9,1]).tolist() if np.any(mask & (predicted==y)) else []})
    for group in dict.fromkeys(groups.tolist()):
        indexes = np.where((groups==group)&(splits!='train'))[0]
        if not len(indexes): continue
        indexes = indexes[np.argsort(times[indexes])]
        first=indexes[0]; gate=GestureGate(); commands=[]
        for i in indexes:
            command=gate.update(str(runtime[i]),float(times[i]))
            if command: commands.append({'action':command,'seconds_from_first_frame':round(float(times[i]-times[first]),4)})
        result['clips'].append({'group':group,'split':str(splits[first]),'hand':str(hands[first]),'kind':str(kinds[first]),'actual':str(y[first]),'commands':commands})
    report['variants'][name]=result
out=args.out.resolve()
out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
for name, result in report['variants'].items():
    print(name)
    for label in ('toggle','next','previous','neutral','three_finger'):
        rs=[r for r in result['frames'] if r['actual']==label]
        print(label, {k:sum(r[k] for r in rs) for k in ('n','correct_raw','correct_accepted','uncertain','wrong_accepted')})
    command_clips=[r for r in result['clips'] if r['actual']!='neutral']
    negative=[r for r in result['clips'] if r['kind']=='three_finger_negative']
    print('command_replay', [(r['split'],r['hand'],r['actual'],r['commands']) for r in command_clips])
    print('three_finger_commands',sum(len(r['commands']) for r in negative))
print('report',out)
