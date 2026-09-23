# Final 2026 Prediction Readiness Audit

**Result: PASS**

Generated: 2026-09-22T11:14:17.803351+00:00

## Dataset counts

- Historical labelled rows: 96764
- 2026 prediction rows: 9522
- Historical matches: 2153
- 2026 matches: 207
- Players per 2026 match: [46]
- Duplicate player-match keys (hist): 0
- Duplicate player-match keys (2026): 0
- Missing match_id (2026): 0
- Missing player_id (2026): 0
- Missing player names (2026): 0
- Missing team/opponent fields (2026): 0

## Coaches votes availability

Actual `coaches_votes` is present in the official 2026 prediction dataset (0% missing).
This matches the historical validation design, where coaches_votes is an observable
input feature (not the Brownlow target). Final inference therefore uses actual 2026
coaches_votes together with leakage-safe expected_coaches_votes from a coach model
trained only on seasons < 2026.

## Critical feature status

- `match_margin`: **READY** (hist miss=0.000%, 2026 miss=0.000%)
- `coaches_votes`: **READY** (hist miss=0.000%, 2026 miss=0.000%)
- `supercoach_score`: **READY** (hist miss=0.000%, 2026 miss=0.000%)
- `afl_fantasy_score`: **READY** (hist miss=0.000%, 2026 miss=0.000%)
- `rating_points`: **READY** (hist miss=0.000%, 2026 miss=0.000%)
- `disposals`: **READY** (hist miss=0.000%, 2026 miss=0.000%)
- `goals`: **READY** (hist miss=0.000%, 2026 miss=0.000%)
- `tackles`: **READY** (hist miss=0.000%, 2026 miss=0.000%)
- `clearances`: **READY** (hist miss=0.000%, 2026 miss=0.000%)
- `contested_possessions`: **READY** (hist miss=0.000%, 2026 miss=0.000%)
- `score_involvements`: **READY** (hist miss=0.000%, 2026 miss=0.000%)
- `metres_gained`: **READY** (hist miss=0.000%, 2026 miss=0.000%)
- `team_won`: **READY** (hist miss=0.000%, 2026 miss=0.000%)
- `close_game`: **READY** (hist miss=0.000%, 2026 miss=0.000%)
- `coaches_votes__match_z`: **READY** (hist miss=0.000%, 2026 miss=0.000%)
- `coaches_votes__match_pct`: **READY** (hist miss=0.000%, 2026 miss=0.000%)
- `coaches_votes__match_rank`: **READY** (hist miss=0.000%, 2026 miss=0.000%)
- `coaches_votes__match_share`: **READY** (hist miss=0.000%, 2026 miss=0.000%)
- `expected_coaches_votes`: **READY** (hist miss=26.737%, 2026 miss=0.000%)
- `coach_residual`: **READY** (hist miss=26.737%, 2026 miss=0.000%)
- `coach_positive_residual`: **READY** (hist miss=26.737%, 2026 miss=0.000%)
- `coach_negative_residual`: **READY** (hist miss=26.737%, 2026 miss=0.000%)
- `coach_residual_abs`: **READY** (hist miss=26.737%, 2026 miss=0.000%)
- `player_position`: **READY** (hist miss=0.000%, 2026 miss=0.000%)

## Notes

- Players per 2026 match unique sizes: [46]
- Suspicious distribution features (flagged): 5
- Actual 2026 coaches_votes present and used consistently with historical CV design.

## Full coverage table

See `final_2026_feature_coverage.csv`.
