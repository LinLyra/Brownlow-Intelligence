"use client";

import { useState, type ReactNode } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  evaluationErrorAnalysis,
  evaluationLeaderboard,
  evaluationPlayerAudits,
  evaluationProvenance,
  evaluationSummary,
  findProfileByName,
} from "@/lib/data";
import { formatPct, formatVotes } from "@/lib/format";
import { PlayerAvatar } from "@/components/ui/PlayerAvatar";
import { TeamBadge } from "@/components/ui/TeamBadge";
import { PageHeader } from "@/components/layout/PageHeader";

const FEATURED = [
  "Nick Daicos",
  "Marcus Bontempelli",
  "Bailey Smith",
  "Patrick Cripps",
  "Lachie Neale",
  "Will Ashcroft",
  "Harry Sheezel",
  "Max Gawn",
  "Zak Butters",
];

function MetricTile({
  value,
  label,
  emphasize,
}: {
  value: string;
  label: string;
  emphasize?: boolean;
}) {
  return (
    <div
      className={`card shadow-card p-4 ${emphasize ? "border-gold/40 bg-gold/[0.04]" : ""}`}
    >
      <p className="text-2xl font-semibold num text-ink md:text-[1.65rem]">
        {value}
      </p>
      <p className="mt-1 text-[11px] uppercase tracking-[0.12em] text-muted">
        {label}
      </p>
    </div>
  );
}

function FoldSection({
  kicker,
  title,
  summary,
  defaultOpen = false,
  children,
}: {
  kicker?: string;
  title: string;
  summary?: string;
  defaultOpen?: boolean;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <details
      className="card shadow-card group overflow-hidden"
      open={open}
      onToggle={(e) => setOpen((e.currentTarget as HTMLDetailsElement).open)}
    >
      <summary className="flex cursor-pointer list-none items-start justify-between gap-3 px-4 py-3.5 marker:content-none sm:px-5 sm:py-4 [&::-webkit-details-marker]:hidden">
        <div className="min-w-0">
          {kicker ? (
            <p className="mb-1 text-[11px] font-medium uppercase tracking-[0.14em] text-gold">
              {kicker}
            </p>
          ) : null}
          <h2 className="text-base font-semibold tracking-tight text-ink sm:text-lg">
            {title}
          </h2>
          {summary ? (
            <p className="mt-1 text-xs text-muted sm:text-sm">{summary}</p>
          ) : null}
        </div>
        <span
          className={`mt-1 shrink-0 text-muted transition-transform ${open ? "rotate-180" : ""}`}
          aria-hidden
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path
              d="M4 6l4 4 4-4"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </span>
      </summary>
      <div className="space-y-4 border-t border-line px-4 pb-5 pt-4 sm:px-5">
        {children}
      </div>
    </details>
  );
}

