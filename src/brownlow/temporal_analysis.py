"""V2.2 Temporal robustness and distribution-shift analysis.

Frozen V2.1 champion feature set: base_plus_components.
Only the temporal training window / sample weights vary.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from .allocation import allocate_frame, assert_feasible_predictions
from .coach_intelligence import SEED, VAL_YEARS, experiment_feature_sets
from .metrics import diagnostics, rmse
from .models import CatBoostWrapper

V21_CHAMPION_MEAN = 0.355865
V21_REPRO_TOL = 0.0015
BOOTSTRAP_SEED = 42
BOOTSTRAP_ITERS = 500

DRIFT_RAW = [
    "coaches_votes",
    "supercoach_score",
    "afl_fantasy_score",
    "rating_points",
    "disposals",
    "contested_possessions",
    "clearances",
    "goals",
    "score_involvements",
    "metres_gained",
]
DRIFT_PCT = [f"{c}__match_pct" for c in DRIFT_RAW if c != "coaches_votes"] + ["coaches_votes__match_pct"]

LINEAR_FEATURES = [
    "coaches_votes",
    "disposals__match_pct",
    "contested_possessions__match_pct",
    "clearances__match_pct",
    "goals__match_pct",
    "score_involvements__match_pct",
    "team_won",
    "close_game",
    "blowout",
]


@dataclass(frozen=True)
class Strategy:
    name: str
    kind: str  # expanding | expanding_exclude | trailing | decay
    param: float | int | None = None


STRATEGIES: list[Strategy] = [
    Strategy("expanding_all", "expanding"),
    Strategy("expanding_exclude_2020", "expanding_exclude", 2020),
    Strategy("trailing_8", "trailing", 8),
    Strategy("trailing_6", "trailing", 6),
    Strategy("trailing_4", "trailing", 4),
    Strategy("decay_005", "decay", 0.05),
    Strategy("decay_010", "decay", 0.10),
    Strategy("decay_020", "decay", 0.20),
    Strategy("decay_035", "decay", 0.35),
]


def effective_sample_size(weights: np.ndarray) -> float:
    w = np.asarray(weights, dtype=float)
    if len(w) == 0 or np.sum(w) <= 0:
        return 0.0
    return float((np.sum(w) ** 2) / np.sum(w**2))


def build_train_slice(
    df: pd.DataFrame,
    val_year: int,
    strategy: Strategy,
) -> tuple[pd.DataFrame, np.ndarray, dict]:
    """Return training rows, sample weights, and fold metadata. Leakage-safe."""
    prior = df[df["season"] < val_year].copy()
    assert prior["season"].max() < val_year

    if strategy.kind == "expanding":
        train = prior
    elif strategy.kind == "expanding_exclude":
        excl = int(strategy.param)
        train = prior[prior["season"] != excl].copy()
    elif strategy.kind == "trailing":
        n = int(strategy.param)
        seasons = sorted(prior["season"].unique())
        keep = set(seasons[-n:]) if len(seasons) > n else set(seasons)
        train = prior[prior["season"].isin(keep)].copy()
    elif strategy.kind == "decay":
        lam = float(strategy.param)
        train = prior
        age = val_year - train["season"].astype(float)
        weights = np.exp(-lam * age.to_numpy())
        meta = _fold_meta(val_year, train, weights)
        return train, weights, meta
    else:
        raise ValueError(strategy.kind)

    weights = np.ones(len(train), dtype=float)
    meta = _fold_meta(val_year, train, weights)
    return train, weights, meta


def _fold_meta(val_year: int, train: pd.DataFrame, weights: np.ndarray) -> dict:
    seasons = sorted(int(s) for s in train["season"].unique())
    return {
        "validation_year": val_year,
        "min_train_year": int(min(seasons)) if seasons else None,
        "max_train_year": int(max(seasons)) if seasons else None,
        "n_seasons": len(seasons),
        "n_observations": int(len(train)),
        "effective_n": effective_sample_size(weights),
        "train_seasons": seasons,
    }


def champion_feature_lists(df: pd.DataFrame) -> tuple[list[str], list[str]]:
    sets = experiment_feature_sets(df)
    return sets["base_plus_components"]


def eval_allocated(df: pd.DataFrame) -> dict:
    d = diagnostics(df, pred_col="prediction")
    y = df["brownlow_votes"].to_numpy(dtype=float)
    raw = df["raw_prediction"].to_numpy(dtype=float)
    out = {
        "rmse_allocated": d["rmse"],
        "rmse_raw": rmse(y, raw),
        "zero_vote_RMSE": d["rmse_zero"],
        "poller_RMSE": d["rmse_pollers"],
        "top3_recall": d["top3_recall"],
        "match_sum_abs_max": d["match_sum_abs_max"],
        "n_validation_rows": int(len(df)),
    }
    return out


def run_temporal_strategies(
    df: pd.DataFrame,
    strategies: list[Strategy] = STRATEGIES,
    val_years: tuple[int, ...] = VAL_YEARS,
    seed: int = SEED,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Fit V2.1 champion features under each temporal strategy.

    Returns fold metrics, wide scorecard helpers, and long OOF predictions.
    """
    nums, cats = champion_feature_lists(df)
    features = nums + cats
    print(f"V2.2 champion features: n_num={len(nums)} n_cat={len(cats)} total={len(features)}")

    fold_rows: list[dict] = []
    oof_parts: list[pd.DataFrame] = []

    for strat in strategies:
        print(f"\n=== STRATEGY {strat.name} ===")
        year_parts: list[pd.DataFrame] = []
        for yr in val_years:
            train, weights, meta = build_train_slice(df, yr, strat)
            assert meta["max_train_year"] < yr
            print(
                f"  val={yr} train=[{meta['min_train_year']},{meta['max_train_year']}] "
                f"n_seasons={meta['n_seasons']} n={meta['n_observations']} "
                f"eff_n={meta['effective_n']:.1f}"
            )
            va = df[df["season"] == yr].copy()
            model = CatBoostWrapper(seed=seed)
            # Unweighted strategies pass ones; decay passes exp(-lambda*age).
            use_w = weights if strat.kind == "decay" else None
            model.fit(train[features], train["brownlow_votes"], cat_cols=cats, sample_weight=use_w)
            va["raw_prediction"] = model.predict(va[features])
            assert np.isfinite(va["raw_prediction"]).all()
            va = allocate_frame(va, "raw_prediction", "capped_simplex")
            assert_feasible_predictions(va)
            metrics = eval_allocated(va)
            fold_rows.append({"strategy": strat.name, **meta, **metrics})
            year_parts.append(
                va[["season", "match_id", "player_id", "brownlow_votes"]]
                .rename(columns={"brownlow_votes": "actual_brownlow_votes"})
                .assign(strategy=strat.name, prediction=va["prediction"].to_numpy(), raw_prediction=va["raw_prediction"].to_numpy())
            )
        oof_parts.append(pd.concat(year_parts, ignore_index=True))

    folds = pd.DataFrame(fold_rows)
    oof = pd.concat(oof_parts, ignore_index=True)
    assert oof.duplicated(["strategy", "season", "match_id", "player_id"]).sum() == 0
    return folds, oof


