# Brownlow Intelligence System (BIS 2026)

LLyra sports-intelligence portfolio project: expected Brownlow Medal votes from AFL player-match performance, coach recognition, and match constraints.

**Site:** Next.js app in [`web/`](web/) · **Research:** Python pipeline in [`src/`](src/) + [`scripts/`](scripts/)

## 2026 Post-Event Evaluation

The 2026 forecast was frozen before post-event evaluation.

The final model generated 9,522 player-match expected-vote forecasts across
207 matches.

After the count, the frozen predictions were evaluated against the realised
2026 Brownlow votes.

| Metric | Result |
|---|---:|
| True holdout RMSE | 0.3005 |
| Match-bootstrap 95% CI | 0.2866–0.3145 |
| Historical rolling OOT RMSE | 0.3559 |
| 3-vote winner accuracy | 69.6% |
| Top-3 recall | 75.7% |
| Season Pearson | 0.968 |
| Season Spearman | 0.736 |
| Top-5 overlap | 80% |
| Top-10 overlap | 80% |

The model correctly ranked Nick Daicos #1, forecasting 40.03 expected votes
before the post-event audit; he finished with 47 actual votes.

The holdout also exposed a clear limitation: forecast compression.
Actual 3-vote performances received only 1.93 expected votes on average,
and the predicted distribution was narrower than the realised distribution.

This post-event evaluation is preserved separately from the original frozen
forecast.

- Live Evaluation (site route): [`/evaluation`](web/src/app/evaluation/page.tsx)
- Final Evaluation Report: [`outputs/evaluation/FINAL_2026_HOLDOUT_EVALUATION.md`](outputs/evaluation/FINAL_2026_HOLDOUT_EVALUATION.md)
- Model Card: [`outputs/final/MODEL_CARD.md`](outputs/final/MODEL_CARD.md)

Vote labels for the audit were reconstructed from the [AFL Tables 2026 Brownlow matrix](https://afltables.com/afl/brownlow/brownlow2026.html) (retrieved 2026-09-24). That source is **not** labelled here as an AFL official machine-readable dump. Provenance: [`outputs/evaluation/2026_actual_vote_provenance.json`](outputs/evaluation/2026_actual_vote_provenance.json).

## Frozen research summary (do not retrain for deploy)

| Item | Value |
| --- | --- |
| Final model | CatBoost (`base_plus_components`) |
| Training | 2015–2025 |
| Forecast | 2026 |
| Features | 178 (173 numeric · 5 categorical) |
| Validation | Rolling OOT 2022–2025 |
| Champion mean OOT RMSE | **0.355865** |
| Base RMSE | 0.358172 |
| Temporal strategy | `expanding_all` (keep 2020) |
| Match constraint | per match: `0 ≤ vote ≤ 3`, sum = 6 |
| 2026 scale | 207 matches · 9,522 forecasts · 1,242 total EV |

Full write-up: [`outputs/final/MODEL_CARD.md`](outputs/final/MODEL_CARD.md)

## Repository layout

```
web/                 # Next.js portfolio site (Vercel)
src/brownlow/        # Modelling library
scripts/             # Experiment / forecast runners
outputs/final/       # Frozen forecast + model card (safe to publish)
outputs/evaluation/  # Post-event holdout audit (separate from forecast)
outputs/reports/     # Ablation / temporal summaries
data/raw/            # NOT in git — place official datathon CSV locally
```

## Local website

```bash
cd web
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Deploy to Vercel

1. Push this repo to **GitHub**.
2. In [vercel.com](https://vercel.com) → **Add New Project** → import the GitHub repo.
3. Set **Root Directory** to `web`.
4. Framework: Next.js (auto). Build: `npm run build`. Install: `npm install`.
5. Deploy. No environment variables required for the static JSON site.

## Research (optional, local only)

Raw competition data is **gitignored**. Place files under `data/raw/` then:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# see scripts/ for V2.1 / V2.2 / final 2026 runners
```

## What is not uploaded

- `.venv/`, `web/node_modules/`, `web/.next/`
- `data/raw/` (official datathon CSV / template)
- `outputs/cache/`, `outputs/oof/` (large regenerable intermediates)
- `.env*` secrets

Site JSON under `web/src/data/` is included so Vercel can build without the raw CSV.

## Disclaimer

Expected votes are model forecasts, not finishing guarantees. Model-ranked Top 3 is not an official ballot. 2026 club affiliations follow the datathon season file (post–2025 trade period). Race / Players / Matches still show the **frozen forecast**; actual results appear on Evaluation and are labelled **ACTUAL**.
