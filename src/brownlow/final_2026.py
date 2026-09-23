"""Final 2026 prediction readiness, inference, and portfolio exports.

Frozen specification:
  V2.1 champion feature set = base_plus_components
  temporal strategy = expanding_all
  CatBoostWrapper(seed=42) + capped-simplex allocation
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .allocation import allocate_frame, assert_feasible_predictions
from .coach_intelligence import (
    COACH_FEATURE_COLS,
    SEED,
    attach_coach_features,
    coach_predict_feature_lists,
    cross_fit_coach_predictions,
    experiment_feature_sets,
)
from .metrics import rmse
from .models import CatBoostWrapper

V21_CHAMPION_MEAN = 0.355865
V21_BASE_MEAN = 0.358172
CRITICAL_FEATURES = [
    "coaches_votes",
    "expected_coaches_votes",
    "coach_residual",
    "coach_positive_residual",
    "coach_negative_residual",
    "coach_residual_abs",
    "supercoach_score",
    "afl_fantasy_score",
    "rating_points",
    "disposals",
    "contested_possessions",
    "clearances",
    "goals",
    "score_involvements",
    "metres_gained",
    "tackles",
    "player_position",
    "team_won",
    "match_margin",
    "close_game",
]


def player_display_name(df: pd.DataFrame) -> pd.Series:
    return (df["player_first_name"].astype(str).str.strip() + " " + df["player_last_name"].astype(str).str.strip()).str.strip()


def opponent_team(df: pd.DataFrame) -> pd.Series:
    home = df["match_home_team"]
    away = df["match_away_team"]
    team = df["player_team"]
    return np.where(team == home, away, home)


def classify_feature(hist_miss: float, fut_miss: float, smd: float | None) -> str:
    if fut_miss >= 0.999:
        return "MISSING"
    if fut_miss >= 0.05:
        return "PARTIAL"
    if smd is not None and abs(smd) >= 0.5:
        return "DISTRIBUTION_WARNING"
    if fut_miss > hist_miss + 0.05:
        return "DISTRIBUTION_WARNING"
    return "READY"


def feature_coverage_table(train: pd.DataFrame, test: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    rows = []
    for feat in features:
        if feat not in train.columns and feat not in test.columns:
            rows.append(
                {
                    "feature": feat,
                    "historical_missing_pct": 1.0,
                    "2026_missing_pct": 1.0,
                    "historical_mean": np.nan,
                    "2026_mean": np.nan,
                    "historical_std": np.nan,
                    "2026_std": np.nan,
                    "historical_min": np.nan,
                    "historical_max": np.nan,
                    "2026_min": np.nan,
                    "2026_max": np.nan,
                    "status": "MISSING",
                }
            )
            continue
        h = train[feat] if feat in train.columns else pd.Series(dtype=float)
        f = test[feat] if feat in test.columns else pd.Series(dtype=float)
        hist_miss = float(h.isna().mean()) if len(h) else 1.0
        fut_miss = float(f.isna().mean()) if len(f) else 1.0
        h_num = pd.to_numeric(h, errors="coerce") if len(h) else pd.Series(dtype=float)
        f_num = pd.to_numeric(f, errors="coerce") if len(f) else pd.Series(dtype=float)
        # categorical: report null rates only for mean/std
        if pd.api.types.is_numeric_dtype(h_num) and h_num.notna().any():
            h_mean, h_std = float(h_num.mean()), float(h_num.std())
            h_min, h_max = float(h_num.min()), float(h_num.max())
        else:
            h_mean = h_std = h_min = h_max = np.nan
        if pd.api.types.is_numeric_dtype(f_num) and f_num.notna().any():
            f_mean, f_std = float(f_num.mean()), float(f_num.std())
            f_min, f_max = float(f_num.min()), float(f_num.max())
        else:
            f_mean = f_std = f_min = f_max = np.nan
        smd = None
        if np.isfinite(h_mean) and np.isfinite(f_mean) and np.isfinite(h_std) and h_std > 1e-12:
            smd = (f_mean - h_mean) / h_std
        status = classify_feature(hist_miss, fut_miss, smd)
        rows.append(
            {
                "feature": feat,
                "historical_missing_pct": hist_miss,
                "2026_missing_pct": fut_miss,
                "historical_mean": h_mean,
                "2026_mean": f_mean,
                "historical_std": h_std,
                "2026_std": f_std,
                "historical_min": h_min,
                "historical_max": h_max,
                "2026_min": f_min,
                "2026_max": f_max,
                "standardized_mean_diff": smd,
                "status": status,
                "is_critical": feat in CRITICAL_FEATURES or feat.startswith("coach"),
            }
        )
    return pd.DataFrame(rows)


def distribution_shift_table(train: pd.DataFrame, test: pd.DataFrame, features: list[str], recent_years=(2023, 2024, 2025)) -> pd.DataFrame:
    recent = train[train["season"].isin(recent_years)]
    rows = []
    for feat in features:
        if feat not in train.columns or feat not in test.columns:
            continue
        h = pd.to_numeric(recent[feat], errors="coerce")
        f = pd.to_numeric(test[feat], errors="coerce")
        if h.notna().sum() < 100 or f.notna().sum() < 100:
            continue
        h_mean, h_std = float(h.mean()), float(h.std())
        f_mean = float(f.mean())
        smd = (f_mean - h_mean) / h_std if h_std > 1e-12 else np.nan
        # Population Stability Index on deciles of recent hist
        try:
            bins = np.unique(np.quantile(h.dropna(), np.linspace(0, 1, 11)))
            if len(bins) < 3:
                psi = np.nan
            else:
                h_counts = np.histogram(h.dropna(), bins=bins)[0].astype(float)
                f_counts = np.histogram(f.dropna(), bins=bins)[0].astype(float)
                h_p = (h_counts + 1e-6) / (h_counts.sum() + 1e-6 * len(h_counts))
                f_p = (f_counts + 1e-6) / (f_counts.sum() + 1e-6 * len(f_counts))
                psi = float(np.sum((f_p - h_p) * np.log(f_p / h_p)))
        except Exception:
            psi = np.nan
        hq = h.quantile([0.1, 0.5, 0.9]).to_dict()
        fq = f.quantile([0.1, 0.5, 0.9]).to_dict()
        miss_shift = float(f.isna().mean() - h.isna().mean())
        flag = abs(smd) >= 0.35 or (np.isfinite(psi) and psi >= 0.25) or abs(miss_shift) >= 0.05
        rows.append(
            {
                "feature": feat,
                "recent_mean": h_mean,
                "2026_mean": f_mean,
                "standardized_mean_diff": smd,
                "psi": psi,
                "missingness_shift": miss_shift,
                "recent_p10": hq.get(0.1),
                "recent_p50": hq.get(0.5),
                "recent_p90": hq.get(0.9),
                "2026_p10": fq.get(0.1),
                "2026_p50": fq.get(0.5),
                "2026_p90": fq.get(0.9),
                "suspicious": bool(flag),
            }
        )
    return pd.DataFrame(rows).sort_values("standardized_mean_diff", key=lambda s: s.abs(), ascending=False)


def build_2026_coach_features(train_feat: pd.DataFrame, test_feat: pd.DataFrame, seed: int = SEED) -> pd.DataFrame:
    """Train coach model on all pre-2026 rows; predict expected coaches for 2026; derive residuals."""
    nums, cats = coach_predict_feature_lists(train_feat)
    features = nums + cats
    assert "coaches_votes" not in features and "brownlow_votes" not in features
    assert int(train_feat["season"].max()) < 2026
    print(f"FINAL COACH MODEL: train seasons {sorted(train_feat.season.unique())} max={int(train_feat.season.max())} < 2026")
    model = CatBoostWrapper(seed=seed)
    model.fit(train_feat[features], train_feat["coaches_votes"].astype(float), cat_cols=cats)
    expected = model.predict(test_feat[features])
    actual = test_feat["coaches_votes"].astype(float).to_numpy()
    resid = actual - expected
    out = test_feat[["season", "match_id", "player_id"]].copy()
    out["actual_coaches_votes"] = actual
    out["expected_coaches_votes"] = expected
    out["coach_residual"] = resid
    out["coach_positive_residual"] = np.maximum(resid, 0.0)
    out["coach_negative_residual"] = np.minimum(resid, 0.0)
    out["coach_residual_abs"] = np.abs(resid)
    return out


def write_readiness_markdown(
    path: str,
    hist: pd.DataFrame,
    test: pd.DataFrame,
    coverage: pd.DataFrame,
    passed: bool,
    notes: list[str],
) -> None:
    crit = coverage[coverage["is_critical"] | coverage["feature"].isin(CRITICAL_FEATURES)]
    lines = [
        "# Final 2026 Prediction Readiness Audit",
        "",
        f"**Result: {'PASS' if passed else 'FAIL'}**",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Dataset counts",
        "",
        f"- Historical labelled rows: {len(hist)}",
        f"- 2026 prediction rows: {len(test)}",
        f"- Historical matches: {hist.match_id.nunique()}",
        f"- 2026 matches: {test.match_id.nunique()}",
        f"- Players per 2026 match: {sorted(test.groupby('match_id').size().unique().tolist())}",
        f"- Duplicate player-match keys (hist): {int(hist.duplicated(['season','match_id','player_id']).sum())}",
        f"- Duplicate player-match keys (2026): {int(test.duplicated(['season','match_id','player_id']).sum())}",
        f"- Missing match_id (2026): {int(test.match_id.isna().sum())}",
        f"- Missing player_id (2026): {int(test.player_id.isna().sum())}",
        f"- Missing player names (2026): {int((test.player_first_name.isna()|test.player_last_name.isna()).sum())}",
        f"- Missing team/opponent fields (2026): {int((test.player_team.isna()|test.match_home_team.isna()|test.match_away_team.isna()).sum())}",
        "",
        "## Coaches votes availability",
        "",
        "Actual `coaches_votes` is present in the official 2026 prediction dataset (0% missing).",
        "This matches the historical validation design, where coaches_votes is an observable",
        "input feature (not the Brownlow target). Final inference therefore uses actual 2026",
        "coaches_votes together with leakage-safe expected_coaches_votes from a coach model",
        "trained only on seasons < 2026.",
        "",
        "## Critical feature status",
        "",
    ]
    for _, r in crit.iterrows():
        lines.append(
            f"- `{r['feature']}`: **{r['status']}** "
            f"(hist miss={r['historical_missing_pct']:.3%}, 2026 miss={r['2026_missing_pct']:.3%})"
        )
    lines += ["", "## Notes", ""]
    lines += [f"- {n}" for n in notes] or ["- None"]
    lines += ["", "## Full coverage table", "", "See `final_2026_feature_coverage.csv`.", ""]
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        f.write("\n".join(lines))


def build_leaderboard(pred: pd.DataFrame) -> pd.DataFrame:
    g = pred.copy()
    g["player_name"] = player_display_name(g)
    # primary team = mode across matches
    def _mode(s):
        m = s.mode()
        return m.iloc[0] if len(m) else s.iloc[0]

    rows = []
    for pid, x in g.groupby("player_id"):
        votes = x["allocated_expected_votes"]
        best_idx = votes.idxmax()
        rows.append(
            {
                "player_id": pid,
                "player_name": x["player_name"].iloc[0],
                "team": _mode(x["player_team"]),
                "position": _mode(x["player_position"]),
                "games": int(len(x)),
                "predicted_expected_votes": float(votes.sum()),
                "total_coaches_votes": float(x["coaches_votes"].sum()) if "coaches_votes" in x else np.nan,
                "avg_expected_votes_per_game": float(votes.mean()),
                "number_of_matches_predicted_above_0_5": int((votes > 0.5).sum()),
                "number_of_matches_predicted_above_1_0": int((votes > 1.0).sum()),
                "number_of_matches_predicted_above_2_0": int((votes > 2.0).sum()),
                "best_predicted_match_votes": float(votes.loc[best_idx]),
                "best_predicted_match_id": int(x.loc[best_idx, "match_id"]),
            }
        )
    out = pd.DataFrame(rows).sort_values("predicted_expected_votes", ascending=False).reset_index(drop=True)
    out.insert(0, "predicted_rank", np.arange(1, len(out) + 1))
    return out


def build_match_top3(pred: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for mid, g in pred.groupby("match_id"):
        top = g.nlargest(3, "allocated_expected_votes")
        for rank, (_, r) in enumerate(top.iterrows(), start=1):
            rows.append(
                {
                    "match_id": int(mid),
                    "match_round": int(r["match_round"]),
                    "match_home_team": r["match_home_team"],
                    "match_away_team": r["match_away_team"],
                    "model_rank": rank,
                    "label": "Model-ranked Top 3",
                    "player_id": int(r["player_id"]),
                    "player_name": f"{r['player_first_name']} {r['player_last_name']}",
                    "player_team": r["player_team"],
                    "allocated_expected_votes": float(r["allocated_expected_votes"]),
                }
            )
    return pd.DataFrame(rows)


def build_player_profiles(pred: pd.DataFrame, leaderboard: pd.DataFrame, top_n: int = 30) -> list[dict]:
    top = leaderboard.head(top_n)
    profiles = []
    perf_cols = [
        c
        for c in [
            "disposals",
            "goals",
            "clearances",
            "contested_possessions",
            "score_involvements",
            "metres_gained",
            "supercoach_score",
            "afl_fantasy_score",
            "rating_points",
            "tackles",
        ]
        if c in pred.columns
    ]
    for _, row in top.iterrows():
        g = pred[pred["player_id"] == row["player_id"]].sort_values(["match_date", "match_id"])
        rounds = []
        for _, r in g.iterrows():
            rounds.append(
                {
                    "round": int(r["match_round"]),
                    "match_id": int(r["match_id"]),
                    "match_date": str(r["match_date"].date()) if pd.notna(r["match_date"]) else None,
                    "opponent": str(r["opponent"]),
                    "expected_brownlow_votes": float(r["allocated_expected_votes"]),
                    "coaches_votes": float(r["coaches_votes"]) if pd.notna(r["coaches_votes"]) else None,
                    **{c: (float(r[c]) if pd.notna(r[c]) else None) for c in perf_cols},
                }
            )
        top_perf = sorted(rounds, key=lambda d: d["expected_brownlow_votes"], reverse=True)[:5]
        summaries = {c: float(g[c].mean()) for c in perf_cols}
        profiles.append(
            {
                "rank": int(row["predicted_rank"]),
                "player_id": int(row["player_id"]),
                "player": row["player_name"],
                "team": row["team"],
                "position": row["position"],
                "games": int(row["games"]),
                "expected_votes": float(row["predicted_expected_votes"]),
                "image_url": None,
                "season_performance_averages": summaries,
                "round_by_round": rounds,
                "top_predicted_performances": top_perf,
            }
        )
    return profiles


def make_final_figures(
    leaderboard: pd.DataFrame,
    pred: pd.DataFrame,
    oof_hist: pd.DataFrame | None,
    fig_dir: str = "outputs/figures/final",
) -> None:
    os.makedirs(fig_dir, exist_ok=True)
    plt.rcParams.update({"figure.dpi": 140, "savefig.dpi": 160, "font.size": 11})

    # 1. top 20
    top20 = leaderboard.head(20).iloc[::-1]
    fig, ax = plt.subplots(figsize=(9, 7))
    ax.barh(top20["player_name"], top20["predicted_expected_votes"], color="#1f4e79")
    ax.set_xlabel("Predicted expected Brownlow votes (season)")
    ax.set_title("2026 Predicted Brownlow Leaderboard — Top 20")
    ax.grid(True, axis="x", alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(fig_dir, "top_20_predicted_brownlow.png"))
    plt.close(fig)

    # 2. model progression (verified only)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    names = ["Original CatBoost base", "V2.1 Coach Intelligence\n(base_plus_components)"]
    vals = [V21_BASE_MEAN, V21_CHAMPION_MEAN]
    ax.bar(names, vals, color=["#9dc3e6", "#1f4e79"])
    ax.set_ylabel("Mean allocated OOT RMSE")
    ax.set_title("Verified model progression")
    for i, v in enumerate(vals):
        ax.text(i, v + 0.0008, f"{v:.6f}", ha="center")
    ax.set_ylim(0.35, 0.365)
    fig.tight_layout()
    fig.savefig(os.path.join(fig_dir, "model_progression.png"))
    plt.close(fig)

    # 3. cumulative expected votes for top 5
    top5_ids = leaderboard.head(5)["player_id"].tolist()
    fig, ax = plt.subplots(figsize=(9, 5))
    for pid in top5_ids:
        g = pred[pred["player_id"] == pid].sort_values(["match_round", "match_date", "match_id"])
        name = player_display_name(g).iloc[0]
        ax.plot(np.arange(1, len(g) + 1), g["allocated_expected_votes"].cumsum(), marker="o", label=name)
    ax.set_xlabel("Games played (chronological)")
    ax.set_ylabel("Cumulative expected Brownlow votes")
    ax.set_title("Top 5 players — cumulative expected votes")
    ax.legend(frameon=False, fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(fig_dir, "top_players_round_progression.png"))
    plt.close(fig)

    # 4. coaches vs expected brownlow
    fig, ax = plt.subplots(figsize=(7, 5))
    sample = pred.sample(n=min(5000, len(pred)), random_state=SEED)
    ax.scatter(sample["coaches_votes"], sample["allocated_expected_votes"], s=8, alpha=0.25, color="#1f4e79")
    ax.set_xlabel("Actual coaches votes (2026)")
    ax.set_ylabel("Allocated expected Brownlow votes")
    ax.set_title("Coaches votes vs model expected Brownlow (2026)")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(fig_dir, "coach_vs_brownlow.png"))
    plt.close(fig)

    # 5. historical OOT error by vote category (from V2.1 OOF if available)
    if oof_hist is not None and len(oof_hist):
        fig, ax = plt.subplots(figsize=(7, 4.5))
        oof_hist = oof_hist.copy()
        oof_hist["abs_err"] = (oof_hist["actual_brownlow_votes"] - oof_hist["pred"]).abs()
        means = oof_hist.groupby("actual_brownlow_votes")["abs_err"].mean()
        ax.bar(means.index.astype(str), means.values, color="#2e75b6")
        ax.set_xlabel("Actual Brownlow votes")
        ax.set_ylabel("Mean absolute error (allocated OOT)")
        ax.set_title("Historical OOT error by Brownlow vote category")
        ax.grid(True, axis="y", alpha=0.3)
        fig.tight_layout()
        fig.savefig(os.path.join(fig_dir, "model_error_by_vote.png"))
        plt.close(fig)

    # 6. top player performance profiles (normalized z vs field)
    dims = [c for c in ["disposals", "contested_possessions", "clearances", "goals", "score_involvements", "metres_gained", "supercoach_score"] if c in pred.columns]
    top6 = leaderboard.head(6)
    field_mean = pred[dims].mean()
    field_std = pred[dims].std().replace(0, np.nan)
    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(dims))
    width = 0.12
    for i, (_, row) in enumerate(top6.iterrows()):
        g = pred[pred["player_id"] == row["player_id"]]
        z = ((g[dims].mean() - field_mean) / field_std).fillna(0).to_numpy()
        ax.plot(x, z, marker="o", label=row["player_name"])
    ax.set_xticks(x)
    ax.set_xticklabels(dims, rotation=30, ha="right")
    ax.axhline(0, color="grey", lw=0.8)
    ax.set_ylabel("Season average z-score vs 2026 field")
    ax.set_title("Leading players — normalized performance profile")
    ax.legend(frameon=False, fontsize=8, ncol=2)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(fig_dir, "top_player_performance_profiles.png"))
    plt.close(fig)
    print(f"wrote figures under {fig_dir}")


def write_model_card(path: str, feature_count: int, train_seasons: list[int], n_train: int) -> None:
    text = f"""# MODEL CARD — Brownlow Intelligence