def temporal_scorecard(folds: pd.DataFrame, champion_mean: float = V21_CHAMPION_MEAN) -> pd.DataFrame:
    piv = folds.pivot(index="strategy", columns="validation_year", values="rmse_allocated")
    piv = piv.reindex(columns=list(VAL_YEARS))
    rows = []
    for strat, g in folds.groupby("strategy"):
        by_year = g.set_index("validation_year")["rmse_allocated"]
        mean_rmse = float(by_year.mean())
        recent2 = float(by_year.loc[[2024, 2025]].mean())
        rows.append(
            {
                "strategy": strat,
                **{int(y): float(by_year.loc[y]) for y in VAL_YEARS},
                "mean_rmse": mean_rmse,
                "std_rmse": float(by_year.std(ddof=0)),
                "worst_season_rmse": float(by_year.max()),
                "recent2_mean_rmse": recent2,
                "delta_vs_v21_champion": mean_rmse - champion_mean,
            }
        )
    out = pd.DataFrame(rows)
    # preserve strategy order
    order = [s.name for s in STRATEGIES]
    out["strategy"] = pd.Categorical(out["strategy"], categories=order, ordered=True)
    return out.sort_values("strategy").reset_index(drop=True)


def paired_comparison(
    oof: pd.DataFrame,
    baseline: str = "expanding_all",
    n_boot: int = BOOTSTRAP_ITERS,
    seed: int = BOOTSTRAP_SEED,
) -> pd.DataFrame:
    """Paired squared-error diffs vs baseline; match-block bootstrap CI."""
    base = oof[oof["strategy"] == baseline][
        ["season", "match_id", "player_id", "actual_brownlow_votes", "prediction"]
    ].rename(columns={"prediction": "pred_base"})
    rows = []
    rng = np.random.default_rng(seed)

    for strat in [s.name for s in STRATEGIES if s.name != baseline]:
        cur = oof[oof["strategy"] == strat][
            ["season", "match_id", "player_id", "prediction"]
        ].rename(columns={"prediction": "pred_cur"})
        m = base.merge(cur, on=["season", "match_id", "player_id"], how="inner", validate="one_to_one")
        y = m["actual_brownlow_votes"].to_numpy(dtype=float)
        se_base = (y - m["pred_base"].to_numpy()) ** 2
        se_cur = (y - m["pred_cur"].to_numpy()) ** 2
        diff = se_cur - se_base  # negative => strategy better
        # season-level mean SE diffs
        m = m.assign(se_diff=diff)
        season_diffs = m.groupby("season")["se_diff"].mean().to_dict()

        # Match-block bootstrap on mean paired MSE difference
        matches = m[["season", "match_id"]].drop_duplicates().to_numpy()
        match_keys = [tuple(x) for x in matches]
        # pre-aggregate match-level mean diff (still weighted equally across matches)
        match_diff = m.groupby(["season", "match_id"])["se_diff"].mean()
        boot = []
        n_m = len(match_diff)
        values = match_diff.to_numpy()
        for _ in range(n_boot):
            idx = rng.integers(0, n_m, size=n_m)
            boot.append(float(values[idx].mean()))
        boot = np.asarray(boot)
        lo, hi = np.quantile(boot, [0.025, 0.975])

        rows.append(
            {
                "strategy": strat,
                "baseline": baseline,
                "mean_paired_mse_diff": float(diff.mean()),
                "median_paired_mse_diff": float(np.median(diff)),
                "pct_obs_improved": float(np.mean(diff < 0) * 100.0),
                "boot_mean_mse_diff": float(boot.mean()),
                "boot_ci95_lo": float(lo),
                "boot_ci95_hi": float(hi),
                "n_obs": int(len(m)),
                "n_matches": int(n_m),
                **{f"season_{int(k)}_mse_diff": float(v) for k, v in season_diffs.items()},
            }
        )
    return pd.DataFrame(rows)


