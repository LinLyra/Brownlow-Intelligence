"use client";

import { useEffect, useId, useState } from "react";
import Link from "next/link";
import { EVAL_MODAL_STORAGE_KEY } from "@/lib/types";
import { evaluationSummary } from "@/lib/data";
import { formatPct } from "@/lib/format";

const METRICS = [
  {
    value: evaluationSummary.evaluation.primary.rmse.toFixed(4),
    label: "True Holdout RMSE",
  },
  {
    value: formatPct(evaluationSummary.evaluation.ranking.top1_3vote_accuracy),
    label: "3-Vote Winner Accuracy",
  },
  {
    value: formatPct(evaluationSummary.evaluation.ranking.top3_recall),
    label: "Top-3 Recall",
  },
  {
    value: evaluationSummary.evaluation.season.pearson.toFixed(3),
    label: "Season Pearson",
  },
] as const;

export function EvaluationModal() {
  const titleId = useId();
  const [open, setOpen] = useState(false);
  const [dontShow, setDontShow] = useState(false);

  useEffect(() => {
    try {
      if (window.localStorage.getItem(EVAL_MODAL_STORAGE_KEY) === "1") return;
    } catch {
      /* ignore */
    }
    setOpen(true);
  }, []);

  function dismiss(persist: boolean) {
    if (persist || dontShow) {
      try {
        window.localStorage.setItem(EVAL_MODAL_STORAGE_KEY, "1");
      } catch {
        /* ignore */
      }
    }
    setOpen(false);
  }

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-navy/45 p-3 sm:items-center sm:p-6"
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
    >
      <button
        type="button"
        className="absolute inset-0 cursor-default"
        aria-label="Dismiss"
        onClick={() => dismiss(false)}
      />
      <div className="relative w-full max-w-lg overflow-hidden rounded-xl border border-line bg-surface shadow-card">
        <div className="border-b border-line px-5 py-4 sm:px-6 sm:py-5">
          <p className="text-[11px] font-medium uppercase tracking-[0.14em] text-gold">
            Post-Event Evaluation
          </p>
          <h2
            id={titleId}
            className="mt-1.5 text-xl font-semibold tracking-tight text-ink sm:text-2xl"
          >
            The forecast met reality.
          </h2>
          <p className="mt-2 text-sm leading-relaxed text-muted">
            The 2026 Brownlow count is now complete. Brownlow Intelligence was
            developed with historical rolling out-of-time validation, and its{" "}
            {evaluationSummary.forecast.n_rows.toLocaleString("en-AU")}{" "}
            player-match forecasts were frozen before post-event evaluation. The
            frozen forecast can now be compared with the realised 2026 count.
          </p>
        </div>

        <div className="grid grid-cols-2 gap-px bg-line sm:grid-cols-4">
          {METRICS.map((m) => (
            <div key={m.label} className="bg-surface px-3 py-3 sm:px-4 sm:py-3.5">
              <p className="text-lg font-semibold num text-ink sm:text-xl">
                {m.value}
              </p>
              <p className="mt-0.5 text-[10px] leading-snug text-muted sm:text-[11px]">
                {m.label}
              </p>
            </div>
          ))}
        </div>

        <div className="space-y-4 px-5 py-4 sm:px-6 sm:py-5">
          <p className="text-xs text-muted">
            Historical development benchmark:{" "}
            <span className="num text-ink">
              {evaluationSummary.forecast.historical_oot_rmse.toFixed(4)}
            </span>{" "}
            mean rolling OOT RMSE (2022–2025)
          </p>

          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <Link
              href="/evaluation"
              onClick={() => dismiss(false)}
              className="inline-flex items-center justify-center rounded-md bg-navy px-4 py-2.5 text-sm font-medium text-white hover:bg-navy-2"
            >
              View Evaluation
            </Link>
            <Link
              href="/race"
              onClick={() => dismiss(false)}
              className="inline-flex items-center justify-center rounded-md border border-line bg-white px-4 py-2.5 text-sm font-medium text-ink hover:bg-slate-50"
            >
              Explore Original Forecast
            </Link>
          </div>

          <label className="flex cursor-pointer items-center gap-2 text-xs text-muted">
            <input
              type="checkbox"
              className="rounded border-line"
              checked={dontShow}
              onChange={(e) => setDontShow(e.target.checked)}
            />
            Don&apos;t show again
          </label>
        </div>
      </div>
    </div>
  );
}
