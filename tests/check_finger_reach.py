import sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'outputs'))
from gesture_features import features
from joint_features import FingerReachFeatures,ArticulatedFeatures

rng=np.random.default_rng(19)
points=rng.uniform(.1,.9,(21,3))
raw=features(points.ravel(),640,480)
t=FingerReachFeatures().fit([raw])
derived=t.transform([raw])[0]
assert derived.shape==(58,) and np.isfinite(derived).all()
assert np.allclose(derived[:39],ArticulatedFeatures().transform([raw])[0])
mirror=points.copy();mirror[:,0]=1-mirror[:,0]
assert np.allclose(derived,t.transform([features(mirror.ravel(),640,480)])[0])
assert np.allclose(derived,t.transform([features((points*1.7+.2).ravel(),640,480)])[0])
corrected=points.copy();corrected[:,1]*=480/640
for i,chain in enumerate([(1,2,3,4),(5,6,7,8),(9,10,11,12),(13,14,15,16),(17,18,19,20)]):
    length=sum(np.linalg.norm(corrected[b]-corrected[a]) for a,b in zip(chain,chain[1:]))
    expected=np.linalg.norm(corrected[chain[-1]]-corrected[chain[0]])/length
    assert np.isclose(derived[39+3*i],expected)
    assert 0<=derived[39+3*i]<=1+1e-10
# Equal bone lengths: a straight thumb reaches its full length; folded thumb does not.
straight=points.copy();straight[1:5]=[[.2,.3,.1],[.3,.3,.1],[.4,.3,.1],[.5,.3,.1]]
folded=straight.copy();folded[3:5]=[[.3,.4,.1],[.2,.4,.1]]
assert np.isclose(t.transform([features(straight.ravel(),640,480)])[0,39],1)
assert t.transform([features(folded.ravel(),640,480)])[0,39]<.5
assert np.isfinite(t.transform(np.zeros((2,210)))).all()
print('PASS: normalized reach matches 3D geometry, distinguishes folding, retains invariances and finite degenerate inputs')
