# Brownlow Intelligence — 2026 Holdout Evaluation

## 1. Evaluation Protocol

This audit scores the **frozen** 2026 player-match forecast against official Brownlow votes.

- Forecast artifact: `outputs/final/2026_player_match_predictions.csv`
- SHA256 (pre-evaluation): `5be4cc3381529c4bb88ca5c5197f5c5481b7e114f62a5c697ad61e71a1bfb5ad`
- Prediction column: `allocated_expected_votes`
- Labels: official 2026 Brownlow 3–2–1 allocations parsed from AFL Tables
  (`https://afltables.com/afl/brownlow/brownlow2026.html`), stored separately at
  `data/evaluation/brownlow_2026_actual_votes.csv`.

Repository MODEL_CARD and feature code treat 2026 Brownlow votes as unavailable for training.
This evaluation introduces those labels **only as holdout targets**. No retraining, recalibration,
or forecast overwrite was performed.

## 2. Forecast Integrity

| Item | Value |
| --- | --- |
| Rows | 9522 |
| Matches | 207 |
| Total allocated expected votes | 1242.000000 |
| SHA256 | `5be4cc3381529c4bb88ca5c5197f5c5481b7e114f62a5c697ad61e71a1bfb5ad` |
| Model | CatBoost `base_plus_components` |
| Historical rolling OOT RMSE | 0.355865 |
| Discrepancies vs prior audit | none |

Post-run SHA256 recheck: `5be4cc3381529c4bb88ca5c5197f5c5481b7e114f62a5c697ad61e71a1bfb5ad` (must match).

## 3. Primary Results

| Metric | Value |
| --- | --- |
| Historical OOT RMSE | 0.355865 |
| **2026 true holdout RMSE** | **0.300540** |
| 95% bootstrap CI (match-level) | [0.286577, 0.314487] |
| MAE | 0.099661 |
| MAE 95% CI | [0.094411, 0.104907] |
| MSE | 0.090324 |
| Mean prediction bias (p−y) | -2.866934e-15 |
| Pearson (player-match) | 0.8333 |
| Spearman (player-match) | 0.4205 |
| RMSE − historical | -0.055325 |
| Relative vs historical | -15.55% |

N = 9522 player-match rows, 207 matches.
Bootstrap: 5000 match-level resamples, seed 42.

## 4. Match-Level Ranking

| Metric | Rate / value |
| --- | --- |
| Top-1 = actual 3-vote | 0.696 |
| Top-3 recall (of actual vote getters) | 0.757 |
| Exact Top-3 set | 0.377 |
| Exact ordered 3–2–1 | 0.184 |
| Mean rank of actual 3 / 2 / 1 | 1.65 / 2.78 / 4.07 |
| MRR (actual 3-vote) | 0.816 |

Expected votes are continuous; these discrete ballot metrics are complementary to RMSE.

## 5. Season-Level Results

| Metric | Value |
| --- | --- |
| Pearson | 0.9675 |
| Spearman | 0.7360 |
| Season MAE | 0.716 |
| Season RMSE | 1.452 |
| Top-3 / 5 / 10 / 20 overlap | 1.00 / 0.80 / 0.80 / 0.85 |
| Predicted #1 | Nick Daicos (40.03 EV) |
| Actual #1 | Nick Daicos (47) |
| Champion ID match | True |

## 6. Where the Model Worked

- Player-match bias is near zero (-2.867e-15), consistent with the sum-to-6 allocator.
- Season-level rank correlation (Spearman 0.736) indicates the forecast ordering of season totals tracked actual polling order.
- Predicted champion (Nick Daicos) matched the actual medallist (Nick Daicos).
- Top-k set overlaps: Top-5 80%, Top-10 80%.

## 7. Where the Model Missed

- Actual 3-vote games: mean predicted EV = 1.932 (mean error -1.068), i.e. systematic compression on elite ballots.
- Exact ordered 3–2–1 rate is low (18.4%); continuous EV ranking rarely reproduces the discrete ballot order exactly.
- Largest season misses are listed in `2026_largest_underpredictions.csv` / `2026_largest_overpredictions.csv` (≥5 games).

## 8. Calibration

Expected-vote bin calibration (not probability calibration):

      bin    n  mean_predicted_ev  mean_actual_votes
0.00–0.10 8084           0.015362           0.002969
0.10–0.25  477           0.158004           0.113208
0.25–0.50  277           0.365405           0.418773
0.50–1.00  272           0.729548           0.750000
1.00–1.50  157           1.258789           1.496815
1.50–2.00  100           1.757363           2.010000
2.00–2.50  103           2.235904           2.495146
2.50–3.00   52           2.675553           2.903846

Weighted absolute calibration gap (ECE-like for expected votes): **0.0255**.

## 9. Error Analysis

- Residual vs coaches_votes (Spearman): 0.08706590128723388
- Residual vs coach_residual (Spearman): -0.13384437231716984
- Pred std / actual std: 0.3967 / 0.5360 (compression if pred_std < actual_std)
- Position breakdown: `2026_error_by_position.csv`
- Match-context RMSEs (if available): close 0.3129140259800594, mid 0.30183627570577015, blowout 0.2885566108936592
- Vote-getter share on winning team: 0.7761674718196457

These are associations, not causal claims.

## 10. Generalisation

Historical expanding_all allocated RMSE (from `v2_2_temporal_fold_metrics.csv`):

 year  allocated_rmse
 2022        0.315314
 2023        0.380906
 2024        0.370621
 2025        0.356620

- Historical mean (folds): 0.355865 (reported champion mean 0.355865)
- Historical range: [0.315314, 0.380906], sd 0.028808
- 2026 holdout: 0.300540
- Within historical range: False
- Z vs historical fold mean: -1.92

## 11. Limitations

- Labels sourced from AFL Tables round matrix, not a machine-readable AFL official dump; mapping uses player name + club + round → `player_id`/`match_id`.
- Match bootstrap CI treats matches exchangeable; it does not yield a paired test vs historical OOF folds.
- Season champion accuracy is descriptive only.
- Diagnostics use available covariates; missing context fields are noted rather than imputed.

## 12. Conclusion

The frozen 2026 forecast achieves holdout allocated RMSE **0.300540**
(95% CI [0.286577, 0.314487]), versus historical rolling OOT **0.355865**.
The difference is -0.055325 (-15.5%). Performance is
outside the 2022–2025 OOT fold range.
Season ranking agreement is meaningful (Spearman 0.736); discrete ballot exact-match rates remain lower, as expected for continuous expected-vote predictions.

No model update is recommended from this audit alone.
