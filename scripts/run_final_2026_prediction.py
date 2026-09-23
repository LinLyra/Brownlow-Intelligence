#!/usr/bin/env python
"""Final frozen-model 2026 Brownlow forecast + portfolio data exports."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

sys.path.append("src")

import numpy as np
import pandas as pd

from brownlow.allocation import assert_feasible_predictions
from brownlow.coach_intelligence import (
    SEED,
    attach_coach_features,
    cross_fit_coach_predictions,
    experiment_feature_sets,
)
from brownlow.data import KEYS, audit_and_clean, load_data
from brownlow.features import build_features
from brownlow.final_2026 import (
    V21_BASE_MEAN,
    V21_CHAMPION_MEAN,
    build_2026_coach_features,
    build_leaderboard,
    build_match_top3,
    build_player_profiles,
    distribution_shift_table,
    feature_coverage_table,
    load_v21_oof_for_error_plot,
    make_final_figures,
    opponent_team,
    player_display_name,
    write_model_card,
    write_readiness_markdown,
)
from brownlow.allocation import allocate_frame
from brownlow.models import CatBoostWrapper

np.random.seed(SEED)


def main():
    os.makedirs("outputs/reports", exist_ok=True)
    os.makedirs("outputs/final", exist_ok=True)
    os.makedirs("outputs/web", exist_ok=True)
    os.makedirs("outputs/figures/final", exist_ok=True)
    os.makedirs("outputs/submissions", exist_ok=True)

    # --- Verify frozen V2.1 champion from existing artifact (do not re-tune) ---
    abl = pd.read_csv("outputs/reports/v2_1_coach_ablation.csv")
    champ = float(abl.loc[abl["experiment"] == "base_plus_components", "mean_rmse"].iloc[0])
    print(f"V2.1 champion artifact mean RMSE = {champ:.6f} (ref {V21_CHAMPION_MEAN})")
    assert abs(champ - V21_CHAMPION_MEAN) < 1e-5, "V2.1 champion artifact drift"

    print("=== Load + feature build ===")
    raw = load_data("data/raw/brownlow_datathon_dataset.csv")
    hist, future, report = audit_and_clean(raw)
    # Explicit: 2026 Brownlow target must not be used anywhere.
    assert future["brownlow_votes"].isna().all(), "2026 brownlow_votes unexpectedly labelled"

    all_clean = (
        pd.concat([hist, future], ignore_index=True)
        .sort_values(["match_date", "match_id", "player_id"])
        .reset_index(drop=True)
    )
    feat = build_features(all_clean)
    train = feat[feat["season"] < 2026].copy()
    test = feat[feat["season"] == 2026].copy()
    assert int(train["season"].max()) < 2026
    assert set(test["season"].unique()) == {2026}

    print("=== Historical coach cross-fit cache (leakage-safe train features) ===")
    coach_hist = cross_fit_coach_predictions(
        train,
        cache_path="outputs/cache/cross_fitted_coach_predictions.csv",
        force_recompute=False,
    )
    train_ci = attach_coach_features(train, coach_hist)

    print("=== Final coach model for 2026 expected coaches ===")
    coach_2026 = build_2026_coach_features(train, test, seed=SEED)
    test_ci = attach_coach_features(test, coach_2026)
    # Document: actual coaches_votes available and used as in validation design
    assert test_ci["coaches_votes"].notna().all(), "2026 coaches_votes missing — cannot proceed"
    assert test_ci["expected_coaches_votes"].notna().all()
    assert test_ci["coach_residual"].notna().all()

    nums, cats = experiment_feature_sets(train_ci)["base_plus_components"]
    features = nums + cats
    print(f"Champion features: n_num={len(nums)} n_cat={len(cats)} total={len(features)}")
    for f in features:
        assert f in train_ci.columns and f in test_ci.columns, f"missing feature column {f}"

    # --- Phase 1–2 readiness + shift ---
    coverage = feature_coverage_table(train_ci, test_ci, features)
    coverage.to_csv("outputs/reports/final_2026_feature_coverage.csv", index=False)
    shift = distribution_shift_table(train_ci, test_ci, [f for f in features if f in train_ci.columns])
    shift.to_csv("outputs/reports/final_2026_distribution_shift.csv", index=False)

    critical_fail = coverage[(coverage["is_critical"]) & (coverage["status"].isin(["MISSING", "PARTIAL"]))]
    notes = [
        f"Players per 2026 match unique sizes: {sorted(test.groupby('match_id').size().unique().tolist())}",
        f"Suspicious distribution features (flagged): {int(shift['suspicious'].sum()) if len(shift) else 0}",
        "Actual 2026 coaches_votes present and used consistently with historical CV design.",
    ]
    if len(critical_fail):
        notes.append("CRITICAL FAILURES: " + ", ".join(critical_fail["feature"].tolist()))
        write_readiness_markdown(
            "outputs/reports/final_2026_readiness_audit.md",
            train_ci,
            test_ci,
            coverage,
            passed=False,
            notes=notes,
        )
        print("READINESS: FAIL")
        print(critical_fail[["feature", "status", "2026_missing_pct"]].to_string(index=False))
        raise SystemExit("STOP: critical 2026 features PARTIAL/MISSING — final prediction aborted.")

    write_readiness_markdown(
        "outputs/reports/final_2026_readiness_audit.md",
        train_ci,
        test_ci,
        coverage,
        passed=True,
        notes=notes,
    )
    print("READINESS: PASS")

    # --- Phase 4 final Brownlow model ---
    print("=== Train final Brownlow champion on all seasons < 2026 ===")
    print(f"train seasons={sorted(train_ci.season.unique())} n={len(train_ci)}")
    assert train_ci["brownlow_votes"].notna().all()
    model = CatBoostWrapper(seed=SEED)
    model.fit(train_ci[features], train_ci["brownlow_votes"], cat_cols=cats)

    test_ci = test_ci.copy()
    test_ci["raw_brownlow_prediction"] = model.predict(test_ci[features])
    assert np.isfinite(test_ci["raw_brownlow_prediction"]).all()
    # Do not use brownlow target
    assert "brownlow_votes" not in features

    allocated = allocate_frame(test_ci.rename(columns={"raw_brownlow_prediction": "raw_prediction"}), "raw_prediction", "capped_simplex")
    test_ci["allocated_expected_votes"] = allocated["prediction"].to_numpy()
    assert_feasible_predictions(test_ci.rename(columns={"allocated_expected_votes": "prediction"}))

    # --- Phase 5 player-match forecast ---
    ctx_cols = [
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
            "expected_coaches_votes",
            "coach_residual",
        ]
        if c in test_ci.columns
    ]
    pred = test_ci[
        [
            "season",
            "match_round",
            "match_id",
            "match_date",
            "player_team",
            "match_home_team",
            "match_away_team",
            "player_id",
            "player_first_name",
            "player_last_name",
            "player_position",
            "coaches_votes",
            "raw_brownlow_prediction",
            "allocated_expected_votes",
            *ctx_cols,
        ]
    ].copy()
    pred["opponent"] = opponent_team(pred)
    pred["player_name"] = player_display_name(pred)
    # QA
    assert pred.duplicated(["season", "match_id", "player_id"]).sum() == 0
    assert len(pred) == len(test)
    assert np.isfinite(pred["allocated_expected_votes"]).all()
    assert pred["allocated_expected_votes"].between(0, 3).all()
    match_sums = pred.groupby("match_id")["allocated_expected_votes"].sum()
    max_sum_err = float((match_sums - 6).abs().max())
    assert max_sum_err <= 1e-8, max_sum_err
    pred.to_csv("outputs/final/2026_player_match_predictions.csv", index=False)

    # --- Phase 6 leaderboard ---
    leaderboard = build_leaderboard(pred)
    leaderboard.to_csv("outputs/final/2026_predicted_brownlow_leaderboard.csv", index=False)
    total_votes = float(leaderboard["predicted_expected_votes"].sum())
    expected_total = 6.0 * pred["match_id"].nunique()
    assert abs(total_votes - expected_total) < 1e-6, (total_votes, expected_total)

    # --- Phase 7 match top3 ---
    top3 = build_match_top3(pred)
    top3.to_csv("outputs/final/2026_match_top3_predictions.csv", index=False)

    # --- Phase 8 profiles ---
    profiles = build_player_profiles(pred, leaderboard, top_n=30)
    with open("outputs/final/2026_player_profiles.json", "w") as f:
        json.dump(profiles, f, indent=2)
    # no fake image urls
    assert all(p.get("image_url") is None for p in profiles)

    # --- Phase 9 web JSON ---
    web_leaderboard = []
    for _, r in leaderboard.head(30).iterrows():
        web_leaderboard.append(
            {
                "predicted_rank": int(r["predicted_rank"]),
                "player_id": int(r["player_id"]),
                "player_name": r["player_name"],
                "team": r["team"],
                "position": r["position"],
                "games": int(r["games"]),
                "predicted_expected_votes": float(r["predicted_expected_votes"]),
                "total_coaches_votes": float(r["total_coaches_votes"]),
                "avg_expected_votes_per_game": float(r["avg_expected_votes_per_game"]),
            }
        )
    with open("outputs/web/leaderboard.json", "w") as f:
        json.dump({"title": "2026 Predicted Brownlow Leaderboard", "top_n": 30, "players": web_leaderboard}, f, indent=2)

    model_perf = {
        "original_base_rmse": V21_BASE_MEAN,
        "coach_intelligence_rmse": V21_CHAMPION_MEAN,
        "champion_experiment": "base_plus_components",
        "temporal_strategy": "expanding_all",
        "fold_rmse": {
            str(y): float(abl.loc[abl["experiment"] == "base_plus_components", str(y)].iloc[0])
            for y in [2022, 2023, 2024, 2025]
        },
        "metric": "mean allocated rolling OOT RMSE",
    }
    with open("outputs/web/model_performance.json", "w") as f:
        json.dump(model_perf, f, indent=2)

    with open("outputs/web/player_profiles.json", "w") as f:
        json.dump(profiles, f, indent=2)

    match_web = []
    for mid, g in top3.groupby("match_id"):
        match_web.append(
            {
                "match_id": int(mid),
                "match_round": int(g["match_round"].iloc[0]),
                "home": g["match_home_team"].iloc[0],
                "away": g["match_away_team"].iloc[0],
                "label": "Model-ranked Top 3",
                "top3": [
                    {
                        "model_rank": int(r["model_rank"]),
                        "player_name": r["player_name"],
                        "player_team": r["player_team"],
                        "allocated_expected_votes": float(r["allocated_expected_votes"]),
                    }
                    for _, r in g.sort_values("model_rank").iterrows()
                ],
            }
        )
    with open("outputs/web/match_predictions.json", "w") as f:
        json.dump(match_web, f, indent=2)

    methodology = {
        "project": "Brownlow Intelligence",
        "objective": "Predict expected Brownlow umpire votes at player-match level",
        "validation": "Rolling out-of-time validation (train < year, validate year for 2022–2025)",
        "coach_intelligence": "Leakage-safe expected coaches votes + residual components",
        "features": "Match-relative stats, context, lagged recognition, coaches votes, coach residuals",
        "model": "CatBoostRegressor with frozen V2.1 hyperparameters",
        "constraint": "Per-match capped-simplex allocation to sum=6 and bounds [0,3]",
        "final_training": "Full-history expanding_all on all labelled seasons before 2026",
        "verified_oot_rmse": {"base": V21_BASE_MEAN, "champion": V21_CHAMPION_MEAN},
    }
    with open("outputs/web/methodology_summary.json", "w") as f:
        json.dump(methodology, f, indent=2)

    # parse check
    for p in [
        "outputs/web/leaderboard.json",
        "outputs/web/model_performance.json",
        "outputs/web/player_profiles.json",
        "outputs/web/match_predictions.json",
        "outputs/web/methodology_summary.json",
        "outputs/final/2026_player_profiles.json",
    ]:
        with open(p) as fh:
            json.load(fh)

    # --- Phase 10 figures ---
    oof_err = load_v21_oof_for_error_plot()
    make_final_figures(leaderboard, pred, oof_err, fig_dir="outputs/figures/final")

    # --- Phase 11 model card ---
    write_model_card(
        "outputs/final/MODEL_CARD.md",
        feature_count=len(features),
        train_seasons=sorted(int(s) for s in train_ci["season"].unique()),
        n_train=len(train_ci),
    )

    # --- Submission form aligned to template ---
    template = pd.read_csv("data/raw/submission_template_v2.csv")
    keys = [
        "season",
        "match_round",
        "match_home_team",
        "match_away_team",
        "player_id",
        "player_first_name",
        "player_last_name",
        "player_team",
    ]
    sub = template.drop(columns=["brownlow_votes_prediction"]).merge(
        pred[keys + ["allocated_expected_votes"]], on=keys, how="left", validate="one_to_one"
    )
    sub = sub.rename(columns={"allocated_expected_votes": "brownlow_votes_prediction"})
    assert sub["brownlow_votes_prediction"].notna().all()
    sub_path = "outputs/submissions/Brownlow_Medal_Datathon_2026_Submission_Form_BrownlowIntelligence_Final.csv"
    sub.to_csv(sub_path, index=False)

    meta = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "readiness": "PASS",
        "n_2026_matches": int(pred["match_id"].nunique()),
        "n_2026_rows": int(len(pred)),
        "feature_count": len(features),
        "train_seasons": sorted(int(s) for s in train_ci.season.unique()),
        "total_expected_votes": total_votes,
        "expected_total_6x_matches": expected_total,
        "max_match_sum_abs_error": max_sum_err,
        "champion_oot_rmse": V21_CHAMPION_MEAN,
        "warnings": shift.loc[shift["suspicious"], "feature"].head(15).tolist() if len(shift) else [],
    }
    with open("outputs/reports/final_2026_run_metadata.json", "w") as f:
        json.dump(meta, f, indent=2)

    print("\n=== FINAL 2026 COMPLETE ===")
    print("READINESS: PASS")
    print(f"matches={meta['n_2026_matches']} rows={meta['n_2026_rows']} features={meta['feature_count']}")
    print(f"total expected votes={total_votes:.8f} vs 6*matches={expected_total:.1f} max_sum_err={max_sum_err:.2e}")
    print("\nTop 20 Predicted Brownlow Leaderboard (expected votes):")
    print(leaderboard.head(20)[["predicted_rank", "player_name", "team", "predicted_expected_votes"]].to_string(index=False))
    if meta["warnings"]:
        print("\nDistribution warnings (inspect):", meta["warnings"][:10])


if __name__ == "__main__":
    main()
