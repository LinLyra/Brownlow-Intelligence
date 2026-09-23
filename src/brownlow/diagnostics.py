"""Diagnostics, figures, and research summary for V2.1 Coach Intelligence."""
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
from sklearn.metrics import mean_absolute_error, mean_squared_error

from .allocation import allocate_frame, assert_feasible_predictions
from .coach_intelligence import EXPERIMENT_PRED_COL, VAL_YEARS, margin_bucket
from .metrics import diagnostics, rmse
from .models import CatBoostWrapper


def eval_fold(df: pd.DataFrame, raw_col: str = "raw_prediction", pred_col: str = "prediction") -> dict:
    """Raw + allocated metrics for one validation fold."""
    y = df["brownlow_votes"].to_numpy(dtype=float)
    raw = df[raw_col].to_numpy(dtype=float)
    assert np.isfinite(raw).all(), "non-finite raw predictions"
    d = diagnostics(df, pred_col=pred_col)
    d["rmse_raw"] = rmse(y, raw)
    d["rmse_allocated"] = d.pop("rmse")
    d["zero_vote_RMSE"] = d.pop("rmse_zero")
    d["poller_RMSE"] = d.pop("rmse_pollers")
    d["n_validation_rows"] = int(len(df))
    return d


def run_brownlow_ablations(
    df: pd.DataFrame,
    feature_sets: dict[str, tuple[list[str], list[str]]],
    val_years: tuple[int, ...] = VAL_YEARS,
    seed: int = 42,
    allocation: str = "capped_simplex",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Controlled CatBoost ablations with identical folds/hparams/allocation/seed."""
    score_rows: list[dict] = []
    oof_by_exp: dict[str, pd.DataFrame] = {}

    for exp_name, (nums, cats) in feature_sets.items():
        features = nums + cats
        print(f"\n=== ABLATION {exp_name} | n_features={len(features)} ===")
        year_parts: list[pd.DataFrame] = []
        for yr in val_years:
            tr = df[df["season"] < yr]
            va = df[df["season"] == yr].copy()
            assert int(tr["season"].max()) < yr, f"Brownlow fold leakage: max(train)={tr.season.max()} >= {yr}"
            print(f"  fold {yr}: max(train_season)={int(tr.season.max())} < val={yr}  n_train={len(tr)} n_val={len(va)}")

            model = CatBoostWrapper(seed=seed)
            model.fit(tr[features], tr["brownlow_votes"], cat_cols=cats)
            va["raw_prediction"] = model.predict(va[features])
            assert np.isfinite(va["raw_prediction"]).all()
            va = allocate_frame(va, "raw_prediction", allocation)
            assert_feasible_predictions(va)

            metrics = eval_fold(va)
            score_rows.append({"experiment": exp_name, "validation_year": yr, **metrics})

            pred_name = EXPERIMENT_PRED_COL[exp_name]
            year_parts.append(
                va[["season", "match_id", "player_id", "player_first_name", "player_last_name", "brownlow_votes"]]
                .rename(columns={"brownlow_votes": "actual_brownlow_votes"})
                .assign(**{pred_name: va["prediction"].to_numpy(), f"{pred_name}_raw": va["raw_prediction"].to_numpy()})
            )
        oof_by_exp[exp_name] = pd.concat(year_parts, ignore_index=True)

    scores = pd.DataFrame(score_rows)

    # Wide OOF: one row per player-match, one prediction column family per experiment
    oof = None
    meta = ["season", "match_id", "player_id", "player_first_name", "player_last_name", "actual_brownlow_votes"]
    for exp_name, part in oof_by_exp.items():
        if oof is None:
            oof = part
        else:
            add_cols = [c for c in part.columns if c not in meta]
            oof = oof.merge(part[["season", "match_id", "player_id"] + add_cols], on=["season", "match_id", "player_id"], how="outer", validate="one_to_one")

    assert oof is not None
    dup = oof.duplicated(["season", "match_id", "player_id"]).sum()
    assert dup == 0, f"OOF duplicate keys: {dup}"
    return scores, oof


def ablation_scorecard(scores: pd.DataFrame, base_mean_ref: float = 0.358172) -> pd.DataFrame:
    """Pivot allocated RMSE by year + mean/std/delta_vs_base."""
    piv = scores.pivot(index="experiment", columns="validation_year", values="rmse_allocated")
    piv = piv.reindex(columns=list(VAL_YEARS))
    out = piv.reset_index()
    means = scores.groupby("experiment")["rmse_allocated"].mean()
    stds = scores.groupby("experiment")["rmse_allocated"].std(ddof=0)
    out["mean_rmse"] = out["experiment"].map(means)
    out["std_rmse"] = out["experiment"].map(stds)
    base_mean = float(means.get("base", base_mean_ref))
    out["delta_vs_base"] = out["mean_rmse"] - base_mean
    out["delta_vs_ref_0_358172"] = out["mean_rmse"] - base_mean_ref
    return out


def coach_model_oot_metrics(coach_oof: pd.DataFrame, val_years: tuple[int, ...] = VAL_YEARS) -> pd.DataFrame:
    rows = []
    for yr in val_years:
        g = coach_oof[coach_oof["season"] == yr]
        y = g["actual_coaches_votes"].to_numpy(dtype=float)
        p = g["expected_coaches_votes"].to_numpy(dtype=float)
        mask = np.isfinite(y) & np.isfinite(p)
        y, p = y[mask], p[mask]
        rows.append(
            {
                "season": yr,
                "rmse": float(np.sqrt(mean_squared_error(y, p))),
                "mae": float(mean_absolute_error(y, p)),
                "correlation": float(np.corrcoef(y, p)[0, 1]) if len(y) > 1 else np.nan,
                "n": int(len(y)),
                "resid_mean": float((y - p).mean()),
                "resid_std": float((y - p).std()),
            }
        )
    return pd.DataFrame(rows)


def residual_correlation_matrix(oof: pd.DataFrame, pred_cols: list[str] | None = None) -> pd.DataFrame:
    cols = pred_cols or [c for c in EXPERIMENT_PRED_COL.values() if c in oof.columns]
    resid = {c: oof["actual_brownlow_votes"].to_numpy(dtype=float) - oof[c].to_numpy(dtype=float) for c in cols}
    R = pd.DataFrame(resid)
    return R.corr()


def grouped_residual_diagnostics(
    oof: pd.DataFrame,
    hist: pd.DataFrame,
    pred_col: str = "base_prediction",
) -> dict[str, pd.DataFrame]:
    """Residual diagnostics for one model, grouped by vote / position / coaches / result."""
    keys = ["season", "match_id", "player_id"]
    meta_cols = keys + ["brownlow_votes", "coaches_votes", "player_position", "player_team", "match_winner", "match_margin"]
    meta = hist[meta_cols].copy()
    meta["team_won"] = (meta["player_team"] == meta["match_winner"]).astype("int8")
    meta["margin_bucket"] = margin_bucket(meta["match_margin"])
    meta["coaches_votes_bucket"] = meta["coaches_votes"].fillna(-1).astype(int)

    m = oof.merge(meta, on=keys, how="left", validate="one_to_one")
    m["residual"] = m["actual_brownlow_votes"] - m[pred_col]

    def _agg(group_col: str) -> pd.DataFrame:
        g = m.groupby(group_col, observed=True)
        return (
            g["residual"]
            .agg(n="count", mean="mean", std="std", mae=lambda s: s.abs().mean(), rmse=lambda s: np.sqrt(np.mean(s**2)))
            .reset_index()
        )

    return {
        "by_brownlow_vote": _agg("actual_brownlow_votes"),
        "by_position": _agg("player_position"),
        "by_coaches_votes": _agg("coaches_votes_bucket"),
        "by_team_result": _agg("team_won"),
    }


def coach_residual_structure(coach_oof: pd.DataFrame, oof: pd.DataFrame, hist: pd.DataFrame) -> pd.DataFrame:
    """Does coach_residual contain structured Brownlow information OOT?"""
    keys = ["season", "match_id", "player_id"]
    m = (
        coach_oof[keys + ["coach_residual", "actual_coaches_votes", "expected_coaches_votes"]]
        .merge(
            oof[keys + ["actual_brownlow_votes", "base_prediction"]],
            on=keys,
            how="inner",
            validate="one_to_one",
        )
    )
    m = m[m["season"].isin(VAL_YEARS) & m["coach_residual"].notna()].copy()
    m["base_brownlow_residual"] = m["actual_brownlow_votes"] - m["base_prediction"]
    rows = [
        {
            "pair": "coach_residual_vs_brownlow_votes",
            "correlation": float(m["coach_residual"].corr(m["actual_brownlow_votes"])),
            "n": int(len(m)),
        },
        {
            "pair": "coach_residual_vs_base_brownlow_residual",
            "correlation": float(m["coach_residual"].corr(m["base_brownlow_residual"])),
            "n": int(len(m)),
        },
        {
            "pair": "expected_coaches_vs_brownlow_votes",
            "correlation": float(m["expected_coaches_votes"].corr(m["actual_brownlow_votes"])),
            "n": int(len(m)),
        },
        {
            "pair": "actual_coaches_vs_brownlow_votes",
            "correlation": float(m["actual_coaches_votes"].corr(m["actual_brownlow_votes"])),
            "n": int(len(m)),
        },
    ]
    return pd.DataFrame(rows)


def make_figures(
    translation: pd.DataFrame,
    coach_oof: pd.DataFrame,
    oof: pd.DataFrame,
    scorecard: pd.DataFrame,
    hist: pd.DataFrame,
    fig_dir: str = "outputs/figures/v2_1",
) -> None:
    os.makedirs(fig_dir, exist_ok=True)
    plt.rcParams.update({"figure.dpi": 140, "savefig.dpi": 160, "font.size": 11})

    # 1. coaches_votes vs E[Brownlow]
    t = translation.sort_values("coaches_votes")
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(t["coaches_votes"], t["E_brownlow"], marker="o", color="#1f4e79")
    for _, r in t.iterrows():
        ax.annotate(f"n={int(r['n'])}", (r["coaches_votes"], r["E_brownlow"]), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=8)
    ax.set_xlabel("Coaches votes")
    ax.set_ylabel("Historical E[Brownlow votes]")
    ax.set_title("Coach votes vs expected Brownlow votes")
    ax.set_xticks(t["coaches_votes"])
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(fig_dir, "coach_votes_vs_expected_brownlow.png"))
    plt.close(fig)

    # 2. Probability mass by coaches_votes
    fig, ax = plt.subplots(figsize=(9, 5))
    x = t["coaches_votes"].to_numpy()
    bottom = np.zeros(len(t))
    colors = ["#d9d9d9", "#9dc3e6", "#2e75b6", "#1f4e79"]
    for b, col in zip((0, 1, 2, 3), colors):
        h = t[f"P_brownlow_{b}"].to_numpy()
        ax.bar(x, h, bottom=bottom, label=f"P(Brownlow={b})", color=col)
        bottom += h
    ax.set_xlabel("Coaches votes")
    ax.set_ylabel("Probability")
    ax.set_title("Brownlow vote probability by coaches votes")
    ax.set_xticks(x)
    ax.legend(frameon=False)
    ax.set_ylim(0, 1.05)
    fig.tight_layout()
    fig.savefig(os.path.join(fig_dir, "brownlow_probability_by_coach_votes.png"))
    plt.close(fig)

    # 3. coach residual vs brownlow residual (OOT val years)
    keys = ["season", "match_id", "player_id"]
    m = coach_oof.merge(oof[keys + ["actual_brownlow_votes", "base_prediction"]], on=keys, how="inner")
    m = m[m["season"].isin(VAL_YEARS) & m["coach_residual"].notna()].copy()
    m["brownlow_residual"] = m["actual_brownlow_votes"] - m["base_prediction"]
    # subsample for readability
    sample = m.sample(n=min(8000, len(m)), random_state=42)
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.scatter(sample["coach_residual"], sample["brownlow_residual"], s=6, alpha=0.25, color="#1f4e79")
    ax.axhline(0, color="grey", lw=0.8)
    ax.axvline(0, color="grey", lw=0.8)
    corr = float(m["coach_residual"].corr(m["brownlow_residual"]))
    ax.set_xlabel("Coach residual (actual − expected coaches votes)")
    ax.set_ylabel("Base Brownlow residual (actual − allocated)")
    ax.set_title(f"Coach residual vs Brownlow residual (OOT)\ncorr={corr:.3f}")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(fig_dir, "coach_residual_vs_brownlow_residual.png"))
    plt.close(fig)

    # 4. RMSE comparison
    fig, ax = plt.subplots(figsize=(9, 5))
    sc = scorecard.sort_values("mean_rmse")
    ax.barh(sc["experiment"], sc["mean_rmse"], color="#2e75b6")
    ax.axvline(0.358172, color="#c00000", ls="--", label="CatBoost ref 0.358172")
    ax.set_xlabel("Mean allocated OOT RMSE")
    ax.set_title("V2.1 Brownlow ablation: mean OOT RMSE")
    ax.legend(frameon=False)
    ax.grid(True, axis="x", alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(fig_dir, "v2_1_model_rmse_comparison.png"))
    plt.close(fig)

    # 5. Coach-umpire disagreement by position
    meta = hist[["season", "match_id", "player_id", "player_position", "brownlow_votes", "coaches_votes"]].copy()
    d = coach_oof.merge(meta, on=keys, how="left")
    d = d[d["season"].isin(VAL_YEARS) & d["coach_residual"].notna()].copy()
    # disagreement: high coach residual but low/high brownlow — use |coach_residual| mean by position
    by_pos = (
        d.groupby("player_position", observed=True)
        .agg(mean_abs_coach_resid=("coach_residual", lambda s: float(s.abs().mean())), n=("coach_residual", "size"))
        .reset_index()
        .sort_values("mean_abs_coach_resid", ascending=False)
    )
    by_pos = by_pos[by_pos["n"] >= 200].head(15)
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.barh(by_pos["player_position"], by_pos["mean_abs_coach_resid"], color="#1f4e79")
    ax.set_xlabel("Mean |coach residual| (OOT)")
    ax.set_title("Coach–performance disagreement by position")
    ax.invert_yaxis()
    ax.grid(True, axis="x", alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(fig_dir, "coach_umpire_disagreement_by_position.png"))
    plt.close(fig)
    print(f"wrote figures under {fig_dir}")


def decide_recommendation(scorecard: pd.DataFrame, resid_corr: pd.DataFrame) -> tuple[str, str]:
    """Evidence-based KEEP / KEEP AS ENSEMBLE CANDIDATE / REJECT."""
    base = scorecard.loc[scorecard["experiment"] == "base"].iloc[0]
    challengers = scorecard[scorecard["experiment"] != "base"].copy()
    best = challengers.loc[challengers["mean_rmse"].idxmin()]
    delta = float(best["mean_rmse"] - base["mean_rmse"])
    # Material improvement threshold relative to RMSE scale (~0.36)
    material = 0.001  # 0.1% absolute RMSE
    instability = float(best["std_rmse"] - base["std_rmse"])

    # Residual diversity: mean off-diagonal corr of best challenger vs base
    pred_map = EXPERIMENT_PRED_COL
    best_col = pred_map.get(best["experiment"])
    base_col = pred_map["base"]
    diversity = None
    if best_col in resid_corr.columns and base_col in resid_corr.columns:
        diversity = float(resid_corr.loc[base_col, best_col]) if base_col in resid_corr.index else None

    if delta < -material and instability < 0.01:
        return (
            "KEEP",
            f"Best challenger `{best['experiment']}` improves mean OOT RMSE by {-delta:.5f} "
            f"vs base with std change {instability:+.5f}.",
        )
    if diversity is not None and diversity < 0.95 and abs(delta) < material:
        return (
            "KEEP AS ENSEMBLE CANDIDATE",
            f"Best challenger `{best['experiment']}` mean RMSE delta={delta:+.5f} (negligible) "
            f"but residual corr vs base={diversity:.3f}, suggesting ensemble diversity.",
        )
    if delta < 0 and diversity is not None and diversity < 0.97:
        return (
            "KEEP AS ENSEMBLE CANDIDATE",
            f"Modest RMSE gain ({delta:+.5f}) with residual corr vs base={diversity:.3f}.",
        )
    return (
        "REJECT",
        f"No material predictive gain (best delta={delta:+.5f} from `{best['experiment']}`) "
        f"and insufficient residual diversity evidence to justify complexity.",
    )


def _md_table(df: pd.DataFrame, floatfmt: str = ".6f") -> str:
    """Minimal markdown table without optional tabulate dependency."""
    show = df.copy()
    for c in show.columns:
        if pd.api.types.is_float_dtype(show[c]):
            show[c] = show[c].map(lambda v: (f"{v:{floatfmt}}" if pd.notna(v) else ""))
    cols = list(show.columns.astype(str))
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    for _, row in show.iterrows():
        lines.append("| " + " | ".join(str(row[c]) for c in show.columns) + " |")
    return "\n".join(lines)


def write_summary(
    path: str,
    coach_metrics: pd.DataFrame,
    scorecard: pd.DataFrame,
    resid_corr: pd.DataFrame,
    structure: pd.DataFrame,
    translation: pd.DataFrame,
    recommendation: str,
    rec_reason: str,
    baseline_mean: float,
) -> None:
    best = scorecard.loc[scorecard["mean_rmse"].idxmin()]
    e0 = float(translation.loc[translation.coaches_votes == 0, "E_brownlow"].iloc[0])
    e10_line = ""
    if (translation.coaches_votes == 10).any():
        e10 = float(translation.loc[translation.coaches_votes == 10, "E_brownlow"].iloc[0])
        e10_line = f"- At coaches_votes=10, E[Brownlow]={e10:.4f}."
    lines = [
        "# V2.1 Coach → Umpire Intelligence — Research Summary",
        "",
        "## 1. Research question",
        "",
        "How does coaches_votes translate into Brownlow votes, what do coaches observe beyond",
        "box-score statistics, and does leakage-safe coach residual intelligence improve",
        "out-of-time Brownlow point prediction?",
        "",
        "## 2. Experimental design",
        "",
        "- Rolling OOT folds: train seasons `< Y`, validate year `Y` for Y in 2022–2025.",
        "- Coach model: CatBoostRegressor predicting `coaches_votes` from performance features",
        "  (explicitly excluding `coaches_votes*` and `brownlow_votes`).",
        "- Brownlow ablations A–F with identical CatBoost hyperparameters, seed=42, and capped-simplex allocation.",
        "- Primary metric: mean allocated OOT RMSE.",
        "",
        "## 3. Leakage-control methodology",
        "",
        "- Expanding-year cross-fitting for coach expected votes: for season S, train only on seasons `< S`.",
        "- Assertions: `max(train_season) < validation_season` for every coach and Brownlow fold.",
        "- Early seasons with `< 3` prior seasons receive NaN coach residual features (no in-sample fill).",
        "- Translation tables are descriptive only and are **not** used as predictive features.",
        "",
        "## 4. Coach model OOT performance",
        "",
        _md_table(coach_metrics),
        "",
        "## 5. Brownlow ablation results",
        "",
        f"Reproduced base CatBoost mean allocated OOT RMSE: **{baseline_mean:.6f}** (reference ≈ 0.358172).",
        "",
        _md_table(scorecard),
        "",
        f"Best experiment by mean RMSE: **{best['experiment']}** ({best['mean_rmse']:.6f}),",
        f"delta vs base = {best['delta_vs_base']:+.6f}.",
        "",
        "## 6. Residual analysis",
        "",
        "Residual correlation matrix (Brownlow allocated residuals across ablations):",
        "",
        _md_table(resid_corr.reset_index().rename(columns={"index": "model"}), floatfmt=".4f"),
        "",
        "Coach residual structure (OOT validation years):",
        "",
        _md_table(structure, floatfmt=".4f"),
        "",
        "## 7. Key descriptive findings",
        "",
        f"- Coaches votes range observed: {int(translation.coaches_votes.min())}–{int(translation.coaches_votes.max())}.",
        f"- At coaches_votes=0, E[Brownlow]={e0:.4f}.",
        e10_line,
        "",
        "## 8. Limitations",
        "",
        "- Coach model uses the same engineered feature stack (minus coach/Brownlow targets); it is not an exhaustive causal model of coach judgement.",
        "- NaN residual features in early seasons reduce training signal for 2015–2017 rows.",
        "- Residual correlations are associative; they do not imply causal umpire–coach mechanisms.",
        "- Single seed / fixed CatBoost hyperparameters; no full hyperparameter re-tune per ablation.",
        "",
        "## 9. KEEP / REJECT recommendation",
        "",
        f"**{recommendation}**",
        "",
        rec_reason,
        "",
        f"_Generated {datetime.now(timezone.utc).isoformat()}_",
        "",
    ]
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        f.write("\n".join([ln for ln in lines if ln is not None]))
    print(f"wrote {path}")


def collect_run_metadata(config: dict[str, Any]) -> dict[str, Any]:
    import sys
    import subprocess

    def _ver(mod):
        try:
            m = __import__(mod)
            return getattr(m, "__version__", "unknown")
        except Exception:
            return None

    commit = None
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        commit = None

    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "pandas": _ver("pandas"),
        "numpy": _ver("numpy"),
        "catboost": _ver("catboost"),
        "lightgbm": _ver("lightgbm"),
        "sklearn": _ver("sklearn"),
        "git_commit": commit,
        "config": config,
    }
