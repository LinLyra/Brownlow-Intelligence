# MODEL CARD — Brownlow Intelligence

## Brownlow Intelligence
Predicting and Understanding Human Judgement in Elite Sport — Point Prediction Engine.

## Objective
Predict **expected Brownlow Medal votes** for each player-match, then allocate predictions within each match so that:
- each player prediction is in `[0, 3]`
- each match sums to exactly `6`

## Data
Historical labelled AFL player-match observations (seasons 2015–2025; n=96764) and the official 2026 prediction rows.

## Prediction target
`brownlow_votes` (umpire votes). The 2026 Brownlow target is unavailable and was not used.

## Validation design
Rolling out-of-time folds:
- train seasons `< Y`, validate year `Y` for Y ∈ {2022, 2023, 2024, 2025}
Primary metric: mean allocated OOT RMSE.

## Final feature families
- Match-relative performance features (z-scores, ranks, shares, percentiles)
- Team shares / context (result, margin buckets, thresholds)
- Lagged player recognition history (strictly past matches only)
- Raw `coaches_votes` (available in both historical and 2026 official rows)
- Leakage-safe Coach Intelligence residuals (`expected_coaches_votes` and residual components)

Feature count used by frozen champion: **178**

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
Euclidean capped-simplex projection per match onto `{x : sum x = 6, 0 ≤ x ≤ 3}`.

## Historical OOT performance (verified)
- Original CatBoost base mean allocated OOT RMSE: **0.358172**
- V2.1 champion (`base_plus_components`) mean allocated OOT RMSE: **0.355865**

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
