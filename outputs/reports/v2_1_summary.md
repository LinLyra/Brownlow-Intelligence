# V2.1 Coach → Umpire Intelligence — Research Summary

## 1. Research question

How does coaches_votes translate into Brownlow votes, what do coaches observe beyond
box-score statistics, and does leakage-safe coach residual intelligence improve
out-of-time Brownlow point prediction?

## 2. Experimental design

- Rolling OOT folds: train seasons `< Y`, validate year `Y` for Y in 2022–2025.
- Coach model: CatBoostRegressor predicting `coaches_votes` from performance features
  (explicitly excluding `coaches_votes*` and `brownlow_votes`).
- Brownlow ablations A–F with identical CatBoost hyperparameters, seed=42, and capped-simplex allocation.
- Primary metric: mean allocated OOT RMSE.

## 3. Leakage-control methodology

- Expanding-year cross-fitting for coach expected votes: for season S, train only on seasons `< S`.
- Assertions: `max(train_season) < validation_season` for every coach and Brownlow fold.
- Early seasons with `< 3` prior seasons receive NaN coach residual features (no in-sample fill).
- Translation tables are descriptive only and are **not** used as predictive features.

## 4. Coach model OOT performance

| season | rmse | mae | correlation | n | resid_mean | resid_std |
| --- | --- | --- | --- | --- | --- | --- |
| 2022 | 1.092748 | 0.458832 | 0.828888 | 9108 | 0.017789 | 1.092603 |
| 2023 | 1.036583 | 0.439223 | 0.847012 | 9522 | 0.006698 | 1.036561 |
| 2024 | 1.035798 | 0.443535 | 0.847734 | 9522 | -0.024430 | 1.035509 |
| 2025 | 0.972405 | 0.410834 | 0.868991 | 9476 | -0.004607 | 0.972394 |

## 5. Brownlow ablation results

Reproduced base CatBoost mean allocated OOT RMSE: **0.358172** (reference ≈ 0.358172).

| experiment | 2022 | 2023 | 2024 | 2025 | mean_rmse | std_rmse | delta_vs_base | delta_vs_ref_0_358172 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| base | 0.317915 | 0.384456 | 0.371153 | 0.359162 | 0.358172 | 0.024904 | 0.000000 | -0.000000 |
| base_no_coach | 0.333037 | 0.394304 | 0.382714 | 0.366806 | 0.369215 | 0.023056 | 0.011043 | 0.011043 |
| base_plus_components | 0.315314 | 0.380906 | 0.370621 | 0.356620 | 0.355865 | 0.024949 | -0.002306 | -0.002307 |
| base_plus_expected | 0.316961 | 0.383451 | 0.373029 | 0.356887 | 0.357582 | 0.025290 | -0.000590 | -0.000590 |
| base_plus_residual | 0.316439 | 0.383152 | 0.371305 | 0.357776 | 0.357168 | 0.025171 | -0.001004 | -0.001004 |
| coach_intelligence | 0.316924 | 0.382385 | 0.368981 | 0.357013 | 0.356326 | 0.024455 | -0.001846 | -0.001846 |

Best experiment by mean RMSE: **base_plus_components** (0.355865),
delta vs base = -0.002306.

## 6. Residual analysis

Residual correlation matrix (Brownlow allocated residuals across ablations):

| model | base_prediction | base_no_coach_prediction | expected_coach_prediction_model | coach_residual_prediction_model | coach_components_prediction_model | coach_intelligence_prediction_model |
| --- | --- | --- | --- | --- | --- | --- |
| base_prediction | 1.0000 | 0.9479 | 0.9929 | 0.9945 | 0.9913 | 0.9920 |
| base_no_coach_prediction | 0.9479 | 1.0000 | 0.9500 | 0.9515 | 0.9531 | 0.9515 |
| expected_coach_prediction_model | 0.9929 | 0.9500 | 1.0000 | 0.9929 | 0.9945 | 0.9949 |
| coach_residual_prediction_model | 0.9945 | 0.9515 | 0.9929 | 1.0000 | 0.9931 | 0.9932 |
| coach_components_prediction_model | 0.9913 | 0.9531 | 0.9945 | 0.9931 | 1.0000 | 0.9953 |
| coach_intelligence_prediction_model | 0.9920 | 0.9515 | 0.9949 | 0.9932 | 0.9953 | 1.0000 |

Coach residual structure (OOT validation years):

| pair | correlation | n |
| --- | --- | --- |
| coach_residual_vs_brownlow_votes | 0.1566 | 37628 |
| coach_residual_vs_base_brownlow_residual | -0.0505 | 37628 |
| expected_coaches_vs_brownlow_votes | 0.6959 | 37628 |
| actual_coaches_vs_brownlow_votes | 0.6668 | 37628 |

## 7. Key descriptive findings

- Coaches votes range observed: 0–10.
- At coaches_votes=0, E[Brownlow]=0.0168.
- At coaches_votes=10, E[Brownlow]=2.3790.

## 8. Limitations

- Coach model uses the same engineered feature stack (minus coach/Brownlow targets); it is not an exhaustive causal model of coach judgement.
- NaN residual features in early seasons reduce training signal for 2015–2017 rows.
- Residual correlations are associative; they do not imply causal umpire–coach mechanisms.
- Single seed / fixed CatBoost hyperparameters; no full hyperparameter re-tune per ablation.

## 9. KEEP / REJECT recommendation

**KEEP**

Best challenger `base_plus_components` improves mean OOT RMSE by 0.00231 vs base with std change +0.00004.

_Generated 2026-09-20T14:40:21.759057+00:00_
