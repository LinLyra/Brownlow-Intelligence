# Brownlow Intelligence — Portfolio Website

Static Next.js frontend for the frozen Brownlow Intelligence forecasts.

## Run locally

```bash
cd web
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

Production:

```bash
cd web
npm run build
npm run start
```

## Data

Verified JSON under `src/data/` is copied from `outputs/web/`. Do not retrain models from this app.

## Configure links

Edit placeholders in `src/lib/types.ts` (`SITE.githubUrl`, `SITE.portfolioUrl`, `SITE.linkedinUrl`).
