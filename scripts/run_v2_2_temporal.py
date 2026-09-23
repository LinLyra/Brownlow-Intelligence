#!/usr/bin/env python
"""V2.2 Temporal robustness / distribution-shift experiment."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

sys.path.append("src")

import numpy as np
import pandas as pd

from brownlow.coach_intelligence import (
    SEED,
    VAL_YEARS,
    attach_coach_features,
    cross_fit_coach_predictions,
)
from brownlow.data import audit_and_clean, load_data
from brownlow.features import build_features
from brownlow.temporal_analysis import (
    V21_CHAMPION_MEAN,
    V21_REPRO_TOL,
    feature_drift_table,
    interpret_results,
    make_figures,
    paired_comparison,
    run_temporal_strategies,
    temporal_linear_coefficients,
    temporal_scorecard,
    voting_environment_tables,
    write_v22_summary,
)


def main():
    np.random.seed(SEED)
    os.makedirs("outputs/reports", exist_ok=True)
    os.makedirs("outputs/oof", exist_ok=True)
    os.makedirs("outputs/figures/v2_2", exist_ok=True)

    print("=== Load + features (reuse V2.1 coach cache) ===")
    raw = load_data("data/raw/brownlow_datathon_dataset.csv")
    hist, future, _ = audit_and_clean(raw)
    all_clean = (
        pd.concat([hist, future], ignore_index=True)
        .sort_values(["match_date", "match_id", "player_id"])
        .reset_index(drop=True)
    )
    feat = build_features(all_clean)
    histf = feat[feat["season"] < 2026].copy()

    coach_oof = cross_fit_coach_predictions(
        histf,
        cache_path="outputs/cache/cross_fitted_coach_predictions.csv",
        force_recompute=False,
    )
    hist_ci = attach_coach_features(histf, coach_oof)

    print("\n=== Part A–B: temporal strategies ===")
    folds, oof = run_temporal_strategies(hist_ci, seed=SEED, val_years=VAL_YEARS)
    scorecard = temporal_scorecard(folds, champion_mean=V21_CHAMPION_MEAN)

    expanding_mean = float(scorecard.loc[scorecard["strategy"] == "expanding_all", "mean_rmse"].iloc[0])
    print(f"\nV2.1 champion reproduction (expanding_all) mean RMSE = {expanding_mean:.6f} (ref {V21_CHAMPION_MEAN})")
    if abs(expanding_mean - V21_CHAMPION_MEAN) > V21_REPRO_TOL:
        raise SystemExit(
            f"STOP: expanding_all mean {expanding_mean:.6f} differs from V2.1 champion "
            f"{V21_CHAMPION_MEAN} by more than {V21_REPRO_TOL}."
        )

    folds.to_csv("outputs/reports/v2_2_temporal_fold_metrics.csv", index=False)
    scorecard.to_csv("outputs/reports/v2_2_temporal_scorecard.csv", index=False)
    oof.to_csv("outputs/oof/v2_2_temporal_oof_predictions.csv", index=False)
    print(scorecard.to_string(index=False))

    print("\n=== Part C: paired OOF comparison ===")
    paired = paired_comparison(oof, baseline="expanding_all")
    paired.to_csv("outputs/reports/v2_2_paired_comparison.csv", index=False)
    print(paired.to_string(index=False))

    print("\n=== Part D: feature drift ===")
    drift = feature_drift_table(histf)
    drift.to_csv("outputs/reports/v2_2_feature_drift.csv", index=False)

    print("\n=== Part E: voting environment ===")
    env = voting_environment_tables(histf)
    # Combined descriptive export + normalized tables
    env["position_vote_share"].to_csv("outputs/reports/v2_2_position_vote_share.csv", index=False)
    env["winning_losing_vote_share"].to_csv("outputs/reports/v2_2_winning_losing_vote_share.csv", index=False)
    env["coaches_by_brownlow"].to_csv("outputs/reports/v2_2_coaches_by_brownlow.csv", index=False)
    env["performance_by_brownlow"].to_csv("outputs/reports/v2_2_performance_by_brownlow.csv", index=False)
    # Compact season-level environment summary
    win = env["winning_losing_vote_share"]
    win_pivot = win.pivot(index="season", columns="team_result", values="vote_share").reset_index()
    coach0 = env["coaches_by_brownlow"]
    coach_wide = coach0.pivot(index="season", columns="brownlow_votes", values="mean_coaches")
    coach_wide.columns = [f"mean_coaches_given_brownlow_{int(c)}" for c in coach_wide.columns]
    env_summary = win_pivot.merge(coach_wide.reset_index(), on="season", how="left")
    env_summary.to_csv("outputs/reports/v2_2_voting_environment.csv", index=False)

    print("\n=== Part F: explanatory temporal coefficients ===")
    coefs = temporal_linear_coefficients(histf)
    coefs.to_csv("outputs/reports/v2_2_temporal_coefficients.csv", index=False)

    print("\n=== Part G–I: figures + summary ===")
    make_figures(scorecard, folds, drift, env, coefs, fig_dir="outputs/figures/v2_2")
    recommendation, answers = interpret_results(scorecard, paired, drift)
    write_v22_summary(
        "outputs/reports/v2_2_summary.md",
        scorecard=scorecard,
        paired=paired,
        drift=drift,
        repro_mean=expanding_mean,
        recommendation=recommendation,
        answers=answers,
    )

    meta = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "seed": SEED,
        "v21_champion_ref": V21_CHAMPION_MEAN,
        "expanding_all_repro": expanding_mean,
        "recommendation": recommendation,
        "val_years": list(VAL_YEARS),
    }
    with open("outputs/reports/v2_2_run_metadata.json", "w") as f:
        json.dump(meta, f, indent=2)

    # Console report for the 10 required bullets
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

    print("\n=== V2.2 COMPLETE ===")
    print(f"1. V2.1 reproduction: {expanding_mean:.6f}")
    print("2. Scorecard written to outputs/reports/v2_2_temporal_scorecard.csv")
    print(f"3. Best mean: {best_mean['strategy']} ({best_mean['mean_rmse']:.6f})")
    print(f"4. Best recent-2: {best_recent['strategy']} ({best_recent['recent2_mean_rmse']:.6f})")
    print(f"5. Most robust (near-best): {most_robust['strategy']} (worst={most_robust['worst_season_rmse']:.6f})")
    print(f"6. Exclude-2020: mean={excl['mean_rmse']:.6f} Δ={excl['mean_rmse']-base['mean_rmse']:+.6f}")
    print(f"7. Best decay: {best_decay['strategy']} mean={best_decay['mean_rmse']:.6f} Δ={best_decay['mean_rmse']-base['mean_rmse']:+.6f}")
    print(f"8. See drift table + summary")
    print(f"9. Paired/bootstrap: outputs/reports/v2_2_paired_comparison.csv")
    print(f"10. Recommended for V2.3: {recommendation}")


if __name__ == "__main__":
    main()
