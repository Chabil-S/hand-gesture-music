from pathlib import Path
import sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'outputs'))
from gesture_features import features
from joint_features import JointFeatures,JOINTS

rng=np.random.default_rng(42)
points=rng.uniform(.1,.9,(21,3))
raw=features(points.ravel(),640,480)
transformer=JointFeatures().fit([raw])
derived=transformer.transform([raw])[0]
corrected=points.copy();corrected[:,1]*=480/640
expected=[]
for a,b,c in JOINTS:
    u=corrected[a]-corrected[b];v=corrected[c]-corrected[b]
    expected.append(np.dot(u,v)/(np.linalg.norm(u)*np.linalg.norm(v)))
assert np.allclose(derived[:len(JOINTS)],expected)
assert derived.shape==(23,) and np.isfinite(derived).all()
mirrored=points.copy();mirrored[:,0]=1-mirrored[:,0]
assert np.allclose(derived,transformer.transform([features(mirrored.ravel(),640,480)])[0])
assert np.allclose(derived,transformer.transform([features((points*1.7+.2).ravel(),640,480)])[0])
print('PASS: joint angles match 3D dot products; descriptors retain mirror/scale/translation invariance')