## Brownlow Intelligence
Predicting and Understanding Human Judgement in Elite Sport — Point Prediction Engine.

## Objective
Predict **expected Brownlow Medal votes** for each player-match, then allocate predictions within each match so that:
- each player prediction is in `[0, 3]`
- each match sums to exactly `6`

## Data
Historical labelled AFL player-match observations (seasons {min(train_seasons)}–{max(train_seasons)}; n={n_train}) and the official 2026 prediction rows.

## Prediction target
`brownlow_votes` (umpire votes). The 2026 Brownlow target is unavailable and was not used.

## Validation design
Rolling out-of-time folds:
- train seasons `< Y`, validate year `Y` for Y ∈ {{2022, 2023, 2024, 2025}}
Primary metric: mean allocated OOT RMSE.

## Final feature families
- Match-relative performance features (z-scores, ranks, shares, percentiles)
- Team shares / context (result, margin buckets, thresholds)
- Lagged player recognition history (strictly past matches only)
- Raw `coaches_votes` (available in both historical and 2026 official rows)
- Leakage-safe Coach Intelligence residuals (`expected_coaches_votes` and residual components)

Feature count used by frozen champion: **{feature_count}**

## Coach Intelligence methodology
A CatBoost model predicts `coaches_votes` from observable performance features (excluding coaches_votes and brownlow_votes).
Expected coaches votes are generated out-of-time / expanding-year for historical rows, and with a final coach model trained on all seasons `< 2026` for 2026 inference.
Residual features measure coach recognition beyond the performance model.

