"""Retain full hand distances while adding learned joint-angle features."""
import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin
from joint_features import JointFeatures

class CombinedFeatures(TransformerMixin, BaseEstimator):
    def fit(self,X,y=None):
        self.n_features_in_=np.asarray(X).shape[1]
        return self
    def transform(self,X):
        X=np.asarray(X,dtype=float)
        return np.column_stack((X,JointFeatures().transform(X)))
