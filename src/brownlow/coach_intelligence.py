"""V2.1 Coach -> Umpire Intelligence: translation tables + leakage-safe coach residuals."""
from __future__ import annotations

import os
from typing import Iterable, Sequence

import numpy as np
import pandas as pd

from .features import model_columns
from .models import CatBoostWrapper

VAL_YEARS = (2022, 2023, 2024, 2025)
COACH_FEATURE_COLS = (
    "expected_coaches_votes",
    "coach_residual",
    "coach_positive_residual",
    "coach_negative_residual",
    "coach_residual_abs",
)
# Minimum prior seasons before we fit a coach model for a target season.
MIN_TRAIN_SEASONS = 3
SEED = 42


def margin_bucket(margin: pd.Series) -> pd.Series:
    a = margin.abs()
    return pd.Series(
        np.where(a <= 12, "close", np.where(a <= 36, "medium", "blowout")),
        index=margin.index,
        dtype="object",
    )


def _translation_table(df: pd.DataFrame, group_cols: Sequence[str] | None = None) -> pd.DataFrame:
    """Empirical P(Brownlow | coaches_votes[, strata]) and E[Brownlow]."""
    x = df.loc[df["brownlow_votes"].notna() & df["coaches_votes"].notna()].copy()
    x["coaches_votes"] = x["coaches_votes"].astype(int)
    keys = list(group_cols or []) + ["coaches_votes"]
    rows = []
    for key, g in x.groupby(keys, observed=True, dropna=False):
        if not isinstance(key, tuple):
            key = (key,)
        n = len(g)
        votes = g["brownlow_votes"].to_numpy(dtype=float)
        row = {k: v for k, v in zip(keys, key)}
        for b in (0, 1, 2, 3):
            row[f"P_brownlow_{b}"] = float(np.mean(votes == b))
        row["E_brownlow"] = float(votes.mean())
        row["n"] = int(n)
        rows.append(row)
    out = pd.DataFrame(rows).sort_values(keys).reset_index(drop=True)
    return out


def build_translation_reports(hist: pd.DataFrame, out_dir: str = "outputs/reports") -> dict[str, pd.DataFrame]:
    """Part A: descriptive coach -> Brownlow translation tables (not used as predictive features)."""
    os.makedirs(out_dir, exist_ok=True)
    x = hist.copy()
    if "team_won" not in x.columns:
        x["team_won"] = (x["player_team"] == x["match_winner"]).astype("int8")
    x["margin_bucket"] = margin_bucket(x["match_margin"])

    tables = {
        "coach_to_brownlow_translation.csv": _translation_table(x),
        "coach_translation_by_position.csv": _translation_table(x, ["player_position"]),
        "coach_translation_by_result.csv": _translation_table(x, ["team_won"]),
        "coach_translation_by_margin.csv": _translation_table(x, ["margin_bucket"]),
    }
    for name, tbl in tables.items():
        path = os.path.join(out_dir, name)
        tbl.to_csv(path, index=False)
        print(f"wrote {path} rows={len(tbl)}")
    return tables


def coach_predict_feature_lists(df: pd.DataFrame) -> tuple[list[str], list[str]]:
    """Features for E[coaches_votes | performance]. Forbidden: coaches_votes*, brownlow_votes."""
    nums, cats = model_columns(df)
    forbid_exact = {
        "brownlow_votes",
        "coaches_votes",
        "match_id",
        "player_id",
        *COACH_FEATURE_COLS,
    }
    nums = [
        c
        for c in nums
        if c not in forbid_exact
        and not c.startswith("coaches_votes")
        and c not in COACH_FEATURE_COLS
    ]
    cats = [c for c in cats if c not in forbid_exact]
    assert "coaches_votes" not in nums and "coaches_votes" not in cats
    assert "brownlow_votes" not in nums and "brownlow_votes" not in cats
    assert not any(c.startswith("coaches_votes") for c in nums)
    return nums, cats


def brownlow_base_feature_lists(df: pd.DataFrame) -> tuple[list[str], list[str]]:
    """Current CatBoost Brownlow feature set (includes raw coaches_votes)."""
    return model_columns(df)


def drop_raw_coach_features(nums: Iterable[str], cats: Iterable[str]) -> tuple[list[str], list[str]]:
    nums = [c for c in nums if c != "coaches_votes" and not str(c).startswith("coaches_votes")]
    cats = list(cats)
    return nums, cats


def _residual_frame(actual: pd.Series, expected: pd.Series) -> pd.DataFrame:
    resid = actual.astype(float) - expected.astype(float)
    return pd.DataFrame(
        {
            "actual_coaches_votes": actual.astype(float).to_numpy(),
            "expected_coaches_votes": expected.astype(float).to_numpy(),
            "coach_residual": resid.to_numpy(),
            "coach_positive_residual": np.maximum(resid.to_numpy(), 0.0),
            "coach_negative_residual": np.minimum(resid.to_numpy(), 0.0),
            "coach_residual_abs": np.abs(resid.to_numpy()),
        },
        index=actual.index,
    )