## Temporal experiment conclusion (V2.2)
- Best strategy: **expanding_all**
- Retain all historical seasons including 2020
- No exponential time decay
- No trailing-window restriction

## Final model
- Algorithm: CatBoostRegressor (existing project hyperparameters, seed=42)
- Feature set: V2.1 `base_plus_components`
- Training window: all labelled seasons before 2026

## Constraint layer
Euclidean capped-simplex projection per match onto `{{x : sum x = 6, 0 ≤ x ≤ 3}}`.

## Historical OOT performance (verified)
- Original CatBoost base mean allocated OOT RMSE: **{V21_BASE_MEAN}**
- V2.1 champion (`base_plus_components`) mean allocated OOT RMSE: **{V21_CHAMPION_MEAN}**

## 2026 inference methodology
1. Build features jointly with history (lagged features remain past-only).
2. Fit coach model on seasons `< 2026`; predict expected coaches for 2026; derive residual features using actual 2026 coaches_votes.
3. Fit Brownlow champion on seasons `< 2026`.
4. Predict raw expected votes; allocate within each match.

## Limitations
- The model predicts **expected umpire voting behaviour** from available player-match information.
- It does **not** observe the private umpire deliberation process.
- Associations should not be interpreted as causal effects.
- Expected season totals are continuous forecasts, not guaranteed finishing positions.
- Model-ranked Top-3 match views are storytelling ranks over continuous expected votes, not literal official 3-2-1 ballots.
"""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        f.write(text)


def load_v21_oof_for_error_plot() -> pd.DataFrame | None:
    path = "outputs/oof/v2_1_coach_oof_predictions.csv"
    if not os.path.exists(path):
        return None
    oof = pd.read_csv(path)
    col = "coach_components_prediction_model"
    if col not in oof.columns:
        return None
    return oof.rename(columns={col: "pred"})[["actual_brownlow_votes", "pred"]].dropna()
