# 2026 Leakage Audit

## Question
Were 2026 actual Brownlow labels isolated from model development and the frozen forecast?

## Repository evidence

1. Frozen forecast file `outputs/final/2026_player_match_predictions.csv` was generated as a pre-result inference artifact
   (see `outputs/final/MODEL_CARD.md`): *"The 2026 Brownlow target is unavailable and was not used."*
2. Training protocol in MODEL_CARD: CatBoost trained on labelled seasons **before 2026**.
3. Feature construction (`src/brownlow/features.py`):
   - `brownlow_votes` is in `ID_COLS` / `DROP_ALWAYS` and is **not** a predictive feature.
   - Lagged recognition features use only **shifted** past votes (`cumsum().shift(1)`).
4. Coach Intelligence (`src/brownlow/coach_intelligence.py` / `final_2026.py`):
   - Explicit asserts exclude `brownlow_votes` from coach and Brownlow feature lists.
5. Datathon raw file still has `brownlow_votes` all-null for season 2026 at evaluation start
   (labels for this audit were obtained separately from AFL Tables after the count).

## Contaminating variables checked against frozen prediction columns

Frozen prediction CSV columns include performance stats and coach signals available pre-count,
plus `allocated_expected_votes`. They do **not** include:
- `brownlow_votes`
- `actual_brownlow_votes`
- 2026 final season Brownlow totals
- post-count variables

## Conclusion

**Supported by repository artifacts:** the frozen 2026 forecast was produced without 2026 Brownlow
labels as features or as a model-selection target. This evaluation introduces official 2026 votes
**only as held-out labels**.

This audit does **not** claim stronger provenance than git/history + MODEL_CARD + code asserts provide.
It does not independently prove the chronological wall-clock freeze relative to the Brownlow telecast;
it verifies that the checked artifacts treat 2026 actuals as unused for prediction.