def cross_fit_coach_predictions(
    df: pd.DataFrame,
    cache_path: str = "outputs/cache/cross_fitted_coach_predictions.csv",
    min_train_seasons: int = MIN_TRAIN_SEASONS,
    seed: int = SEED,
    force_recompute: bool = False,
) -> pd.DataFrame:
    """Expanding-year OOT coach predictions for every historical season with enough prior history.

    For target season S: train coach model on seasons < S, predict S.
    Seasons with fewer than `min_train_seasons` prior seasons get NaN expected values
    (CatBoost handles NaN in downstream Brownlow models). Never uses in-sample residuals.
    """
    os.makedirs(os.path.dirname(cache_path) or ".", exist_ok=True)
    if os.path.exists(cache_path) and not force_recompute:
        cached = pd.read_csv(cache_path)
        print(f"loaded coach cross-fit cache: {cache_path} rows={len(cached)}")
        return cached

    nums, cats = coach_predict_feature_lists(df)
    features = nums + cats
    seasons = sorted(int(s) for s in df["season"].dropna().unique())
    pieces: list[pd.DataFrame] = []

    for season in seasons:
        prior = [s for s in seasons if s < season]
        target = df[df["season"] == season].copy()
        keys = target[["season", "match_id", "player_id"]].copy()

        if len(prior) < min_train_seasons:
            print(
                f"COACH FOLD season={season}: insufficient history "
                f"(prior_seasons={len(prior)} < {min_train_seasons}) -> NaN residuals"
            )
            exp = pd.Series(np.nan, index=target.index)
            block = pd.concat([keys.reset_index(drop=True), _residual_frame(target["coaches_votes"], exp).reset_index(drop=True)], axis=1)
            pieces.append(block)
            continue

        train = df[df["season"] < season]
        max_train = int(train["season"].max())
        assert max_train < season, f"leakage: max(train_season)={max_train} >= validation_season={season}"
        print(
            f"COACH FOLD season={season}: train_seasons={sorted(train['season'].unique().tolist())} "
            f"max(train)={max_train} < val={season}  n_train={len(train)} n_val={len(target)}"
        )

        y = train["coaches_votes"].astype(float)
        assert "coaches_votes" not in features
        assert "brownlow_votes" not in features
        model = CatBoostWrapper(seed=seed)
        model.fit(train[features], y, cat_cols=cats)
        expected = pd.Series(model.predict(target[features]), index=target.index)
        block = pd.concat(
            [keys.reset_index(drop=True), _residual_frame(target["coaches_votes"], expected).reset_index(drop=True)],
            axis=1,
        )
        pieces.append(block)

    out = pd.concat(pieces, ignore_index=True)
    # Uniqueness by player-match key
    dup = out.duplicated(["season", "match_id", "player_id"]).sum()
    assert dup == 0, f"duplicate player-match keys in coach cache: {dup}"
    out.to_csv(cache_path, index=False)
    print(f"wrote coach cross-fit cache: {cache_path} rows={len(out)}")
    return out


def attach_coach_features(df: pd.DataFrame, coach_oof: pd.DataFrame) -> pd.DataFrame:
    """Left-join leakage-safe coach residual features onto feature frame."""
    cols = ["season", "match_id", "player_id", *COACH_FEATURE_COLS]
    merge_cols = [c for c in cols if c in coach_oof.columns]
    extra = [c for c in COACH_FEATURE_COLS if c in df.columns]
    base = df.drop(columns=extra, errors="ignore")
    out = base.merge(coach_oof[merge_cols], on=["season", "match_id", "player_id"], how="left", validate="one_to_one")
    return out


def experiment_feature_sets(df: pd.DataFrame) -> dict[str, tuple[list[str], list[str]]]:
    """Controlled ablation feature sets (identical cats where applicable)."""
    base_nums, base_cats = brownlow_base_feature_lists(df)
    # Ensure coach intelligence columns are not already in base via model_columns
    base_nums = [c for c in base_nums if c not in COACH_FEATURE_COLS]
    no_coach_nums, no_coach_cats = drop_raw_coach_features(base_nums, base_cats)

    def add(nums: list[str], extra: Sequence[str]) -> list[str]:
        out = list(nums)
        for c in extra:
            if c not in out:
                out.append(c)
        return out

    return {
        "base": (list(base_nums), list(base_cats)),
        "base_no_coach": (list(no_coach_nums), list(no_coach_cats)),
        "base_plus_expected": (add(base_nums, ["expected_coaches_votes"]), list(base_cats)),
        "base_plus_residual": (add(base_nums, ["coach_residual"]), list(base_cats)),
        "base_plus_components": (
            add(
                base_nums,
                [
                    "expected_coaches_votes",
                    "coach_residual",
                    "coach_positive_residual",
                    "coach_negative_residual",
                    "coach_residual_abs",
                ],
            ),
            list(base_cats),
        ),
        "coach_intelligence": (
            add(base_nums, ["expected_coaches_votes", "coach_residual"]),
            list(base_cats),
        ),
    }


EXPERIMENT_PRED_COL = {
    "base": "base_prediction",
    "base_no_coach": "base_no_coach_prediction",
    "base_plus_expected": "expected_coach_prediction_model",
    "base_plus_residual": "coach_residual_prediction_model",
    "base_plus_components": "coach_components_prediction_model",
    "coach_intelligence": "coach_intelligence_prediction_model",
}
