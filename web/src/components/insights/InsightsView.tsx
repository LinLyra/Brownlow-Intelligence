"use client";

import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { diagnostics } from "@/lib/data";
import { formatInt, formatPct, formatRmse } from "@/lib/format";
import { PageHeader } from "@/components/layout/PageHeader";

export function InsightsView() {
  const ablation = [
    {
      name: "Base without coach",
      rmse: diagnostics.ablation.base_no_coach,
      fill: "#94a3b8",
    },
    {
      name: "Base",
      rmse: diagnostics.ablation.base,
      fill: "#64748b",
    },
    {
      name: "Coach Intelligence",
      rmse: diagnostics.ablation.base_plus_components,
      fill: "#b8963e",
    },
  ];

  const temporal = [
    { name: "expanding_all", rmse: diagnostics.temporal.expanding_all },
    { name: "trailing_8", rmse: diagnostics.temporal.trailing_8 },
    {
      name: "exclude_2020",
      rmse: diagnostics.temporal.expanding_exclude_2020,
    },
    { name: "trailing_6", rmse: diagnostics.temporal.trailing_6 },
    { name: "trailing_4", rmse: diagnostics.temporal.trailing_4 },
  ];

  const errorByVote = diagnostics.errorByVote.map((r) => ({
    vote: String(r.actualVotes),
    mae: Number(r.mae.toFixed(3)),
    meanPred: Number(r.meanPrediction.toFixed(3)),
    n: r.n,
  }));

  return (
    <div className="page-wrap space-y-6">
      <PageHeader
        kicker="Research Findings"
        title="Insights"
        subtitle="Visual findings from validated ablation and temporal experiments. Associations are predictive — not causal claims."
      />

      {/* Section A */}
      <article className="card shadow-card p-5 md:p-6">
        <h2 className="text-sm font-semibold uppercase tracking-[0.12em]">
          A · Coach Recognition Matters
        </h2>
        <p className="mt-2 max-w-3xl text-sm text-muted leading-relaxed">
          Coach votes are a strong contemporaneous human-evaluation signal.
          Decomposing coach recognition into expected and residual components
          produced a smaller additional improvement. Do not interpret this as
          causality.
        </p>

        <div className="mt-5 grid gap-6 lg:grid-cols-[1.2fr_1fr]">
          <div className="h-[220px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={ablation}
                layout="vertical"
                margin={{ top: 4, right: 48, left: 8, bottom: 4 }}
              >
                <XAxis
                  type="number"
                  domain={[0.35, 0.375]}
                  tickLine={false}
                  axisLine={false}
                  tick={{ fill: "#64748b", fontSize: 11 }}
                />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={130}
                  tickLine={false}
                  axisLine={false}
                  tick={{ fill: "#0f172a", fontSize: 12 }}
                />
                <Tooltip
                  formatter={(v) => [formatRmse(Number(v)), "OOT RMSE"]}
                  contentStyle={{
                    borderRadius: 8,
                    border: "1px solid #e2e8f0",
                    fontSize: 12,
                  }}
                />
                <Bar dataKey="rmse" radius={[0, 4, 4, 0]} barSize={18}>
                  {ablation.map((d) => (
                    <Cell key={d.name} fill={d.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          <dl className="space-y-3 self-center">
            {ablation.map((d) => (
              <div
                key={d.name}
                className="flex items-baseline justify-between gap-3 border-b border-line pb-2 last:border-0"
              >
                <dt className="text-sm text-muted">{d.name}</dt>
                <dd className="text-base font-semibold num">{formatRmse(d.rmse)}</dd>
              </div>
            ))}
          </dl>
        </div>
      </article>

      {/* Section B */}
      <article className="card shadow-card p-5 md:p-6">
        <h2 className="text-sm font-semibold uppercase tracking-[0.12em]">
          B · What Gets Brownlow Recognition?
        </h2>
        <p className="mt-2 max-w-3xl text-sm text-muted leading-relaxed">
          Historical out-of-time diagnostics on vote strata. Zero-vote dominance
          and mean prediction by actual vote illustrate how sparse Brownlow
          recognition is — and how the model responds across the vote ladder.
        </p>

        <div className="mt-5 grid gap-4 sm:grid-cols-3">
          <div className="rounded-md border border-line px-4 py-3">
            <p className="label">Historical rows</p>
            <p className="mt-1 text-2xl font-semibold num">
              {formatInt(diagnostics.nHistoricalRows)}
            </p>
          </div>
          <div className="rounded-md border border-line px-4 py-3">
            <p className="label">Zero-vote rate</p>
            <p className="mt-1 text-2xl font-semibold num">
              {formatPct(diagnostics.zeroVoteRate)}
            </p>
          </div>
          <div className="rounded-md border border-line px-4 py-3">
            <p className="label">Champion OOT RMSE</p>
            <p className="mt-1 text-2xl font-semibold num text-gold">
              {formatRmse(diagnostics.ablation.base_plus_components)}
            </p>
          </div>
        </div>

        <div className="mt-6 h-[240px]">
          <p className="mb-2 text-xs font-medium uppercase tracking-[0.12em] text-muted">
            Mean prediction & MAE by actual Brownlow votes
          </p>
          <ResponsiveContainer width="100%" height="90%">
            <BarChart data={errorByVote} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <XAxis
                dataKey="vote"
                tickLine={false}
                axisLine={false}
                tick={{ fill: "#64748b", fontSize: 11 }}
                label={{
                  value: "Actual votes",
                  position: "insideBottom",
                  offset: -2,
                  fill: "#94a3b8",
                  fontSize: 11,
                }}
              />
              <YAxis
                tickLine={false}
                axisLine={false}
                tick={{ fill: "#64748b", fontSize: 11 }}
                width={36}
              />
              <Tooltip
                content={({ active, payload }) => {
                  if (!active || !payload?.[0]) return null;
                  const d = payload[0].payload as {
                    vote: string;
                    mae: number;
                    meanPred: number;
                    n: number;
                  };
                  return (
                    <div className="rounded-md border border-line bg-white px-3 py-2 text-xs shadow-card">
                      <p className="font-medium">Actual {d.vote} votes</p>
                      <p className="mt-1 text-muted">
                        Mean pred {d.meanPred} · MAE {d.mae} · n={formatInt(d.n)}
                      </p>
                    </div>
                  );
                }}
              />
              <Bar
                dataKey="meanPred"
                name="Mean prediction"
                fill="#0b1220"
                radius={[3, 3, 0, 0]}
              />
              <Bar
                dataKey="mae"
                name="MAE"
                fill="#b8963e"
                radius={[3, 3, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <p className="mt-2 text-xs text-muted">
          Navy = mean prediction · Gold = MAE. Supported by project diagnostics
          only — no invented performance relationships.
        </p>
      </article>

      {/* Section C */}
      <article className="card shadow-card p-5 md:p-6">
        <h2 className="text-sm font-semibold uppercase tracking-[0.12em]">
          C · Historical Data Still Matters
        </h2>
        <p className="mt-2 max-w-3xl text-sm text-muted leading-relaxed">
          Full historical training remained the strongest validated strategy.
          Trailing windows and excluding 2020 did not improve the benchmark.
        </p>

        <div className="mt-5 overflow-x-auto">
          <table className="w-full min-w-[420px] text-sm">
            <thead>
              <tr className="border-b border-line text-left text-[11px] uppercase tracking-[0.1em] text-muted">
                <th className="pb-2 font-medium">Strategy</th>
                <th className="pb-2 font-medium text-right">OOT RMSE</th>
                <th className="pb-2 pl-4 font-medium">Relative</th>
              </tr>
            </thead>
            <tbody>
              {temporal.map((t) => {
                const best = diagnostics.temporal.expanding_all;
                const width =
                  ((0.36 - t.rmse) / (0.36 - best + 0.000001)) * 100;
                return (
                  <tr
                    key={t.name}
                    className="border-b border-line/70 last:border-0"
                  >
                    <td className="py-2.5 font-medium">
                      {t.name}
                      {t.name === "expanding_all" ? (
                        <span className="ml-2 text-[10px] uppercase tracking-wider text-gold">
                          champion
                        </span>
                      ) : null}
                    </td>
                    <td className="py-2.5 text-right num font-semibold">
                      {formatRmse(t.rmse)}
                    </td>
                    <td className="py-2.5 pl-4">
                      <div className="h-1.5 w-28 overflow-hidden rounded-full bg-slate-100">
                        <div
                          className="h-full rounded-full bg-gold"
                          style={{
                            width: `${Math.max(8, Math.min(100, width))}%`,
                          }}
                        />
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </article>
    </div>
  );
}