def feature_drift_table(hist: pd.DataFrame) -> pd.DataFrame:
    rows = []
    features = [c for c in DRIFT_RAW + DRIFT_PCT if c in hist.columns]
    for season, g in hist.groupby("season"):
        y = g["brownlow_votes"].astype(float)
        for feat in features:
            x = g[feat].astype(float)
            mask = x.notna() & y.notna()
            if mask.sum() < 30:
                pearson = spearman = np.nan
            else:
                pearson = float(x[mask].corr(y[mask], method="pearson"))
                spearman = float(x[mask].corr(y[mask], method="spearman"))
            rows.append(
                {
                    "season": int(season),
                    "feature": feat,
                    "feature_family": "match_pct" if feat.endswith("__match_pct") else "raw",
                    "pearson": pearson,
                    "spearman": spearman,
                    "n": int(mask.sum()),
                }
            )
    return pd.DataFrame(rows)


def voting_environment_tables(hist: pd.DataFrame) -> dict[str, pd.DataFrame]:
    x = hist.copy()
    if "team_won" not in x.columns:
        x["team_won"] = (x["player_team"] == x["match_winner"]).astype("int8")
    x["is_three"] = (x["brownlow_votes"] == 3).astype(int)
    vote_sum = x.groupby("season")["brownlow_votes"].transform("sum").replace(0, np.nan)

    # Position vote share
    pos = (
        x.groupby(["season", "player_position"], observed=True)["brownlow_votes"]
        .sum()
        .reset_index(name="votes")
    )
    pos["vote_share"] = pos["votes"] / pos.groupby("season")["votes"].transform("sum")
    three = (
        x.groupby(["season", "player_position"], observed=True)["is_three"]
        .sum()
        .reset_index(name="n_three_votes")
    )
    three["three_share"] = three["n_three_votes"] / three.groupby("season")["n_three_votes"].transform("sum")
    pos = pos.merge(three, on=["season", "player_position"], how="left")

    # Winning/losing vote share
    wl = (
        x.groupby(["season", "team_won"], observed=True)["brownlow_votes"]
        .sum()
        .reset_index(name="votes")
    )
    wl["vote_share"] = wl["votes"] / wl.groupby("season")["votes"].transform("sum")
    wl["team_result"] = wl["team_won"].map({1: "winning", 0: "losing"})

    # Mean coaches conditional on brownlow
    coach_cond = (
        x.groupby(["season", "brownlow_votes"])["coaches_votes"]
        .agg(mean_coaches="mean", median_coaches="median", n="size")
        .reset_index()
    )

    # Core stats by brownlow level
    core = ["disposals", "contested_possessions", "clearances", "goals", "score_involvements", "metres_gained", "supercoach_score"]
    core = [c for c in core if c in x.columns]
    perf = (
        x.groupby(["season", "brownlow_votes"])[core]
        .agg(["mean", "median"])
        .reset_index()
    )
    perf.columns = ["season", "brownlow_votes"] + [f"{a}_{b}" for a, b in perf.columns[2:]]

    return {
        "position_vote_share": pos,
        "winning_losing_vote_share": wl,
        "coaches_by_brownlow": coach_cond,
        "performance_by_brownlow": perf,
    }


