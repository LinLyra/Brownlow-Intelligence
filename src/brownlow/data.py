from __future__ import annotations
import pandas as pd

KEYS = ["season", "match_id", "player_id"]

def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["match_date"] = pd.to_datetime(df["match_date"], dayfirst=True, errors="coerce")
    return df

def audit_and_clean(df: pd.DataFrame, predict_season: int = 2026):
    hist = df[df.season < predict_season].copy()
    future = df[df.season == predict_season].copy()
    sums = hist.groupby(["season", "match_id"], observed=True).brownlow_votes.sum(min_count=1)
    bad = sums[(sums.notna()) & (~sums.between(5.999999, 6.000001))]
    bad_keys = set(bad.index.tolist())
    if bad_keys:
        idx = pd.MultiIndex.from_frame(hist[["season", "match_id"]])
        hist = hist[~idx.isin(bad_keys)].copy()
    report = {
        "rows": len(df), "columns": df.shape[1], "historical_rows": len(hist),
        "prediction_rows": len(future), "bad_vote_sum_matches": list(bad_keys),
        "duplicate_keys": int(df.duplicated(KEYS).sum()),
        "prediction_matches": int(future.match_id.nunique()),
        "prediction_players_per_match": future.groupby("match_id").size().value_counts().sort_index().to_dict(),
    }
    return hist, future, report
