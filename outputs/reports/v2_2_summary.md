# V2.2 Temporal Robustness — Research Summary

## Research question

How stable is the Brownlow voting *predictive relationship* through time, and how much
historical data should be used when predicting a future AFL season?

V2.1 champion reproduction (expanding_all / base_plus_components): **0.355865**
(reference 0.355865).

## Temporal strategy scorecard

| strategy | 2022 | 2023 | 2024 | 2025 | mean_rmse | std_rmse | worst_season_rmse | recent2_mean_rmse | delta_vs_v21_champion |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| expanding_all | 0.315314 | 0.380906 | 0.370621 | 0.356620 | 0.355865 | 0.024949 | 0.380906 | 0.363621 | 0.000000 |
| expanding_exclude_2020 | 0.317114 | 0.382664 | 0.370865 | 0.357170 | 0.356953 | 0.024707 | 0.382664 | 0.364017 | 0.001088 |
| trailing_8 | 0.315314 | 0.380906 | 0.370235 | 0.357233 | 0.355922 | 0.024899 | 0.380906 | 0.363734 | 0.000057 |
| trailing_6 | 0.313280 | 0.382126 | 0.375961 | 0.356559 | 0.356982 | 0.026937 | 0.382126 | 0.366260 | 0.001117 |
| trailing_4 | 0.317552 | 0.383098 | 0.372659 | 0.358346 | 0.357914 | 0.024904 | 0.383098 | 0.365502 | 0.002049 |
| decay_005 | 0.315687 | 0.382055 | 0.373696 | 0.357752 | 0.357298 | 0.025561 | 0.382055 | 0.365724 | 0.001433 |
| decay_010 | 0.316121 | 0.381504 | 0.372983 | 0.356471 | 0.356770 | 0.025135 | 0.381504 | 0.364727 | 0.000905 |
| decay_020 | 0.317945 | 0.382202 | 0.370282 | 0.357896 | 0.357081 | 0.024175 | 0.382202 | 0.364089 | 0.001216 |
| decay_035 | 0.317032 | 0.384638 | 0.372135 | 0.357638 | 0.357861 | 0.025435 | 0.384638 | 0.364887 | 0.001996 |

## Paired comparison vs expanding_all

| strategy | baseline | mean_paired_mse_diff | median_paired_mse_diff | pct_obs_improved | boot_mean_mse_diff | boot_ci95_lo | boot_ci95_hi | n_obs | n_matches | season_2022_mse_diff | season_2023_mse_diff | season_2024_mse_diff | season_2025_mse_diff |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| expanding_exclude_2020 | expanding_all | 0.00075971 | 0 | 33.5256 | 0.000770198 | -7.92407e-05 | 0.00163428 | 37628 | 818 | 0.00113846 | 0.00134228 | 0.000180819 | 0.00039197 |
| trailing_8 | expanding_all | 3.76478e-05 | 0 | 18.5155 | 8.94744e-06 | -0.000523094 | 0.000679617 | 37628 | 818 | 0 | 0 | -0.000286167 | 0.000437051 |
| trailing_6 | expanding_all | 0.000924059 | 0 | 38.9417 | 0.000929036 | -2.17438e-05 | 0.00188731 | 37628 | 818 | -0.0012783 | 0.000931124 | 0.00398673 | -4.37439e-05 |
| trailing_4 | expanding_all | 0.00146049 | 0 | 35.0032 | 0.00148936 | 0.000247998 | 0.00264979 | 37628 | 818 | 0.00141642 | 0.00167467 | 0.00151427 | 0.0012336 |
| decay_005 | expanding_all | 0.00106167 | 0 | 36.2895 | 0.00105533 | 0.000315905 | 0.0017449 | 37628 | 818 | 0.000235678 | 0.000877012 | 0.00228882 | 0.000808019 |
| decay_010 | expanding_all | 0.000656336 | 0 | 33.1349 | 0.000664805 | -0.00018525 | 0.00146043 | 37628 | 818 | 0.000509976 | 0.000455763 | 0.0017559 | -0.000106345 |
| decay_020 | expanding_all | 0.000819379 | 0 | 33.1774 | 0.00079818 | -3.88071e-05 | 0.00164806 | 37628 | 818 | 0.001666 | 0.000989153 | -0.000251694 | 0.000911308 |
| decay_035 | expanding_all | 0.00145371 | 0 | 34.1767 | 0.00146855 | 0.000495188 | 0.00255414 | 37628 | 818 | 0.00108682 | 0.00285721 | 0.00112438 | 0.00072695 |

## Feature drift (largest Pearson range across seasons)

| feature | min_p | max_p | range |
| --- | --- | --- | --- |
| coaches_votes | 0.6453 | 0.7334 | 0.0882 |
| goals | 0.2150 | 0.2971 | 0.0821 |
| supercoach_score | 0.3753 | 0.4538 | 0.0785 |
| afl_fantasy_score | 0.3645 | 0.4414 | 0.0769 |
| clearances | 0.2944 | 0.3555 | 0.0611 |
| disposals | 0.3365 | 0.3936 | 0.0571 |
| contested_possessions | 0.3296 | 0.3772 | 0.0475 |
| metres_gained | 0.2701 | 0.3065 | 0.0364 |

## Answers

### 1. Is the Brownlow prediction function temporally stable?

Fold RMSE under expanding_all ranges from 0.3153 to 0.3809 (std=0.0249). Associations appear broadly persistent, but year-to-year predictive difficulty is not constant—treat stability as approximate, not absolute.

### 2. Does old historical data still help?

Trailing windows vs expanding_all: trailing_4 mean=0.357914, trailing_8=0.355922, expanding_all=0.355865. Shorter windows did not dominate; older seasons still appear to carry usable predictive association.

### 3. Is there evidence that recent seasons deserve greater weight?

Best decay strategy: decay_010 mean=0.356770 (Δ vs expanding_all=+0.000904), recent-2=0.364727. No clear gain from exponential decay over uniform expanding history.

### 4. Does excluding 2020 help?

expanding_exclude_2020 mean=0.356953 (Δ=+0.001088), recent-2=0.364017 vs expanding_all recent-2=0.363621. Excluding 2020 did not improve mean OOT; retain 2020 unless other evidence emerges.

### 5. Which features show the strongest temporal drift?

Largest season-to-season Pearson ranges among raw signals: coaches_votes (Δr=0.088), goals (Δr=0.082), supercoach_score (Δr=0.078).

### 6. Which temporal strategy should be carried forward?

**expanding_all**

Carry forward `expanding_all` based on mean OOT, recent-2 mean, worst-season RMSE, and paired evidence (best_mean=expanding_all, best_recent2=expanding_all, most_robust_near_best=trailing_8).

### 7. Limitations

Strategies share the same feature set and hyperparameters; results may shift under retuning. Paired bootstrap uses match blocks but a single seed. Ridge coefficients are associative explanatory summaries, not causal umpire effects. 2020 exclusion is one empirical contrast, not a full regime-shift causal analysis.