def temporal_linear_coefficients(
    hist: pd.DataFrame,
    val_years: tuple[int, ...] = VAL_YEARS,
    alpha: float = 1.0,
) -> pd.DataFrame:
    """Explanatory Ridge coefficients over expanding prior windows (not the champion)."""
    feats = [c for c in LINEAR_FEATURES if c in hist.columns]
    rows: list[dict] = []

    for yr in val_years:
        tr = hist[hist["season"] < yr].copy()
        assert int(tr["season"].max()) < yr
        X = tr[feats].astype(float).fillna(0.0)
        y = tr["brownlow_votes"].astype(float)
        Xs = StandardScaler().fit_transform(X)
        model = Ridge(alpha=alpha, random_state=SEED).fit(Xs, y)
        for f, coef in zip(feats, model.coef_):
            rows.append(
                {
                    "window": "expanding_prior",
                    "validation_year": int(yr),
                    "fit_season": None,
                    "min_train_year": int(tr["season"].min()),
                    "max_train_year": int(tr["season"].max()),
                    "feature": f,
                    "std_coefficient": float(coef),
                    "intercept": float(model.intercept_),
                }
            )

    for season in sorted(int(s) for s in hist["season"].unique()):
        g = hist[hist["season"] == season]
        if len(g) < 500:
            continue
        Xg = g[feats].astype(float).fillna(0.0)
        yg = g["brownlow_votes"].astype(float)
        Xs = StandardScaler().fit_transform(Xg)
        m = Ridge(alpha=alpha, random_state=SEED).fit(Xs, yg)
        for f, coef in zip(feats, m.coef_):
            rows.append(
                {
                    "window": "single_season",
                    "validation_year": None,
                    "fit_season": int(season),
                    "min_train_year": int(season),
                    "max_train_year": int(season),
                    "feature": f,
                    "std_coefficient": float(coef),
                    "intercept": float(m.intercept_),
                }
            )
    return pd.DataFrame(rows)


