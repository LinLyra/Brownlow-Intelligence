import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error, roc_auc_score

def rmse(y, p): return float(np.sqrt(mean_squared_error(y, p)))

def diagnostics(df, pred_col="prediction"):
    y = df.brownlow_votes.to_numpy(); p = df[pred_col].to_numpy()
    poll = y > 0
    result = {
        "rmse": rmse(y,p),
        "rmse_zero": rmse(y[~poll],p[~poll]) if (~poll).any() else np.nan,
        "rmse_pollers": rmse(y[poll],p[poll]) if poll.any() else np.nan,
        "match_sum_abs_max": float((df.groupby("match_id")[pred_col].sum()-6).abs().max()),
    }
    # top-3 recall: actual three recipients contained in predicted top 3
    vals=[]
    for _,g in df.groupby("match_id"):
        actual=set(g.loc[g.brownlow_votes>0].player_id)
        predicted=set(g.nlargest(3,pred_col).player_id)
        if actual: vals.append(len(actual & predicted)/len(actual))
    result["top3_recall"] = float(np.mean(vals)) if vals else np.nan
    return result
