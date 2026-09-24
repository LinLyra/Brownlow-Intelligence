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

## Post-Event Evaluation

The sections above describe the **pre-event** frozen forecast. After the 2026 Brownlow count, those frozen predictions were scored as a true holdout. **No retraining or recalibration** was performed.

### Forecast integrity
- File: `outputs/final/2026_player_match_predictions.csv`
- SHA256: `5be4cc3381529c4bb88ca5c5197f5c5481b7e114f62a5c697ad61e71a1bfb5ad`
- Scale: 9,522 player-match rows · 207 matches · 1,242 allocated expected votes
- Prediction column: `allocated_expected_votes`

### Evaluation protocol
- Labels: realised 2026 Brownlow 3–2–1 votes, used **only** as evaluation targets
- Join: `match_id` + `player_id` (100% of positive-vote records)
- Primary metric: allocated player-match RMSE
- Uncertainty: match-level bootstrap (5,000 resamples, seed 42)

### Data provenance (actual votes)
Match-level actuals were **reconstructed** from the AFL Tables 2026 Brownlow vote matrix
(`https://afltables.com/afl/brownlow/brownlow2026.html`), retrieved **2026-09-24**.
This is **not** labelled as an AFL official machine-readable dump.
See `outputs/evaluation/2026_actual_vote_provenance.json` for source and file hashes.

### 2026 holdout results
| Metric | Value |
| --- | ---: |
| True holdout RMSE | 0.300540 |
| Match-bootstrap 95% CI | 0.2866–0.3145 |
| Historical rolling OOT RMSE | 0.355865 |
| Top-1 / actual 3-vote accuracy | 69.6% |
| Top-3 recall | 75.7% |
| Exact Top-3 set | 37.7% |
| Exact ordered 3–2–1 | 18.4% |
| Season Pearson | 0.968 |
| Season Spearman | 0.736 |
| Top-5 / Top-10 overlap | 80% / 80% |

Predicted champion: Nick Daicos (40.03 EV) · Actual champion: Nick Daicos (47 votes).

### Known misses (examples)
Largest underpredictions included Bailey Smith, Max Gawn, and Clayton Oliver.
Largest overpredictions included Caleb Daniel, Lachie Neale, and Wayne Milera.
Full lists: `outputs/evaluation/2026_largest_underpredictions.csv`,
`outputs/evaluation/2026_largest_overpredictions.csv`.

### Forecast compression
Actual 3-vote games carried a mean predicted EV of **1.93**. Prediction SD (**0.40**)
was narrower than actual vote SD (**0.54**), consistent with regression toward the mean /
limited tail calibration. Descriptive only — not a causal claim.

Full report: `outputs/evaluation/FINAL_2026_HOLDOUT_EVALUATION.md`