export function EvaluationView() {
  const s = evaluationSummary;
  const primary = s.evaluation.primary;
  const ranking = s.evaluation.ranking;
  const season = s.evaluation.season;
  const gen = s.evaluation.generalisation;
  const diag = evaluationErrorAnalysis.diagnostics;
  const under = evaluationLeaderboard.largest_underpredictions.slice(0, 3);
  const over = evaluationLeaderboard.largest_overpredictions.slice(0, 3);

  const featured = FEATURED.map((name) => {
    const row =
      evaluationLeaderboard.forecast_top20.find((p) => p.player === name) ??
      evaluationLeaderboard.largest_underpredictions.find(
        (p) => p.player === name
      ) ??
      evaluationLeaderboard.largest_overpredictions.find(
        (p) => p.player === name
      );
    return row
      ? {
          player: row.player,
          team: row.team,
          predicted_expected_votes: row.predicted_expected_votes,
          actual_votes: row.actual_votes,
          predicted_rank: row.predicted_rank,
          actual_rank: row.actual_rank,
        }
      : null;
  }).filter(Boolean) as {
    player: string;
    team: string;
    predicted_expected_votes: number;
    actual_votes: number;
    predicted_rank: number;
    actual_rank: number;
  }[];

  const histChart = [
    ...gen.historical_years.map((y) => ({
      label: String(y.year),
      rmse: Number(y.allocated_rmse.toFixed(4)),
      kind: "oot" as const,
    })),
    {
      label: "Mean",
      rmse: Number(gen.historical_mean.toFixed(4)),
      kind: "mean" as const,
    },
    {
      label: "2026",
      rmse: Number(gen.holdout_2026_rmse.toFixed(4)),
      kind: "holdout" as const,
    },
  ];

  const daicos = evaluationPlayerAudits.contenders.find(
    (c) => c.player === "Nick Daicos"
  );
  const daicosRounds =
    daicos?.rounds?.map((r) => ({
      round: r.round,
      ev: Number(r.frozen_ev.toFixed(3)),
      actual: r.actual_vote,
      opponent: r.opponent,
    })) ?? [];

  const shaShort = `${s.forecast.sha256.slice(0, 12)}…`;

  return (
    <div className="page-wrap space-y-3 md:space-y-3.5">
      {/* Always visible — screenshot-friendly hero */}
      <div>
        <PageHeader
          kicker="Post-Event Evaluation"
          title="Frozen Forecast. Real Outcomes."
          subtitle={`A post-event audit of ${s.forecast.n_rows.toLocaleString("en-AU")} frozen player-match forecasts across all ${s.forecast.n_matches} matches of the 2026 AFL season.`}
        />
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <MetricTile
            value={primary.rmse.toFixed(4)}
            label="True Holdout RMSE"
            emphasize
          />
          <MetricTile
            value={formatPct(ranking.top1_3vote_accuracy)}
            label="3-Vote Winner Accuracy"
          />
          <MetricTile
            value={formatPct(ranking.top3_recall)}
            label="Top-3 Recall"
          />
          <MetricTile
            value={season.pearson.toFixed(3)}
            label="Season Pearson"
          />
        </div>
        <p className="mt-3 text-xs text-muted">
          Expand a section below for detail. Collapsed by default for a compact
          overview.
        </p>
      </div>

      <FoldSection
        title="Did the model generalise?"
        summary={`Holdout ${primary.rmse.toFixed(4)} vs historical mean ${s.forecast.historical_oot_rmse.toFixed(4)}`}
        defaultOpen
      >
        <div className="h-52 w-full sm:h-56">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={histChart} barCategoryGap="18%">
              <CartesianGrid stroke="#e2e8f0" vertical={false} />
              <XAxis
                dataKey="label"
                tick={{ fill: "#64748b", fontSize: 12 }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                domain={[0.28, 0.4]}
                tick={{ fill: "#64748b", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                width={42}
              />
              <Tooltip
                formatter={(v) => [
                  typeof v === "number" ? v.toFixed(4) : String(v ?? ""),
                  "Allocated RMSE",
                ]}
                contentStyle={{
                  borderRadius: 8,
                  border: "1px solid #e2e8f0",
                  fontSize: 12,
                }}
              />
              <Bar dataKey="rmse" radius={[4, 4, 0, 0]}>
                {histChart.map((d) => (
                  <Cell
                    key={d.label}
                    fill={
                      d.kind === "holdout"
                        ? "#b8963e"
                        : d.kind === "mean"
                          ? "#94a3b8"
                          : "#1e3a5f"
                    }
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
        <p className="text-sm leading-relaxed text-muted">
          The frozen 2026 forecast achieved an RMSE of{" "}
          <span className="num text-ink">{primary.rmse.toFixed(4)}</span>{" "}
          (match-bootstrap 95% CI:{" "}
          <span className="num text-ink">
            {primary.rmse_ci95[0].toFixed(4)}–{primary.rmse_ci95[1].toFixed(4)}
          </span>
          ), compared with a mean rolling out-of-time RMSE of{" "}
          <span className="num text-ink">
            {s.forecast.historical_oot_rmse.toFixed(4)}
          </span>{" "}
          across the 2022–2025 development folds.
        </p>
      </FoldSection>

      <FoldSection
        title="Forecast vs Reality"
        summary="Predicted EV vs ACTUAL season votes for key contenders"
      >
        <ul className="space-y-2">
          {featured.map((p) => {
            const profile = findProfileByName(p.player);
            return (
              <li
                key={p.player}
                className="flex flex-wrap items-center gap-3 rounded-lg border border-line bg-bg/60 p-3 sm:gap-4"
              >
                <PlayerAvatar
                  name={p.player}
                  team={p.team}
                  imageUrl={profile?.imageUrl ?? null}
                  size="md"
                />
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-medium text-ink">{p.player}</p>
                    <TeamBadge team={p.team} size="sm" showName={false} />
                  </div>
                  <p className="mt-1 text-xs text-muted">
                    Rank #{p.predicted_rank} → ACTUAL #{p.actual_rank}
                  </p>
                </div>
                <div className="grid grid-cols-2 gap-4 text-right sm:min-w-[160px]">
                  <div>
                    <p className="text-sm font-semibold num">
                      {formatVotes(p.predicted_expected_votes)}
                    </p>
                    <p className="text-[10px] uppercase tracking-[0.1em] text-muted">
                      Predicted
                    </p>
                  </div>
                  <div>
                    <p className="text-sm font-semibold num text-gold">
                      {p.actual_votes}
                    </p>
                    <p className="text-[10px] uppercase tracking-[0.1em] text-muted">
                      Actual
                    </p>
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
      </FoldSection>

      <FoldSection
        title="Match-level ranking quality"
        summary={`${formatPct(ranking.top1_3vote_accuracy)} top-1 · ${formatPct(ranking.top3_recall)} top-3 recall`}
      >
        <div className="grid gap-3 sm:grid-cols-2">
          <MetricTile
            value={formatPct(ranking.top1_3vote_accuracy)}
            label="Model #1 received actual 3 votes"
          />
          <MetricTile
            value={formatPct(ranking.top3_recall)}
            label="Actual vote-getters in model Top 3"
          />
          <MetricTile
            value={formatPct(ranking.exact_top3_set_rate)}
            label="Exact Top-3 player set"
          />
          <MetricTile
            value={formatPct(ranking.exact_ordered_321_rate)}
            label="Exact ordered 3–2–1"
          />
        </div>
      </FoldSection>

      <FoldSection
        title="Where the model worked"
        summary="RMSE, season correlation, Top-k overlap, champion ID"
      >
        <div className="space-y-3 text-sm leading-relaxed text-muted">
          <p>
            Holdout RMSE{" "}
            <span className="num text-ink">{primary.rmse.toFixed(4)}</span> vs
            historical mean{" "}
            <span className="num text-ink">
              {s.forecast.historical_oot_rmse.toFixed(4)}
            </span>
            . Season Pearson{" "}
            <span className="num text-ink">{season.pearson.toFixed(3)}</span>,
            Spearman{" "}
            <span className="num text-ink">{season.spearman.toFixed(3)}</span>.
            Top-5 / Top-10 overlap{" "}
            <span className="num text-ink">
              {formatPct(season.top_5_overlap, 0)}
            </span>{" "}
            /{" "}
            <span className="num text-ink">
              {formatPct(season.top_10_overlap, 0)}
            </span>
            . Predicted #1{" "}
            <span className="text-ink">{season.predicted_rank1_player}</span>{" "}
            matched ACTUAL ({season.actual_rank1_votes} votes).
          </p>
        </div>
      </FoldSection>

      <FoldSection
        title="Where the model missed"
        summary="Largest under- and over-predictions (≥5 games)"
      >
        <div className="grid gap-4 lg:grid-cols-2">
          <div className="rounded-lg border border-line p-4">
            <h3 className="text-sm font-semibold uppercase tracking-[0.12em]">
              Underpredictions
            </h3>
            <ul className="mt-3 space-y-3">
              {under.map((p) => {
                const profile = findProfileByName(p.player);
                return (
                  <li key={p.player} className="flex items-center gap-3">
                    <PlayerAvatar
                      name={p.player}
                      team={p.team}
                      imageUrl={profile?.imageUrl ?? null}
                      size="sm"
                    />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium">{p.player}</p>
                      <p className="text-xs text-muted">
                        {formatVotes(p.predicted_expected_votes)} →{" "}
                        {p.actual_votes} ACTUAL
                      </p>
                    </div>
                    <span className="text-sm font-semibold num">
                      +{formatVotes(p.under_gap)}
                    </span>
                  </li>
                );
              })}
            </ul>
          </div>
          <div className="rounded-lg border border-line p-4">
            <h3 className="text-sm font-semibold uppercase tracking-[0.12em]">
              Overpredictions
            </h3>
            <ul className="mt-3 space-y-3">
              {over.map((p) => {
                const profile = findProfileByName(p.player);
                return (
                  <li key={p.player} className="flex items-center gap-3">
                    <PlayerAvatar
                      name={p.player}
                      team={p.team}
                      imageUrl={profile?.imageUrl ?? null}
                      size="sm"
                    />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium">{p.player}</p>
                      <p className="text-xs text-muted">
                        {formatVotes(p.predicted_expected_votes)} →{" "}
                        {p.actual_votes} ACTUAL
                      </p>
                    </div>
                    <span className="text-sm font-semibold num">
                      +{formatVotes(p.over_gap)}
                    </span>
                  </li>
                );
              })}
            </ul>
          </div>
        </div>
      </FoldSection>

      <FoldSection
        title="Forecast compression"
        summary={`3-vote mean EV ${diag.actual_3_mean_pred.toFixed(2)} · pred SD ${diag.pred_std.toFixed(2)} vs actual SD ${diag.actual_std.toFixed(2)}`}
      >
        <div className="grid gap-3 sm:grid-cols-3">
          <MetricTile
            value={diag.actual_3_mean_pred.toFixed(2)}
            label="Mean EV on actual 3-vote games"
          />
          <MetricTile value={diag.pred_std.toFixed(2)} label="Prediction SD" />
          <MetricTile
            value={diag.actual_std.toFixed(2)}
            label="Actual vote SD"
          />
        </div>
        <p className="text-sm leading-relaxed text-muted">
          The forecast distribution was narrower than the realised vote
          distribution —{" "}
          <span className="text-ink">forecast compression</span> /
          regression toward the mean on extreme outcomes. Descriptive, not
          causal.
        </p>
      </FoldSection>

      <FoldSection
        kicker="Case study"
        title="Nick Daicos"
        summary={`${formatVotes(daicos?.predicted_expected_votes ?? 0)} EV → ${daicos?.actual_votes ?? "—"} ACTUAL · #${daicos?.predicted_rank ?? "—"} → #${daicos?.actual_rank ?? "—"}`}
      >
        <div className="grid gap-4 sm:grid-cols-4">
          <div>
            <p className="text-[11px] uppercase tracking-[0.12em] text-muted">
              Season forecast
            </p>
            <p className="mt-1 text-xl font-semibold num">
              {formatVotes(daicos?.predicted_expected_votes ?? 0)} EV
            </p>
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-[0.12em] text-muted">
              Actual
            </p>
            <p className="mt-1 text-xl font-semibold num text-gold">
              {daicos?.actual_votes ?? "—"}
            </p>
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-[0.12em] text-muted">
              Predicted rank
            </p>
            <p className="mt-1 text-xl font-semibold num">
              #{daicos?.predicted_rank ?? "—"}
            </p>
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-[0.12em] text-muted">
              Actual rank
            </p>
            <p className="mt-1 text-xl font-semibold num">
              #{daicos?.actual_rank ?? "—"}
            </p>
          </div>
        </div>
        <div className="h-52 w-full sm:h-56">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={daicosRounds}>
              <CartesianGrid stroke="#e2e8f0" vertical={false} />
              <XAxis
                dataKey="round"
                tick={{ fill: "#64748b", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                domain={[0, 3]}
                ticks={[0, 1, 2, 3]}
                tick={{ fill: "#64748b", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                width={28}
              />
              <Tooltip
                contentStyle={{
                  borderRadius: 8,
                  border: "1px solid #e2e8f0",
                  fontSize: 12,
                }}
                formatter={(v, name) => [
                  typeof v === "number" ? v.toFixed(3) : String(v ?? ""),
                  name === "ev" ? "Frozen EV" : "ACTUAL vote",
                ]}
                labelFormatter={(r) => `Round ${r}`}
              />
              <Bar
                dataKey="actual"
                name="actual"
                fill="#c4a35a"
                opacity={0.85}
                radius={[3, 3, 0, 0]}
              />
              <Line
                type="monotone"
                dataKey="ev"
                name="ev"
                stroke="#1e3a5f"
                strokeWidth={2}
                dot={{ r: 3, fill: "#1e3a5f" }}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </FoldSection>

      <FoldSection
        title="Model integrity"
        summary={`SHA256 ${shaShort} · 207 matches · no recalibration`}
      >
        <dl className="grid gap-3 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-muted">Frozen forecast rows</dt>
            <dd className="mt-0.5 font-medium num">
              {s.forecast.n_rows.toLocaleString("en-AU")}
            </dd>
          </div>
          <div>
            <dt className="text-muted">Matches</dt>
            <dd className="mt-0.5 font-medium num">{s.forecast.n_matches}</dd>
          </div>
          <div>
            <dt className="text-muted">Expected-vote total</dt>
            <dd className="mt-0.5 font-medium num">
              {Math.round(s.forecast.total_expected_votes).toLocaleString(
                "en-AU"
              )}
            </dd>
          </div>
          <div>
            <dt className="text-muted">Forecast SHA256</dt>
            <dd className="mt-0.5 break-all font-mono text-xs">{shaShort}</dd>
          </div>
          <div>
            <dt className="text-muted">Actual count</dt>
            <dd className="mt-0.5 font-medium">
              {s.actual.n_matches_ok} matches /{" "}
              <span className="num">{s.actual.total_votes}</span> votes
            </dd>
          </div>
          <div>
            <dt className="text-muted">Positive-vote join</dt>
            <dd className="mt-0.5 font-medium">100%</dd>
          </div>
        </dl>
        <p className="border-t border-line pt-4 text-sm text-muted">
          No retraining. No post-event recalibration.{" "}
          <span className="text-ink">
            2026 actual votes were used only for post-event evaluation.
          </span>
        </p>
        <p className="text-xs leading-relaxed text-muted">
          Labels reconstructed from{" "}
          <a
            href={evaluationProvenance.source_url}
            className="text-ink underline-offset-2 hover:underline"
            target="_blank"
            rel="noreferrer"
          >
            {evaluationProvenance.source_name}
          </a>{" "}
          (retrieved {evaluationProvenance.retrieval_date_utc}) — not labelled
          as an AFL official dump.
        </p>
      </FoldSection>

      <FoldSection
        title="What comes next"
        summary="Research directions · not a V3 model announcement"
      >
        <ul className="list-disc space-y-1.5 pl-5 text-sm text-muted">
          <li>Tail calibration of extreme expected-vote mass</li>
          <li>Modelling of extreme 3-vote performances</li>
          <li>Positional under / overprediction patterns</li>
          <li>Coach-versus-umpire disagreement structure</li>
          <li>Uncertainty modelling around continuous forecasts</li>
        </ul>
      </FoldSection>
    </div>
  );
}
