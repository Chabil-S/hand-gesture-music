import sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'outputs'))
from joint_features import ArticulatedFeatures
from gesture_features import features
points=np.random.default_rng(51).normal(size=(21,3))
result=ArticulatedFeatures().transform([features(points.ravel(),640,640)])[0]
for i,(a,b,c) in enumerate([(0,1,2),(0,5,6),(0,9,10),(0,13,14),(0,17,18)]):
    left=points[a]-points[b];right=points[c]-points[b]
    expected=np.dot(left,right)/(np.linalg.norm(left)*np.linalg.norm(right))
    np.testing.assert_allclose(result[23+i],expected,atol=1e-9)
mirrored=points.copy();mirrored[:,0]*=-1
np.testing.assert_allclose(result,ArticulatedFeatures().transform([features((mirrored*3+[1,4,6]).ravel(),640,640)])[0],atol=1e-9)
print('PASS: palm-joint cosines match independent 3D geometry and preserve scale/mirror/translation invariance')