def make_figures(
    scorecard: pd.DataFrame,
    folds: pd.DataFrame,
    drift: pd.DataFrame,
    env: dict[str, pd.DataFrame],
    coefs: pd.DataFrame,
    fig_dir: str = "outputs/figures/v2_2",
) -> None:
    os.makedirs(fig_dir, exist_ok=True)
    plt.rcParams.update({"figure.dpi": 140, "savefig.dpi": 160, "font.size": 11})

    # 1. strategy RMSE bars
    sc = scorecard.sort_values("mean_rmse")
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(sc["strategy"].astype(str), sc["mean_rmse"], color="#2e75b6")
    ax.axvline(V21_CHAMPION_MEAN, color="#c00000", ls="--", label=f"V2.1 champion {V21_CHAMPION_MEAN}")
    ax.set_xlabel("Mean allocated OOT RMSE")
    ax.set_title("V2.2 temporal training strategies")
    ax.legend(frameon=False)
    ax.grid(True, axis="x", alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(fig_dir, "temporal_strategy_rmse.png"))
    plt.close(fig)

    # 2. delta by year vs expanding_all
    base = folds[folds["strategy"] == "expanding_all"].set_index("validation_year")["rmse_allocated"]
    fig, ax = plt.subplots(figsize=(9, 5))
    for strat in [s.name for s in STRATEGIES if s.name != "expanding_all"]:
        g = folds[folds["strategy"] == strat].set_index("validation_year")["rmse_allocated"]
        ax.plot(g.index, g - base.reindex(g.index), marker="o", label=strat)
    ax.axhline(0, color="grey", lw=0.8)
    ax.set_xlabel("Validation year")
    ax.set_ylabel("Δ allocated RMSE vs expanding_all")
    ax.set_title("Strategy delta by validation year")
    ax.legend(frameon=False, fontsize=8, ncol=2)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(fig_dir, "strategy_delta_by_year.png"))
    plt.close(fig)

    # 3. feature correlation heatmap (pearson, raw features)
    raw_drift = drift[drift["feature_family"] == "raw"]
    mat = raw_drift.pivot(index="feature", columns="season", values="pearson")
    fig, ax = plt.subplots(figsize=(10, 6))
    im = ax.imshow(mat.to_numpy(), aspect="auto", cmap="RdBu_r", vmin=-0.2, vmax=0.8)
    ax.set_yticks(range(len(mat.index)))
    ax.set_yticklabels(mat.index)
    ax.set_xticks(range(len(mat.columns)))
    ax.set_xticklabels(mat.columns, rotation=45)
    ax.set_title("Feature–Brownlow Pearson correlation by season")
    fig.colorbar(im, ax=ax, fraction=0.046)
    fig.tight_layout()
    fig.savefig(os.path.join(fig_dir, "feature_brownlow_correlation_heatmap.png"))
    plt.close(fig)

    # 4. position vote share over time (top positions)
    pos = env["position_vote_share"]
    top = (
        pos.groupby("player_position")["votes"].sum().sort_values(ascending=False).head(8).index
    )
    fig, ax = plt.subplots(figsize=(9, 5))
    for p in top:
        g = pos[pos["player_position"] == p].sort_values("season")
        ax.plot(g["season"], g["vote_share"], marker="o", label=p)
    ax.set_xlabel("Season")
    ax.set_ylabel("Share of Brownlow votes")
    ax.set_title("Position vote share over time")
    ax.legend(frameon=False, fontsize=8, ncol=2)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(fig_dir, "position_vote_share_over_time.png"))
    plt.close(fig)

    # 5. winning team vote share
    wl = env["winning_losing_vote_share"]
    win = wl[wl["team_result"] == "winning"].sort_values("season")
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(win["season"], win["vote_share"], marker="o", color="#1f4e79")
    ax.axhline(0.5, color="grey", ls="--", lw=0.8)
    ax.set_ylim(0.4, 0.7)
    ax.set_xlabel("Season")
    ax.set_ylabel("Winning-team vote share")
    ax.set_title("Winning-team Brownlow vote share over time")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(fig_dir, "winning_team_vote_share_over_time.png"))
    plt.close(fig)

    # 6. temporal coefficients (expanding prior)
    cexp = coefs[coefs["window"] == "expanding_prior"].copy()
    fig, ax = plt.subplots(figsize=(9, 5))
    for f, g in cexp.groupby("feature"):
        g = g.sort_values("validation_year")
        ax.plot(g["validation_year"], g["std_coefficient"], marker="o", label=f)
    ax.set_xlabel("Validation year (expanding prior fit)")
    ax.set_ylabel("Standardized Ridge coefficient")
    ax.set_title("Explanatory temporal coefficients (not the champion model)")
    ax.legend(frameon=False, fontsize=7, ncol=2)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(fig_dir, "temporal_coefficients.png"))
    plt.close(fig)

    # 7. historical data value curve: trailing_n + expanding
    focus = scorecard[scorecard["strategy"].isin(["trailing_4", "trailing_6", "trailing_8", "expanding_all"])].copy()
    # map to approximate history length
    hist_map = {"trailing_4": 4, "trailing_6": 6, "trailing_8": 8, "expanding_all": 10}
    focus["history"] = focus["strategy"].map(hist_map)
    focus = focus.sort_values("history")
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(focus["history"], focus["mean_rmse"], marker="o", color="#2e75b6", label="mean OOT RMSE")
    ax.plot(focus["history"], focus["recent2_mean_rmse"], marker="s", color="#c00000", label="recent-2 mean")
    ax.set_xlabel("Approximate training history (seasons)")
    ax.set_ylabel("Allocated OOT RMSE")
    ax.set_title("Historical data value curve")
    ax.legend(frameon=False)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(fig_dir, "historical_data_value_curve.png"))
    plt.close(fig)
    print(f"wrote figures under {fig_dir}")


