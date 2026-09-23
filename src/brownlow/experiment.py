from __future__ import annotations
import json, os
import numpy as np
import pandas as pd
from .allocation import allocate_frame, assert_feasible_predictions
from .metrics import diagnostics
from .models import LGBMWrapper, CatBoostWrapper, TwoStageLGBM

MODELS={"lightgbm":LGBMWrapper,"catboost":CatBoostWrapper,"two_stage":TwoStageLGBM}

def temporal_cv(df, features, cats, val_years=(2022,2023,2024,2025), seed=42, allocation="capped_simplex"):
    rows=[]; oofs=[]
    for name, cls in MODELS.items():
        for yr in val_years:
            tr=df[df.season < yr]; va=df[df.season == yr].copy()
            model=cls(seed=seed)
            model.fit(tr[features], tr.brownlow_votes, cat_cols=cats)
            va["raw_prediction"]=model.predict(va[features])
            va=allocate_frame(va,"raw_prediction",allocation)
            d=diagnostics(va)
            rows.append({"model":name,"val_season":yr,**d})
            oofs.append(va[["season","match_id","player_id","brownlow_votes"]].assign(model=name,prediction=va.prediction.values))
    return pd.DataFrame(rows), pd.concat(oofs,ignore_index=True)

def _coaches_zero_signal_matches(va: pd.DataFrame):
    """Return match_id -> reason for missing or zero coaches_votes signal."""
    reasons = {}
    for mid, g in va.groupby("match_id"):
        c = g["coaches_votes"]
        if c.isna().all():
            reasons[mid] = "coaches_votes all missing"
        elif float(c.fillna(0).sum()) <= 0:
            reasons[mid] = "coaches_votes sum is zero"
    return reasons

def allocate_coaches_direct(va: pd.DataFrame, allocation: str = "capped_simplex") -> pd.DataFrame:
    """Allocate coaches_votes into feasible Brownlow predictions.

    Zero-signal matches (missing or sum-zero coaches_votes) get equal 6/n_players.
    All other matches use the same capped-simplex path as the model pipeline.
    Anomalies are printed; constraints are asserted (no silent invalid fills).
    """
    out = va.copy()
    zero_signal = _coaches_zero_signal_matches(out)
    for mid, reason in sorted(zero_signal.items(), key=lambda kv: kv[0]):
        print(f"ZERO-SIGNAL match_id={mid}: {reason} -> equal allocation 6/n_players")

    # Use coaches_votes as raw scores; NaNs treated as 0 only after zero-signal detection.
    out["raw_prediction"] = out["coaches_votes"].astype(float).fillna(0.0)
    signal_mask = ~out["match_id"].isin(zero_signal)
    # Non-zero-signal matches: same allocator as the model pipeline.
    if signal_mask.any():
        allocated = allocate_frame(out.loc[signal_mask], "raw_prediction", allocation)
        out.loc[signal_mask, "prediction"] = allocated["prediction"].to_numpy()
    # Zero-signal matches: equal share (explicit fallback, not silent epsilon fill).
    for mid in zero_signal:
        m = out["match_id"] == mid
        n = int(m.sum())
        if n == 0:
            print(f"ANOMALOUS match_id={mid}: zero-signal match has no players")
            continue
        out.loc[m, "prediction"] = 6.0 / n

    if out["prediction"].isna().any():
        bad = out.loc[out["prediction"].isna(), "match_id"].drop_duplicates().tolist()
        for mid in bad:
            print(f"ANOMALOUS match_id={mid}: prediction still missing after allocation")
        raise AssertionError(f"{len(bad)} match(es) have missing predictions after allocation")

    assert_feasible_predictions(out)
    return out

def baseline_cv(df, val_years=(2022,2023,2024,2025), allocation="capped_simplex"):
    rows=[]; outs=[]
    for yr in val_years:
        va=df[df.season==yr].copy()
        va["naive"]=va.groupby("match_id").player_id.transform("size").rdiv(6.0)
        d=diagnostics(va.rename(columns={"naive":"prediction"}))
        rows.append({"model":"naive_equal","val_season":yr,**d})
        vc=allocate_coaches_direct(va, allocation=allocation)
        d=diagnostics(vc)
        rows.append({"model":"coaches_direct","val_season":yr,**d})
    return pd.DataFrame(rows)
