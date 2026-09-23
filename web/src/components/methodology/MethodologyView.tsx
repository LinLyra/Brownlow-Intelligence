import { ArrowRight } from "lucide-react";
import { modelPerformance } from "@/lib/data";
import { formatRmse } from "@/lib/format";
import { SITE } from "@/lib/types";
import { PageHeader } from "@/components/layout/PageHeader";

const FOLDS = [
  { train: "2015–2021", test: "2022" },
  { train: "2015–2022", test: "2023" },
  { train: "2015–2023", test: "2024" },
  { train: "2015–2024", test: "2025" },
];

const PIPELINE = [
  "Performance Data",
  "Match-Relative Features",
  "Coach Intelligence",
  "CatBoost",
  "Match Constraint",
  "Season Forecast",
];

export function MethodologyView() {
  return (
    <div className="page-wrap space-y-6">
      <PageHeader
        kicker="Technical Summary"
        title="Methodology"
        subtitle="Structured reference for technical recruiters. Implementation clutter omitted."
      />

      <article className="card shadow-card p-5 md:p-6">
        <h2 className="text-sm font-semibold uppercase tracking-[0.12em]">
          Model Summary
        </h2>
        <dl className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {[
            { label: "Final Model", value: "CatBoost" },
            { label: "Training", value: SITE.trainingYears },
            { label: "Forecast", value: String(SITE.forecastYear) },
            { label: "Features", value: String(SITE.featureCount) },
            { label: "Numeric", value: String(SITE.numericFeatures) },
            { label: "Categorical", value: String(SITE.categoricalFeatures) },
            {
              label: "OOT RMSE",
              value: formatRmse(modelPerformance.coachIntelligenceRmse),
            },
            {
              label: "Champion Experiment",
              value: modelPerformance.championExperiment,
            },
          ].map((item) => (
            <div
              key={item.label}
              className="rounded-md border border-line bg-slate-50/50 px-3 py-3"
            >
              <dt className="label">{item.label}</dt>
              <dd className="mt-1 text-base font-semibold num">{item.value}</dd>
            </div>
          ))}
        </dl>
      </article>

      <article className="card shadow-card p-5 md:p-6">
        <h2 className="text-sm font-semibold uppercase tracking-[0.12em]">
          Validation Design
        </h2>
        <p className="mt-2 max-w-3xl text-sm text-muted leading-relaxed">
          Each validation season was predicted only using earlier seasons.
          Rolling out-of-time folds evaluate the model on seasons that were
          never used for that fold&apos;s training. 2026 was never used for
          model tuning.
        </p>

        <ol className="mt-5 flex flex-col gap-2 md:flex-row md:flex-wrap md:items-stretch">
          {FOLDS.map((f, i) => (
            <li
              key={f.test}
              className="flex flex-1 items-center gap-2 min-w-[160px]"
            >
              <div className="flex-1 rounded-md border border-line px-3 py-3">
                <p className="text-[11px] text-muted">{f.train}</p>
                <p className="mt-1 text-sm font-semibold">
                  → {f.test}
                </p>
                <p className="mt-1 text-xs num text-gold">
                  RMSE {formatRmse(modelPerformance.foldRmse[f.test])}
                </p>
              </div>
              {i < FOLDS.length - 1 ? (
                <ArrowRight
                  size={14}
                  className="hidden shrink-0 text-muted md:block"
                  aria-hidden
                />
              ) : null}
            </li>
          ))}
        </ol>
      </article>

      <article className="card shadow-card p-5 md:p-6">
        <h2 className="text-sm font-semibold uppercase tracking-[0.12em]">
          Modelling Pipeline
        </h2>
        <ol className="mt-5 flex flex-col gap-2 md:flex-row md:flex-wrap md:items-center">
          {PIPELINE.map((stage, i) => (
            <li key={stage} className="flex items-center gap-2">
              <span className="rounded-md border border-line bg-white px-3 py-2 text-sm font-medium">
                {stage}
              </span>
              {i < PIPELINE.length - 1 ? (
                <ArrowRight size={14} className="text-muted shrink-0" aria-hidden />
              ) : null}
            </li>
          ))}
        </ol>
      </article>

      <article className="card shadow-card p-5 md:p-6">
        <h2 className="text-sm font-semibold uppercase tracking-[0.12em]">
          Match Constraint
        </h2>
        <ul className="mt-4 space-y-2 text-sm">
          <li className="flex gap-2">
            <span className="text-gold font-semibold">→</span>
            <span>
              <span className="num">0 ≤</span> expected vote{" "}
              <span className="num">≤ 3</span>
            </span>
          </li>
          <li className="flex gap-2">
            <span className="text-gold font-semibold">→</span>
            <span>
              Sum expected votes per match = <span className="num">6</span>
            </span>
          </li>
        </ul>
      </article>

      <article className="card shadow-card p-5 md:p-6">
        <h2 className="text-sm font-semibold uppercase tracking-[0.12em]">
          Limitations
        </h2>
        <ul className="mt-4 space-y-2 text-sm text-muted leading-relaxed">
          <li>Expected votes are forecasts.</li>
          <li>Umpire deliberations are unobserved.</li>
          <li>Historical relationships are not causal.</li>
          <li>Model-ranked Top 3 is not the official ballot.</li>
          <li>Some 2026 context features show distribution shift.</li>
        </ul>
      </article>
    </div>
  );
}