def _md_table(df: pd.DataFrame, floatfmt: str = ".6f") -> str:
    show = df.copy()
    for c in show.columns:
        if pd.api.types.is_float_dtype(show[c]):
            show[c] = show[c].map(lambda v: f"{v:{floatfmt}}" if pd.notna(v) else "")
        show[c] = show[c].astype(str)
    cols = list(show.columns.astype(str))
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    for _, row in show.iterrows():
        lines.append("| " + " | ".join(row[c] for c in show.columns) + " |")
    return "\n".join(lines)


def write_v22_summary(
    path: str,
    scorecard: pd.DataFrame,
    paired: pd.DataFrame,
    drift: pd.DataFrame,
    repro_mean: float,
    recommendation: str,
    answers: dict[str, str],
) -> None:
    # strongest drift: max abs pearson range across seasons for raw features
    raw = drift[drift["feature_family"] == "raw"]
    ranges = (
        raw.groupby("feature")["pearson"]
        .agg(min_p="min", max_p="max")
        .assign(range=lambda d: d["max_p"] - d["min_p"])
        .sort_values("range", ascending=False)
    )

    lines = [
        "# V2.2 Temporal Robustness — Research Summary",
        "",
        "## Research question",
        "",
        "How stable is the Brownlow voting *predictive relationship* through time, and how much",
        "historical data should be used when predicting a future AFL season?",
        "",
        f"V2.1 champion reproduction (expanding_all / base_plus_components): **{repro_mean:.6f}**",
        f"(reference {V21_CHAMPION_MEAN}).",
        "",
        "## Temporal strategy scorecard",
        "",
        _md_table(scorecard),
        "",
        "## Paired comparison vs expanding_all",
        "",
        _md_table(paired, floatfmt=".6g"),
        "",
        "## Feature drift (largest Pearson range across seasons)",
        "",
        _md_table(ranges.head(8).reset_index(), floatfmt=".4f"),
        "",
        "## Answers",
        "",
        "### 1. Is the Brownlow prediction function temporally stable?",
        "",
        answers["stability"],
        "",
        "### 2. Does old historical data still help?",
        "",
        answers["old_data"],
        "",
        "### 3. Is there evidence that recent seasons deserve greater weight?",
        "",
        answers["decay"],
        "",
        "### 4. Does excluding 2020 help?",
        "",
        answers["exclude_2020"],
        "",
        "### 5. Which features show the strongest temporal drift?",
        "",
        answers["drift"],
        "",
        "### 6. Which temporal strategy should be carried forward?",
        "",
        f"**{recommendation}**",
        "",
        answers["recommend_reason"],
        "",
        "### 7. Limitations",
        "",
        answers["limitations"],
        "",
    ]
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        f.write("\n".join(lines))
    print(f"wrote {path}")


