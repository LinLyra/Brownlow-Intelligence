"use client";

import type { ReactNode } from "react";
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

function Section({
  kicker,
  title,
  children,
}: {
  kicker?: string;
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="space-y-4">
      <div>
        {kicker ? (
          <p className="mb-1 text-[11px] font-medium uppercase tracking-[0.14em] text-gold">
            {kicker}
          </p>
        ) : null}
        <h2 className="text-lg font-semibold tracking-tight text-ink md:text-xl">
          {title}
        </h2>
      </div>
      {children}
    </section>
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
    <div className="page-wrap space-y-10 md:space-y-12">
      {/* 1 — Hero */}
      <div>
        <PageHeader
          kicker="Post-Event Evaluation"
          title="Frozen Forecast. Real Outcomes."
          subtitle={`A post-event audit of ${s.forecast.n_rows.toLocaleString("en-AU")} frozen player-match forecasts across all ${s.forecast.n_matches} matches of the 2026 AFL season.`}
        />
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <MetricTile value={primary.rmse.toFixed(4)} label="True Holdout RMSE" emphasize />
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
      </div>

      {/* 2 — Generalisation */}
      <Section title="Did the model generalise?">
        <div className="card shadow-card p-4 md:p-5">
          <div className="h-56 w-full sm:h-64">
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
          <p className="mt-4 text-sm leading-relaxed text-muted">
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
          <p className="mt-2 text-xs text-muted">
            Bars: historical OOT folds · grey = fold mean · gold = 2026 true
            holdout.
          </p>
        </div>
      </Section>

      {/* 3 — Forecast vs Reality */}
      <Section title="Forecast vs Reality">
        <p className="text-sm text-muted">
          Season totals from the frozen forecast compared with{" "}
          <span className="font-medium text-ink">ACTUAL</span> Brownlow votes.
          Forecast pages elsewhere remain unchanged.
        </p>
        <ul className="space-y-2">
          {featured.map((p) => {
            const profile = findProfileByName(p.player);
            return (
              <li
                key={p.player}
                className="card shadow-card flex flex-wrap items-center gap-3 p-3 sm:gap-4 sm:p-4"
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
                    <span className="text-xs text-muted">{p.team}</span>
                  </div>
                  <p className="mt-1 text-xs text-muted">
                    Rank #{p.predicted_rank} →{" "}
                    <span className="text-ink">ACTUAL #{p.actual_rank}</span>
                  </p>
                </div>
                <div className="grid grid-cols-2 gap-4 text-right sm:min-w-[180px]">
                  <div>
                    <p className="text-sm font-semibold num">
                      {formatVotes(p.predicted_expected_votes)}
                    </p>
                    <p className="text-[10px] uppercase tracking-[0.1em] text-muted">
                      Predicted EV
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
      </Section>

      {/* 4 — Ranking quality */}
      <Section title="Match-level ranking quality">
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
        <p className="text-sm text-muted">
          Expected votes are continuous; discrete ballot exact-match rates are
          complementary diagnostics, not the primary scoring metric.
        </p>
      </Section>

      {/* 5 — Where it worked */}
      <Section title="Where the model worked">
        <div className="card shadow-card space-y-3 p-5 text-sm leading-relaxed text-muted">
          <p>
            Player-match holdout RMSE of{" "}
            <span className="num text-ink">{primary.rmse.toFixed(4)}</span> sat
            below the historical development mean of{" "}
            <span className="num text-ink">
              {s.forecast.historical_oot_rmse.toFixed(4)}
            </span>
            .
          </p>
          <p>
            Season totals tracked realised polling order closely (Pearson{" "}
            <span className="num text-ink">{season.pearson.toFixed(3)}</span>,
            Spearman{" "}
            <span className="num text-ink">{season.spearman.toFixed(3)}</span>
            ).
          </p>
          <p>
            Set overlap reached{" "}
            <span className="num text-ink">
              {formatPct(season.top_5_overlap, 0)}
            </span>{" "}
            for Top-5 and{" "}
            <span className="num text-ink">
              {formatPct(season.top_10_overlap, 0)}
            </span>{" "}
            for Top-10.
          </p>
          <p>
            The frozen forecast ranked{" "}
            <span className="text-ink">{season.predicted_rank1_player}</span>{" "}
            #1 ({formatVotes(season.predicted_rank1_expected_votes)} EV); he
            finished #1 with{" "}
            <span className="num text-ink">{season.actual_rank1_votes}</span>{" "}
            ACTUAL votes.
          </p>
          <p>
            Match ranking captured the actual 3-vote winner{" "}
            <span className="num text-ink">
              {formatPct(ranking.top1_3vote_accuracy)}
            </span>{" "}
            of the time and recovered{" "}
            <span className="num text-ink">
              {formatPct(ranking.top3_recall)}
            </span>{" "}
            of vote-getters inside the model Top 3.
          </p>
        </div>
      </Section>

      {/* 6 — Where it missed */}
      <Section title="Where the model missed">
        <div className="grid gap-4 lg:grid-cols-2">
          <div className="card shadow-card p-5">
            <h3 className="text-sm font-semibold uppercase tracking-[0.12em] text-ink">
              Largest underpredictions
            </h3>
            <p className="mt-1 text-xs text-muted">
              ACTUAL − predicted EV · players with ≥5 games
            </p>
            <ul className="mt-4 space-y-3">
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
                        <span className="text-ink">{p.actual_votes}</span>{" "}
                        ACTUAL
                      </p>
                    </div>
                    <span className="text-sm font-semibold num text-ink">
                      +{formatVotes(p.under_gap)}
                    </span>
                  </li>
                );
              })}
            </ul>
          </div>
          <div className="card shadow-card p-5">
            <h3 className="text-sm font-semibold uppercase tracking-[0.12em] text-ink">
              Largest overpredictions
            </h3>
            <p className="mt-1 text-xs text-muted">
              Predicted EV − ACTUAL · players with ≥5 games
            </p>
            <ul className="mt-4 space-y-3">
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
                        <span className="text-ink">{p.actual_votes}</span>{" "}
                        ACTUAL
                      </p>
                    </div>
                    <span className="text-sm font-semibold num text-ink">
                      +{formatVotes(p.over_gap)}
                    </span>
                  </li>
                );
              })}
            </ul>
          </div>
        </div>
      </Section>

      {/* 7 — Compression */}
      <Section title="The model knew who was good. It was less confident about how good.">
        <div className="card shadow-card p-5 md:p-6">
          <div className="grid gap-3 sm:grid-cols-3">
            <MetricTile
              value={diag.actual_3_mean_pred.toFixed(2)}
              label="Mean EV on actual 3-vote games"
            />
            <MetricTile
              value={diag.pred_std.toFixed(2)}
              label="Prediction SD"
            />
            <MetricTile
              value={diag.actual_std.toFixed(2)}
              label="Actual vote SD"
            />
          </div>
          <p className="mt-5 text-sm leading-relaxed text-muted">
            The forecast distribution was narrower than the realised vote
            distribution. Elite performances were ranked effectively, but
            extreme outcomes show{" "}
            <span className="text-ink">forecast compression</span> —
            regression toward the mean and limited tail calibration on 3-vote
            games. These are descriptive associations from the holdout, not
            causal claims.
          </p>
        </div>
      </Section>

      {/* 8 — Daicos */}
      <Section kicker="Case study" title="Nick Daicos">
        <div className="card shadow-card overflow-hidden">
          <div className="grid gap-4 border-b border-line p-5 sm:grid-cols-4 sm:p-6">
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
          <div className="p-4 md:p-5">
            <div className="h-56 w-full sm:h-64">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={daicosRounds}>
                  <CartesianGrid stroke="#e2e8f0" vertical={false} />
                  <XAxis
                    dataKey="round"
                    tick={{ fill: "#64748b", fontSize: 11 }}
                    axisLine={false}
                    tickLine={false}
                    label={{
                      value: "Round",
                      position: "insideBottom",
                      offset: -2,
                      fill: "#94a3b8",
                      fontSize: 11,
                    }}
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
            <p className="mt-4 text-sm leading-relaxed text-muted">
              The earlier 40-EV season forecast was aggressive relative to
              typical historical season totals, yet still underpredicted the
              realised count of {daicos?.actual_votes ?? 47}. Rank #1 was
              correct; the magnitude of the peak season was not fully captured.
              The original forecast narrative on Race / Players is unchanged.
            </p>
          </div>
        </div>
      </Section>

      {/* 9 — Integrity */}
      <Section title="Model integrity">
        <div className="card shadow-card p-5 md:p-6">
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
              <dd className="mt-0.5 break-all font-mono text-xs text-ink">
                {shaShort}
              </dd>
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
          <p className="mt-5 border-t border-line pt-4 text-sm text-muted">
            No retraining. No post-event recalibration.{" "}
            <span className="text-ink">
              2026 actual votes were used only for post-event evaluation.
            </span>
          </p>
          <p className="mt-3 text-xs leading-relaxed text-muted">
            Vote labels reconstructed from{" "}
            <a
              href={evaluationProvenance.source_url}
              className="text-ink underline-offset-2 hover:underline"
              target="_blank"
              rel="noreferrer"
            >
              {evaluationProvenance.source_name}
            </a>{" "}
            (retrieved {evaluationProvenance.retrieval_date_utc}). This is not
            labelled as an AFL official machine-readable dump. Source HTML
            SHA256:{" "}
            <span className="font-mono">
              {evaluationProvenance.source_html_sha256.slice(0, 12)}…
            </span>
          </p>
        </div>
      </Section>

      {/* 10 — Next */}
      <Section title="What comes next">
        <div className="card shadow-card space-y-3 p-5 text-sm leading-relaxed text-muted">
          <p>
            Research directions revealed by the holdout — distinct from the
            frozen forecast product:
          </p>
          <ul className="list-disc space-y-1.5 pl-5">
            <li>Tail calibration of extreme expected-vote mass</li>
            <li>Modelling of extreme 3-vote performances</li>
            <li>Positional under / overprediction patterns</li>
            <li>Coach-versus-umpire disagreement structure</li>
            <li>Uncertainty modelling around continuous forecasts</li>
          </ul>
          <p className="pt-1">
            These are open research questions. They do not modify the frozen
            2026 forecast artifacts on Race, Players, or Matches.
          </p>
        </div>
      </Section>
    </div>
  );
}
