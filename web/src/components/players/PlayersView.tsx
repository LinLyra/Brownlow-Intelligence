"use client";

import { useMemo, useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import {
  Bar,
  BarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { getLeader, getProfile, leaderboard, zScoreAmongTop30 } from "@/lib/data";
import { formatVotes, roundLabel } from "@/lib/format";
import { positionLabel, playerImage, teamAbbr } from "@/lib/teams";
import { PageHeader } from "@/components/layout/PageHeader";
import { PlayerAvatar } from "@/components/ui/PlayerAvatar";
import { TeamBadge } from "@/components/ui/TeamBadge";

const STATS: { key: string; label: string }[] = [
  { key: "disposals", label: "Disposals" },
  { key: "goals", label: "Goals" },
  { key: "clearances", label: "Clearances" },
  { key: "contested_possessions", label: "Contested Possessions" },
  { key: "score_involvements", label: "Score Involvements" },
  { key: "metres_gained", label: "Metres Gained" },
];

const COMPARE_METRICS = [
  { key: "disposals", label: "Disposals" },
  { key: "contested_possessions", label: "Contested possessions" },
  { key: "clearances", label: "Clearances" },
  { key: "goals", label: "Goals" },
  { key: "score_involvements", label: "Score involvements" },
  { key: "metres_gained", label: "Metres gained" },
];

export function PlayersView() {
  const options = leaderboard.slice(0, 30);
  const search = useSearchParams();
  const initial = Number(search.get("id")) || options[0].playerId;

  const [selectedId, setSelectedId] = useState(initial);
  const [compareId, setCompareId] = useState(
    options.find((p) => p.playerId !== initial)?.playerId ?? options[1]?.playerId
  );
  const [query, setQuery] = useState("");

  useEffect(() => {
    if (Number.isFinite(initial) && initial > 0) setSelectedId(initial);
  }, [initial]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return options;
    return options.filter(
      (p) =>
        p.player.toLowerCase().includes(q) ||
        p.team.toLowerCase().includes(q) ||
        teamAbbr(p.team).toLowerCase().includes(q)
    );
  }, [options, query]);

  const leader = getLeader(selectedId) ?? options[0];
  const profile = getProfile(leader.playerId);
  const compare = getLeader(compareId);
  const compareProfile = compare ? getProfile(compare.playerId) : undefined;

  const roundBars = useMemo(() => {
    if (!profile) return [];
    return profile.rounds.map((r) => ({
      round: r.round,
      label: `R${r.round}`,
      expected: Number(r.expectedBrownlowVotes.toFixed(3)),
      opponent: r.opponent,
      coaches: r.coachesVotes,
    }));
  }, [profile]);

  const best = profile?.topPerformances.slice(0, 5) ?? [];

  const compareRows = useMemo(() => {
    if (!compare) return [];
    return COMPARE_METRICS.map((m) => ({
      ...m,
      aRaw: profile?.seasonAverages[m.key] ?? null,
      bRaw: compareProfile?.seasonAverages[m.key] ?? null,
      aZ: zScoreAmongTop30(leader.playerId, m.key),
      bZ: zScoreAmongTop30(compare.playerId, m.key),
    }));
  }, [leader.playerId, compare, profile, compareProfile]);

  const maxAbsZ = Math.max(
    1,
    ...compareRows.flatMap((r) => [Math.abs(r.aZ), Math.abs(r.bZ)])
  );

  return (
    <div className="page-wrap space-y-6">
      <PageHeader
        kicker="Player Explorer"
        title="Players"
        subtitle="Explore why individual players rank where they do — expected votes, coach recognition, and key performance context."
      />

      <div className="grid gap-4 sm:grid-cols-[240px_minmax(0,1fr)] sm:items-start">
        <aside className="card shadow-card p-4 sm:sticky sm:top-20 sm:max-h-[calc(100vh-6rem)] sm:overflow-hidden flex flex-col">
          <label className="label">Search / Select</label>
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Name or team…"
            className="mt-2 w-full rounded-md border border-line bg-white px-3 py-2 text-sm outline-none focus:border-gold"
          />
          <ul className="mt-3 flex-1 space-y-0.5 overflow-y-auto max-h-[280px] sm:max-h-none">
            {filtered.map((p) => (
              <li key={p.playerId}>
                <button
                  type="button"
                  onClick={() => setSelectedId(p.playerId)}
                  className={`flex w-full items-center gap-2 rounded-md px-2.5 py-2 text-left text-sm transition-colors ${
                    p.playerId === leader.playerId
                      ? "bg-navy text-white"
                      : "hover:bg-slate-50 text-ink"
                  }`}
                >
                  <PlayerAvatar
                    name={p.player}
                    team={p.team}
                    imageUrl={playerImage(p.playerId)}
                    size="sm"
                    className={
                      p.playerId === leader.playerId
                        ? "!border-white/20"
                        : ""
                    }
                  />
                  <span className="min-w-0 flex-1 truncate">
                    <span className="num text-xs opacity-70">#{p.rank}</span>{" "}
                    {p.player}
                  </span>
                  <span className="text-xs opacity-60 num shrink-0">
                    {formatVotes(p.expectedVotes)}
                  </span>
                </button>
              </li>
            ))}
            {filtered.length === 0 ? (
              <li className="px-2 py-3 text-sm text-muted">No players found.</li>
            ) : null}
          </ul>
        </aside>

        <div className="space-y-4 min-w-0">
          <article className="card shadow-card p-5">
            <div className="flex flex-wrap items-start gap-4">
              <PlayerAvatar
                name={leader.player}
                team={leader.team}
                imageUrl={profile?.imageUrl || playerImage(leader.playerId)}
                size="lg"
              />
              <div className="min-w-0 flex-1">
                <p className="label text-gold">Rank #{leader.rank}</p>
                <h2 className="mt-1 text-2xl font-semibold">{leader.player}</h2>
                <p className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-muted">
                  <TeamBadge team={leader.team} size="sm" />
                  <span>· {positionLabel(leader.position)} · {leader.games} games</span>
                </p>
                <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
                  <Stat label="Expected Votes" value={formatVotes(leader.expectedVotes)} accent />
                  <Stat label="Coaches Votes" value={String(leader.totalCoachesVotes)} />
                  <Stat
                    label="Avg Exp / Game"
                    value={formatVotes(leader.avgExpectedVotesPerGame)}
                  />
                  <Stat label="Games" value={String(leader.games)} />
                </div>
              </div>
            </div>

            <h3 className="mt-6 label">Statistical Summary</h3>
            <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-3">
              {STATS.map((s) => {
                const v = profile?.seasonAverages[s.key];
                return (
                  <div
                    key={s.key}
                    className="rounded-md border border-line bg-slate-50/60 px-3 py-2"
                  >
                    <p className="text-[11px] text-muted">{s.label}</p>
                    <p className="mt-0.5 text-base font-semibold num">
                      {v == null ? "—" : v.toFixed(1)}
                    </p>
                  </div>
                );
              })}
            </div>
          </article>

          <article className="card shadow-card p-5">
            <h3 className="text-sm font-semibold uppercase tracking-[0.12em]">
              Expected Votes by Round
            </h3>
            <div className="mt-4 h-[240px] md:h-[280px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={roundBars} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
                  <XAxis
                    dataKey="label"
                    tickLine={false}
                    axisLine={false}
                    tick={{ fill: "#64748b", fontSize: 10 }}
                    interval="preserveStartEnd"
                  />
                  <YAxis
                    tickLine={false}
                    axisLine={false}
                    tick={{ fill: "#64748b", fontSize: 11 }}
                    width={32}
                  />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (!active || !payload?.[0]) return null;
                      const d = payload[0].payload as {
                        round: number;
                        opponent: string;
                        expected: number;
                        coaches: number | null;
                      };
                      return (
                        <div className="rounded-md border border-line bg-white px-3 py-2 text-xs shadow-card">
                          <p className="font-medium">
                            {roundLabel(d.round)} vs {d.opponent}
                          </p>
                          <p className="mt-1 text-muted">
                            Expected {formatVotes(d.expected)}
                            {d.coaches != null
                              ? ` · Coach votes ${d.coaches}`
                              : ""}
                          </p>
                        </div>
                      );
                    }}
                  />
                  <Bar dataKey="expected" fill="#b8963e" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </article>

          <article className="card shadow-card p-5">
            <h3 className="text-sm font-semibold uppercase tracking-[0.12em]">
              Best Predicted Performances
            </h3>
            <div className="mt-3 overflow-x-auto">
              <table className="w-full min-w-[560px] text-sm">
                <thead>
                  <tr className="border-b border-line text-left text-[11px] uppercase tracking-[0.1em] text-muted">
                    <th className="pb-2 font-medium">Round</th>
                    <th className="pb-2 font-medium">Opponent</th>
                    <th className="pb-2 font-medium text-right">Exp. Votes</th>
                    <th className="pb-2 font-medium text-right">Coach</th>
                    <th className="pb-2 font-medium text-right">Disp</th>
                    <th className="pb-2 font-medium text-right">Goals</th>
                    <th className="pb-2 font-medium text-right">Clr</th>
                  </tr>
                </thead>
                <tbody>
                  {best.map((r) => (
                    <tr key={r.matchId} className="border-b border-line/70 last:border-0">
                      <td className="py-2">{roundLabel(r.round)}</td>
                      <td className="py-2 text-muted">{r.opponent}</td>
                      <td className="py-2 text-right font-semibold num">
                        {formatVotes(r.expectedBrownlowVotes)}
                      </td>
                      <td className="py-2 text-right num text-muted">
                        {r.coachesVotes ?? "—"}
                      </td>
                      <td className="py-2 text-right num text-muted">
                        {r.disposals ?? "—"}
                      </td>
                      <td className="py-2 text-right num text-muted">
                        {r.goals ?? "—"}
                      </td>
                      <td className="py-2 text-right num text-muted">
                        {r.clearances ?? "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </article>

          <article className="card shadow-card p-5">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <h3 className="text-sm font-semibold uppercase tracking-[0.12em]">
                Compare With
              </h3>
              <select
                className="rounded-md border border-line bg-white px-3 py-2 text-sm outline-none focus:border-gold"
                value={compareId}
                onChange={(e) => setCompareId(Number(e.target.value))}
              >
                {options
                  .filter((p) => p.playerId !== leader.playerId)
                  .map((p) => (
                    <option key={p.playerId} value={p.playerId}>
                      #{p.rank} {p.player}
                    </option>
                  ))}
              </select>
            </div>

            {compare ? (
              <>
                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  {[leader, compare].map((p) => (
                    <div
                      key={p.playerId}
                      className="rounded-md border border-line px-3 py-3"
                    >
                      <p className="text-xs text-muted">#{p.rank}</p>
                      <p className="font-semibold">{p.player}</p>
                      <p className="text-sm text-muted">
                        {formatVotes(p.expectedVotes)} expected ·{" "}
                        {p.totalCoachesVotes} coach votes
                      </p>
                    </div>
                  ))}
                </div>

                <div className="mt-5 space-y-3">
                  {compareRows.map((r) => (
                    <div key={r.key}>
                      <div className="mb-1 flex justify-between text-xs">
                        <span className="text-muted">{r.label}</span>
                        <span className="num text-muted">
                          {r.aRaw == null ? "—" : r.aRaw.toFixed(1)} vs{" "}
                          {r.bRaw == null ? "—" : r.bRaw.toFixed(1)}
                        </span>
                      </div>
                      <div className="relative h-7 rounded-md bg-slate-100">
                        <div className="absolute left-1/2 top-0 bottom-0 w-px bg-line" />
                        <div
                          className="absolute top-1.5 h-4 rounded-sm bg-gold"
                          style={{
                            left:
                              r.aZ >= 0
                                ? "50%"
                                : `${50 + (r.aZ / maxAbsZ) * 45}%`,
                            width: `${(Math.abs(r.aZ) / maxAbsZ) * 45}%`,
                          }}
                          title={`${leader.player} z=${r.aZ.toFixed(2)}`}
                        />
                        <div
                          className="absolute top-1.5 h-4 rounded-sm bg-navy/70"
                          style={{
                            left:
                              r.bZ >= 0
                                ? "50%"
                                : `${50 + (r.bZ / maxAbsZ) * 45}%`,
                            width: `${(Math.abs(r.bZ) / maxAbsZ) * 45}%`,
                          }}
                          title={`${compare.player} z=${r.bZ.toFixed(2)}`}
                        />
                      </div>
                    </div>
                  ))}
                  <p className="text-xs text-muted">
                    Gold = {leader.player} · Navy = {compare.player}. Zero line is
                    the Top-30 mean (field-relative z-score).
                  </p>
                </div>
              </>
            ) : null}
          </article>
        </div>
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent?: boolean;
}) {
  return (
    <div className="rounded-md border border-line px-3 py-2">
      <p className="text-[11px] text-muted">{label}</p>
      <p
        className={`mt-0.5 text-lg font-semibold num ${accent ? "text-gold" : ""}`}
      >
        {value}
      </p>
    </div>
  );
}
