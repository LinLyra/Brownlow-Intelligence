from __future__ import annotations
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.ensemble import HistGradientBoostingRegressor

class LGBMWrapper:
    def __init__(self, seed=42, objective="regression"):
        from lightgbm import LGBMRegressor
        self.model=LGBMRegressor(n_estimators=1200, learning_rate=.025, num_leaves=31, max_depth=-1,
            subsample=.85, colsample_bytree=.85, reg_lambda=2.0, reg_alpha=.2, random_state=seed, n_jobs=-1)
    def fit(self,X,y,cat_cols=None):
        X=X.copy()
        for c in (cat_cols or []): X[c]=X[c].astype("category")
        self.cat_cols=cat_cols or []; self.model.fit(X,y); return self
    def predict(self,X):
        X=X.copy()
        for c in self.cat_cols: X[c]=X[c].astype("category")
        return self.model.predict(X)

class CatBoostWrapper:
    def __init__(self, seed=42):
        from catboost import CatBoostRegressor
        self.model=CatBoostRegressor(iterations=1200, depth=7, learning_rate=.035, loss_function="RMSE",
            random_seed=seed, verbose=False, l2_leaf_reg=5, random_strength=.5)
    def fit(self,X,y,cat_cols=None,sample_weight=None):
        X=X.copy(); self.cat_cols=cat_cols or []
        for c in self.cat_cols: X[c]=X[c].fillna("__NA__").astype(str)
        # sample_weight is optional; omitting it preserves historical V2.1 behaviour.
        if sample_weight is None:
            self.model.fit(X,y,cat_features=self.cat_cols)
        else:
            self.model.fit(X,y,cat_features=self.cat_cols,sample_weight=sample_weight)
        return self
    def predict(self,X):
        X=X.copy()
        for c in self.cat_cols: X[c]=X[c].fillna("__NA__").astype(str)
        return self.model.predict(X)

class TwoStageLGBM:
    """P(vote>0) * E[vote|vote>0]. Must earn its place by OOF RMSE; not assumed superior."""
    def __init__(self, seed=42):
        from lightgbm import LGBMClassifier, LGBMRegressor
        self.rec=LGBMClassifier(n_estimators=900, learning_rate=.025, num_leaves=31, class_weight="balanced",
            reg_lambda=2, random_state=seed, n_jobs=-1)
        self.intensity=LGBMRegressor(n_estimators=700, learning_rate=.025, num_leaves=15, reg_lambda=3,
            random_state=seed+1, n_jobs=-1)
    def _prep(self,X):
        X=X.copy()
        for c in self.cat_cols: X[c]=X[c].astype("category")
        return X
    def fit(self,X,y,cat_cols=None):
        self.cat_cols=cat_cols or []; X=self._prep(X)
        poll=(np.asarray(y)>0).astype(int)
        self.rec.fit(X,poll)
        self.intensity.fit(X.loc[poll==1], np.asarray(y)[poll==1])
        return self
    def predict(self,X):
        X=self._prep(X)
        return self.rec.predict_proba(X)[:,1] * self.intensity.predict(X)