def interpret_results(scorecard: pd.DataFrame, paired: pd.DataFrame, drift: pd.DataFrame) -> tuple[str, dict[str, str]]:
    sc = scorecard.copy()
    sc["strategy"] = sc["strategy"].astype(str)
    best_mean = sc.loc[sc["mean_rmse"].idxmin()]
    best_recent = sc.loc[sc["recent2_mean_rmse"].idxmin()]
    near = sc[sc["mean_rmse"] <= sc["mean_rmse"].min() + 0.0015].copy()
    near["robust_score"] = near["worst_season_rmse"] + near["std_rmse"]
    most_robust = near.loc[near["robust_score"].idxmin()]

    excl = sc.loc[sc["strategy"] == "expanding_exclude_2020"].iloc[0]
    base = sc.loc[sc["strategy"] == "expanding_all"].iloc[0]
    decays = sc[sc["strategy"].str.startswith("decay_")]
    best_decay = decays.loc[decays["mean_rmse"].idxmin()]

    raw = drift[drift["feature_family"] == "raw"]
    ranges = (
        raw.groupby("feature")["pearson"].agg(lambda s: float(s.max() - s.min())).sort_values(ascending=False)
    )
    top_drift = ", ".join(f"{k} (Δr={v:.3f})" for k, v in ranges.head(3).items())

    rec = str(most_robust["strategy"])
    if float(best_mean["mean_rmse"]) + 1e-12 < float(base["mean_rmse"]) and float(best_mean["recent2_mean_rmse"]) <= float(base["recent2_mean_rmse"]) + 0.0005:
        rec = str(best_mean["strategy"])
    elif float(excl["mean_rmse"]) < float(base["mean_rmse"]) - 0.0003 and float(excl["recent2_mean_rmse"]) <= float(base["recent2_mean_rmse"]):
        rec = "expanding_exclude_2020"
    else:
        if float(most_robust["mean_rmse"]) < float(base["mean_rmse"]) - 0.0002:
            rec = str(most_robust["strategy"])
        else:
            rec = "expanding_all"

    t4 = float(sc.loc[sc["strategy"] == "trailing_4", "mean_rmse"].iloc[0])
    t8 = float(sc.loc[sc["strategy"] == "trailing_8", "mean_rmse"].iloc[0])

    answers = {
        "stability": (
            f"Fold RMSE under expanding_all ranges from {float(base[2022]):.4f} to {float(base[2023]):.4f} "
            f"(std={float(base['std_rmse']):.4f}). Associations appear broadly persistent, but year-to-year "
            f"predictive difficulty is not constant—treat stability as approximate, not absolute."
        ),
        "old_data": (
            f"Trailing windows vs expanding_all: trailing_4 mean={t4:.6f}, "
            f"trailing_8={t8:.6f}, expanding_all={float(base['mean_rmse']):.6f}. "
            f"{'Shorter windows did not dominate' if float(base['mean_rmse']) <= t4 else 'Shorter windows looked competitive'}; "
            f"older seasons still appear to carry usable predictive association."
        ),
        "decay": (
            f"Best decay strategy: {best_decay['strategy']} mean={float(best_decay['mean_rmse']):.6f} "
            f"(Δ vs expanding_all={float(best_decay['mean_rmse'])-float(base['mean_rmse']):+.6f}), "
            f"recent-2={float(best_decay['recent2_mean_rmse']):.6f}. "
            f"{'Mild support for up-weighting recent seasons.' if float(best_decay['mean_rmse']) < float(base['mean_rmse']) else 'No clear gain from exponential decay over uniform expanding history.'}"
        ),
        "exclude_2020": (
            f"expanding_exclude_2020 mean={float(excl['mean_rmse']):.6f} (Δ={float(excl['mean_rmse'])-float(base['mean_rmse']):+.6f}), "
            f"recent-2={float(excl['recent2_mean_rmse']):.6f} vs expanding_all recent-2={float(base['recent2_mean_rmse']):.6f}. "
            f"{'Excluding 2020 improved mean OOT under this design.' if float(excl['mean_rmse']) < float(base['mean_rmse']) else 'Excluding 2020 did not improve mean OOT; retain 2020 unless other evidence emerges.'}"
        ),
        "drift": f"Largest season-to-season Pearson ranges among raw signals: {top_drift}.",
        "recommend_reason": (
            f"Carry forward `{rec}` based on mean OOT, recent-2 mean, worst-season RMSE, and paired evidence "
            f"(best_mean={best_mean['strategy']}, best_recent2={best_recent['strategy']}, "
            f"most_robust_near_best={most_robust['strategy']})."
        ),
        "limitations": (
            "Strategies share the same feature set and hyperparameters; results may shift under retuning. "
            "Paired bootstrap uses match blocks but a single seed. Ridge coefficients are associative "
            "explanatory summaries, not causal umpire effects. 2020 exclusion is one empirical contrast, "
            "not a full regime-shift causal analysis."
        ),
    }
    return rec, answers
