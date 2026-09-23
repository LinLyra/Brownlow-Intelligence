# Brownlow Intelligence System (BIS 2026)

LLyra sports-intelligence portfolio project: expected Brownlow Medal votes from AFL player-match performance, coach recognition, and match constraints.

**Site:** Next.js app in [`web/`](web/) · **Research:** Python pipeline in [`src/`](src/) + [`scripts/`](scripts/)

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

Expected votes are model forecasts, not finishing guarantees. Model-ranked Top 3 is not an official ballot. 2026 club affiliations follow the datathon season file (post–2025 trade period).
