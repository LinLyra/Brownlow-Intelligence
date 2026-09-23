#!/usr/bin/env python
"""V2.1 Coach -> Umpire Intelligence experiment runner."""
from __future__ import annotations

import json
import os
import sys

sys.path.append("src")

import numpy as np
import pandas as pd

from brownlow.allocation import assert_feasible_predictions
from brownlow.coach_intelligence import (
    EXPERIMENT_PRED_COL,
    MIN_TRAIN_SEASONS,
    SEED,
    VAL_YEARS,
    attach_coach_features,
    build_translation_reports,
    coach_predict_feature_lists,
    cross_fit_coach_predictions,
    experiment_feature_sets,
)
from brownlow.data import audit_and_clean, load_data
from brownlow.diagnostics import (
    ablation_scorecard,
    coach_model_oot_metrics,
    coach_residual_structure,
    collect_run_metadata,
    decide_recommendation,
    grouped_residual_diagnostics,
    make_figures,
    residual_correlation_matrix,
    run_brownlow_ablations,
    write_summary,
)
from brownlow.features import build_features

REF_CATBOOST_MEAN = 0.358172
BASE_TOL = 0.002  # stop if base reproduction drifts materially


def main():
    np.random.seed(SEED)
    os.makedirs("outputs/reports", exist_ok=True)
    os.makedirs("outputs/oof", exist_ok=True)
    os.makedirs("outputs/cache", exist_ok=True)
    os.makedirs("outputs/figures/v2_1", exist_ok=True)

    print("=== Load + features ===")
    raw = load_data("data/raw/brownlow_datathon_dataset.csv")
    hist, future, _ = audit_and_clean(raw)
    all_clean = (
        pd.concat([hist, future], ignore_index=True)
        .sort_values(["match_date", "match_id", "player_id"])
        .reset_index(drop=True)
    )
    feat = build_features(all_clean)
    histf = feat[feat["season"] < 2026].copy()

    # ----- Part A: descriptive translation -----
    print("\n=== Part A: coach -> Brownlow translation ===")
    tables = build_translation_reports(histf)
    translation = tables["coach_to_brownlow_translation.csv"]

    # ----- Parts B–C: cross-fitted coach model -----
    print("\n=== Parts B–C: cross-fitted coach predictions ===")
    # Assert coach feature exclusion
    c_nums, c_cats = coach_predict_feature_lists(histf)
    assert "coaches_votes" not in c_nums + c_cats
    assert "brownlow_votes" not in c_nums + c_cats
    assert not any(str(c).startswith("coaches_votes") for c in c_nums)
    print(f"coach model features: n_num={len(c_nums)} n_cat={len(c_cats)}")

    coach_oof = cross_fit_coach_predictions(
        histf,
        cache_path="outputs/cache/cross_fitted_coach_predictions.csv",
        min_train_seasons=MIN_TRAIN_SEASONS,
        seed=SEED,
        force_recompute=False,
    )

    # Attach to Brownlow frame
    hist_ci = attach_coach_features(histf, coach_oof)

    # ----- Parts D–E: ablations -----
    print("\n=== Parts D–E: Brownlow ablations ===")
    feature_sets = experiment_feature_sets(hist_ci)
    for name, (nums, cats) in feature_sets.items():
        print(f"  {name}: {len(nums)}+{len(cats)} features")

    scores, oof = run_brownlow_ablations(hist_ci, feature_sets, val_years=VAL_YEARS, seed=SEED)
    scorecard = ablation_scorecard(scores, base_mean_ref=REF_CATBOOST_MEAN)

    base_mean = float(scorecard.loc[scorecard["experiment"] == "base", "mean_rmse"].iloc[0])
    print(f"\nBASE CatBoost mean allocated OOT RMSE = {base_mean:.6f} (ref {REF_CATBOOST_MEAN})")
    if abs(base_mean - REF_CATBOOST_MEAN) > BASE_TOL:
        raise SystemExit(
            f"STOP: base CatBoost mean RMSE {base_mean:.6f} differs from reference "
            f"{REF_CATBOOST_MEAN} by more than {BASE_TOL}. Investigate before comparing V2.1."
        )

    scores.to_csv("outputs/reports/v2_1_coach_ablation_fold_metrics.csv", index=False)
    scorecard.to_csv("outputs/reports/v2_1_coach_ablation.csv", index=False)
    oof.to_csv("outputs/oof/v2_1_coach_oof_predictions.csv", index=False)
    print("wrote outputs/reports/v2_1_coach_ablation.csv")
    print("wrote outputs/oof/v2_1_coach_oof_predictions.csv")
    print(scorecard.to_string(index=False))

    # Feasibility on each allocated prediction column
    for exp, col in EXPERIMENT_PRED_COL.items():
        if col not in oof.columns:
            continue
        tmp = oof[["season", "match_id", "player_id", col]].rename(columns={col: "prediction"})
        assert np.isfinite(tmp["prediction"]).all(), f"non-finite preds in {col}"
        assert_feasible_predictions(tmp)
    print("allocation feasibility OK for all ablation prediction columns")

    # ----- Parts F–G: residual + coach diagnostics -----
    print("\n=== Parts F–G: residual + coach diagnostics ===")
    coach_metrics = coach_model_oot_metrics(coach_oof, VAL_YEARS)
    coach_metrics.to_csv("outputs/reports/v2_1_coach_model_oot_metrics.csv", index=False)
    print(coach_metrics.to_string(index=False))

    resid_corr = residual_correlation_matrix(oof)
    resid_corr.to_csv("outputs/reports/v2_1_residual_correlations.csv")
    print("residual correlations:\n", resid_corr.round(4))

    structure = coach_residual_structure(coach_oof, oof, histf)
    structure.to_csv("outputs/reports/v2_1_coach_residual_structure.csv", index=False)
    print(structure.to_string(index=False))

    # Grouped residual diagnostics for base and best challenger
    for label, pred_col in [("base", "base_prediction"), ("coach_intelligence", "coach_intelligence_prediction_model")]:
        if pred_col not in oof.columns:
            continue
        groups = grouped_residual_diagnostics(oof, histf, pred_col=pred_col)
        for gname, gdf in groups.items():
            path = f"outputs/reports/v2_1_residuals_{label}_{gname}.csv"
            gdf.to_csv(path, index=False)

    # ----- Parts H–I: summary + figures -----
    print("\n=== Parts H–I: summary + figures ===")
    recommendation, rec_reason = decide_recommendation(scorecard, resid_corr)
    write_summary(
        "outputs/reports/v2_1_summary.md",
        coach_metrics=coach_metrics,
        scorecard=scorecard,
        resid_corr=resid_corr,
        structure=structure,
        translation=translation,
        recommendation=recommendation,
        rec_reason=rec_reason,
        baseline_mean=base_mean,
    )
    make_figures(translation, coach_oof, oof, scorecard, histf, fig_dir="outputs/figures/v2_1")

    # ----- Part K: metadata -----
    meta = collect_run_metadata(
        {
            "seed": SEED,
            "val_years": list(VAL_YEARS),
            "min_train_seasons": MIN_TRAIN_SEASONS,
            "ref_catboost_mean": REF_CATBOOST_MEAN,
            "base_mean_reproduced": base_mean,
            "recommendation": recommendation,
            "experiments": list(feature_sets.keys()),
        }
    )
    with open("outputs/reports/v2_1_run_metadata.json", "w") as f:
        json.dump(meta, f, indent=2)
    print("wrote outputs/reports/v2_1_run_metadata.json")

    print("\n=== V2.1 COMPLETE ===")
    print(f"Recommendation: {recommendation}")
    print(rec_reason)
    best = scorecard.loc[scorecard["mean_rmse"].idxmin()]
    print(
        f"Best={best['experiment']} mean_rmse={best['mean_rmse']:.6f} "
        f"delta_vs_base={best['delta_vs_base']:+.6f} delta_vs_ref={best['delta_vs_ref_0_358172']:+.6f}"
    )


if __name__ == "__main__":
    main()
