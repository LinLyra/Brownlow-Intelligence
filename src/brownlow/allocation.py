from __future__ import annotations
import numpy as np
import pandas as pd

def scale_nonnegative(s, total=6.0):
    x = np.clip(np.asarray(s, dtype=float), 0, None)
    if x.sum() <= 1e-12:
        return np.full(len(x), total / len(x))
    return x * total / x.sum()

def capped_simplex_projection(v, total=6.0, cap=3.0, tol=1e-12, max_iter=200):
    """Euclidean projection onto {x: sum x=total, 0<=x<=cap} via bisection.
    This is optimal only for distance to supplied raw scores, not automatically for true-label RMSE.
    """
    v = np.asarray(v, dtype=float)
    lo, hi = float(v.min() - cap), float(v.max())
    # Do not early-break: updating lo/hi then re-midpointting after a lucky hit
    # yields a different tau and can leave sum far from `total`.
    for _ in range(max_iter):
        tau = 0.5 * (lo + hi)
        s = np.clip(v - tau, 0.0, cap).sum()
        if s > total:
            lo = tau
        else:
            hi = tau
        if abs(hi - lo) < tol:
            break
    x = np.clip(v - 0.5 * (lo + hi), 0.0, cap)
    # numerical correction
    for _ in range(5):
        diff = total - x.sum()
        if abs(diff) < 1e-10:
            break
        free = (x > 1e-12) & (x < cap - 1e-12)
        if not free.any():
            break
        x[free] += diff / free.sum()
        x = np.clip(x, 0, cap)
    return x

def assert_feasible_predictions(df, pred_col="prediction", total=6.0, cap=3.0, atol=1e-8):
    """Raise with anomalous match IDs if allocation constraints are violated."""
    p = df[pred_col].to_numpy(dtype=float)
    bad_bounds = df.loc[(p < -atol) | (p > cap + atol), "match_id"].drop_duplicates().tolist()
    sums = df.groupby("match_id")[pred_col].sum()
    bad_sums = sums[(sums - total).abs() > atol]
    anomalies = []
    for mid in bad_bounds:
        anomalies.append((mid, f"player prediction outside [0,{cap}]"))
    for mid, s in bad_sums.items():
        anomalies.append((mid, f"match sum={float(s):.12g} (expected {total})"))
    if anomalies:
        for mid, reason in anomalies:
            print(f"ANOMALOUS match_id={mid}: {reason}")
        raise AssertionError(
            f"{len(anomalies)} allocation constraint violation(s); see match IDs above"
        )

def allocate_frame(df, raw_col="raw_prediction", method="capped_simplex"):
    out = df.copy()
    fn = capped_simplex_projection if method == "capped_simplex" else scale_nonnegative
    out["prediction"] = out.groupby("match_id", group_keys=False)[raw_col].transform(lambda s: fn(s.to_numpy()))
    return out
