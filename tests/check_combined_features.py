import sys, io
from pathlib import Path
import numpy as np
import joblib
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'outputs'))
from combined_features import CombinedFeatures
from gesture_features import features

points=np.random.default_rng(42).normal(size=(21,3))
before=features(points.ravel(),640,640)
mirrored=points.copy();mirrored[:,0]*=-1
after=features((mirrored*2+[3,4,5]).ravel(),640,640)
transform=CombinedFeatures()
np.testing.assert_allclose(transform.transform([before]),transform.transform([after]),atol=1e-9)
assert transform.transform([before]).shape==(1,233)
try:transform.transform([[0.]*20])
except ValueError:pass
else:raise AssertionError('Invalid input accepted')
data=np.load(Path(__file__).resolve().parents[1]/'outputs/models/20261004_221121/derived_features.npz')
indices=np.concatenate([np.where((data['split']=='train')&(data['y']==label))[0][:15] for label in ('neutral','toggle','next','previous')])
model=make_pipeline(CombinedFeatures(),StandardScaler(),LogisticRegression(max_iter=1000))
model.fit(data['X'][indices],data['y'][indices])
blob=io.BytesIO();joblib.dump(model,blob);blob.seek(0)
np.testing.assert_allclose(model.predict_proba(data['X'][indices]),joblib.load(blob).predict_proba(data['X'][indices]))
print('PASS: mirror/scale/translation invariance, invalid landmarks rejected, trained combined pipeline roundtrip')
