"""Joint angles and fingertip distances derived from the same palm-scaled landmarks.
No thresholds are hand-written: a classifier learns from train-only examples.
"""
import numpy as np
from sklearn.base import BaseEstimator,TransformerMixin

PAIRS=list(zip(*np.triu_indices(21,1)))
LOOKUP={tuple(map(int,pair)):i for i,pair in enumerate(PAIRS)}
JOINTS=[(1,2,3),(2,3,4),(5,6,7),(6,7,8),(9,10,11),(10,11,12),
        (13,14,15),(14,15,16),(17,18,19),(18,19,20)]
DISTANCES=[(0,4),(3,5),(4,5),(4,9),(4,13),(4,17),(4,8),(4,12),
           (5,8),(9,12),(13,16),(17,20),(8,12)]

class JointFeatures(TransformerMixin,BaseEstimator):
    def fit(self,X,y=None):
        self.n_features_in_=np.asarray(X).shape[1]
        return self
    def transform(self,X):
        X=np.asarray(X,dtype=float)
        if X.ndim!=2 or X.shape[1]!=210:raise ValueError('Expected 210 pairwise distances')
        def distance(a,b):return X[:,LOOKUP[tuple(sorted((a,b)))]]
        columns=[]
        for a,b,c in JOINTS:
            ab=distance(a,b);bc=distance(b,c);ac=distance(a,c)
            cosine=(ab*ab+bc*bc-ac*ac)/np.maximum(2*ab*bc,1e-10)
            columns.append(np.clip(cosine,-1,1))
        columns.extend(distance(a,b) for a,b in DISTANCES)
        return np.column_stack(columns)

class ArticulatedFeatures(JointFeatures):
    """Also describe finger folding at the palm and distances between all tips."""
    def transform(self,X):
        X=np.asarray(X,dtype=float)
        original=super().transform(X)
        def distance(a,b):return X[:,LOOKUP[tuple(sorted((a,b)))]]
        extra=[]
        for a,b,c in [(0,1,2),(0,5,6),(0,9,10),(0,13,14),(0,17,18)]:
            ab=distance(a,b);bc=distance(b,c);ac=distance(a,c)
            extra.append(np.clip((ab*ab+bc*bc-ac*ac)/np.maximum(2*ab*bc,1e-10),-1,1))
        tips=[4,8,12,16,20]
        pairs=[(0,t) for t in tips]+[(a,b) for i,a in enumerate(tips) for b in tips[i+1:]]
        for pair in pairs:
            if pair not in DISTANCES:extra.append(distance(*pair))
        return np.column_stack([original,*extra])


class FingerReachFeatures(ArticulatedFeatures):
    """Add bone-length-normalized reach and direction to describe finger folding.

    Keeps the articulated descriptors, so rejection of an extended thumb in a
    three-finger pose can still use its relation to the palm and other fingers.
    All ratios are geometric features, not hand-written command thresholds.
    """
    def transform(self,X):
        X=np.asarray(X,dtype=float)
        original=super().transform(X)
        def distance(a,b):return X[:,LOOKUP[tuple(sorted((a,b)))]]
        extra=[];lengths=[]
        chains=[(1,2,3,4),(5,6,7,8),(9,10,11,12),(13,14,15,16),(17,18,19,20)]
        for a,b,c,d in chains:
            length=distance(a,b)+distance(b,c)+distance(c,d)
            lengths.append(length)
            extra.append(distance(a,d)/np.maximum(length,1e-10))
            extra.append(distance(b,d)/np.maximum(distance(b,c)+distance(c,d),1e-10))
            palm=distance(0,a);reach=distance(a,d);wrist_tip=distance(0,d)
            extra.append(np.clip((palm*palm+reach*reach-wrist_tip*wrist_tip)
                                 /np.maximum(2*palm*reach,1e-10),-1,1))
        for i in range(1,5):
            extra.append(distance(4,chains[i][-1])/np.maximum(lengths[0]+lengths[i],1e-10))
        return np.column_stack([original,*extra])
