import sys, json
from pathlib import Path
import numpy as np
import joblib
base=Path(__file__).resolve().parents[1]/'outputs'
sys.path.insert(0,str(base))
from live_comparison import Branch, ComparisonApp, phase_at

directory=base/'models/20261004_171415'
model=joblib.load(directory/'gesture_model.joblib')
config=json.loads((directory/'selection_frozen.json').read_text())
import csv
p=next(e for e in config['inputs'] if 'toggle' in e['file'])
with (base/p['file']).open(encoding='utf-8') as file:row=next(csv.DictReader(file))
coords=[float(row[f'{axis}{i}']) for i in range(21) for axis in 'xyz']
branch=Branch(model,.6,config)
def frame(t,hands):return {'t':t,'w':int(row['width']),'h':int(row['height']),'hands':hands}
hand={'coords':coords,'handedness':'Left','handedness_score':1.}
branch.update(frame(0,[]));branch.update(frame(.2,[]));assert not branch.update(frame(.4,[]))['latched']
events=[]
for t in np.arange(.5,2.,.1):
    result=branch.update(frame(float(t),[hand]))
    if result['command']:events.append(result['command'])
assert events==['toggle'],events
branch.update(frame(2.1,[]));branch.update(frame(2.3,[]));branch.update(frame(2.5,[]))
for t in np.arange(2.6,3.6,.1):
    result=branch.update(frame(float(t),[hand]))
    if result['command']:events.append(result['command'])
assert events==['toggle','toggle'],events
assert [phase_at(t) for t in (0,3,7,10,14,17)]==[('prepare',None),('hold',1),('release',1),('hold',2),('release',2),('done',None)]
before=(base/'latest_model.json').read_bytes()
app=ComparisonApp();app.root.withdraw();app.root.update();app.close()
assert (base/'latest_model.json').read_bytes()==before
print('PASS: paired branches, hold/release, phase boundaries, real-model UI initialization, active pointer unchanged')
