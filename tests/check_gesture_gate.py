import sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'outputs'))
from gesture_features import features,GestureGate

rng=np.random.default_rng(42)
points=rng.normal(size=(21,3))
original=features(points.reshape(-1),640,480)
reflected=points.copy(); reflected[:,0]*=-1
assert np.allclose(original,features(reflected.reshape(-1),640,480))
assert np.allclose(original,features((points*2+3).reshape(-1),640,480))
gate=GestureGate()
def feed(label,start,end):
    result=[]
    for t in np.arange(start,end,0.05):
        command=gate.update(label,float(t))
        if command: result.append(command)
    return result
assert feed('toggle',0,3)==['toggle']
assert feed('next',3,4)==[]
assert feed('uncertain',4,5)==[]
assert feed('next',5,6)==[]
assert feed('no_hand',6,6.6)==[]
assert feed('next',6.6,8)==['next']
assert feed('neutral',8,8.6)==[]
assert feed('previous',8.6,10)==['previous']
gate.reset()
assert feed('toggle',0,0.3)==[]
assert feed('toggle',1,1.3)==[] # stale frame gap must not confirm
assert feed('uncertain',1.3,1.6)==[]
assert feed('toggle',1.6,1.9)==[]
print('PASS: reflection/scale/translation invariance, hold, release, no repeat, uncertainty, frame gaps')
