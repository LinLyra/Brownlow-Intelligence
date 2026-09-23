"use client";

import Link from "next/link";
import { Calendar, ChartLine, Star, Users } from "lucide-react";
import { leaderboard, modelPerformance, playerProfiles } from "@/lib/data";
import { formatInt, formatRmse, formatVotes } from "@/lib/format";
import { playerImage, positionLabel, teamAbbr, teamColor } from "@/lib/teams";
import { SITE } from "@/lib/types";
import { MetricCard } from "@/components/layout/MetricCard";
import { PageHeader } from "@/components/layout/PageHeader";
import { PlayerAvatar } from "@/components/ui/PlayerAvatar";
import { TeamBadge } from "@/components/ui/TeamBadge";
import { RaceChart } from "@/components/race/RaceChart";

function resolveImage(
  playerId: number,
  profileUrl?: string | null
): string | null {
  return profileUrl || playerImage(playerId);
}

export function RaceView() {
  const top5 = leaderboard.slice(0, 5);
  const top20 = leaderboard.slice(0, 20);
  const maxVotes = top20[0]?.expectedVotes ?? 1;
  const leader = top5[0];
  const leaderProfile = playerProfiles.find((p) => p.playerId === leader?.playerId);

  return (
    <div className="page-wrap space-y-6">
      <PageHeader
        kicker="2026 Brownlow Forecast"
        title="2026 Predicted Brownlow Race"
        subtitle={`Expected votes generated from ${formatInt(SITE.forecasts)} player-match forecasts across ${SITE.matches} matches.`}
      />

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          label="Matches"
          value={formatInt(SITE.matches)}
          icon={<Calendar size={16} />}
        />
        <MetricCard
          label="Player-Match Forecasts"
          value={formatInt(SITE.forecasts)}
          icon={<Users size={16} />}
        />
        <MetricCard
          label="Expected Votes Allocated"
          value={formatInt(SITE.totalExpectedVotes)}
          icon={<Star size={16} />}
        />
        <MetricCard
          label="Rolling OOT RMSE"
          value={formatRmse(modelPerformance.coachIntelligenceRmse)}
          icon={<ChartLine size={16} />}
        />
      </div>

      {/* #1 leader + Top 5 — single merged card, left / right */}
      <article className="card shadow-card overflow-hidden">
        <div className="grid sm:grid-cols-[1fr_1.15fr]">
          <div className="bg-navy text-white p-5 md:p-6">
            <div className="flex gap-4 items-start">
              <PlayerAvatar
                name={leader.player}
                team={leader.team}
                imageUrl={resolveImage(leader.playerId, leaderProfile?.imageUrl)}
                size="lg"
                className="!border-white/20 !bg-white/10 !text-white shrink-0"
              />
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <p className="text-[11px] font-semibold tracking-[0.16em] text-gold">
                    #1
                  </p>
                  <TeamBadge team={leader.team} size="sm" showName={false} />
                  <span className="text-xs text-white/55">
                    {teamAbbr(leader.team)}
                  </span>
                </div>
                <h2 className="mt-1 text-xl font-semibold md:text-2xl truncate">
                  {leader.player}
                </h2>
                <p className="mt-1 text-sm text-white/65">
                  {leader.team} · {positionLabel(leader.position)}
                </p>
                <p className="mt-3 text-sm text-white/75">
                  The clear favourite for 2026.
                </p>
                <div className="mt-4 grid grid-cols-2 gap-3">
                  <div>
                    <p className="text-2xl font-semibold num text-gold">
                      {formatVotes(leader.expectedVotes)}
                    </p>
                    <p className="text-[11px] uppercase tracking-[0.12em] text-white/50">
                      Expected Votes
                    </p>
                  </div>
                  <div>
                    <p className="text-2xl font-semibold num">{leader.games}</p>
                    <p className="text-[11px] uppercase tracking-[0.12em] text-white/50">
                      Projected Games
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="border-t border-line p-5 sm:border-t-0 sm:border-l sm:p-6">
            <div className="mb-4 flex items-center justify-between gap-3">
              <h2 className="text-sm font-semibold uppercase tracking-[0.12em] text-ink">
                Top 5 Contenders
              </h2>
              <a
                href="#full-top-20"
                className="text-xs font-medium text-gold hover:underline"
              >
                View Full Top 20 →
              </a>
            </div>
            <ul className="space-y-3">
              {top5.map((p) => {
                const profile = playerProfiles.find(
                  (x) => x.playerId === p.playerId
                );
                return (
                  <li key={p.playerId} className="flex items-center gap-3">
                    <span className="w-5 text-xs font-semibold text-muted num">
                      {p.rank}
                    </span>
                    <PlayerAvatar
                      name={p.player}
                      team={p.team}
                      imageUrl={resolveImage(p.playerId, profile?.imageUrl)}
                      size="sm"
                    />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-baseline justify-between gap-2">
                        <p className="truncate text-sm font-medium">
                          {p.player}
                          <span className="ml-1.5 inline-flex items-center gap-1 text-xs text-muted font-normal">
                            <TeamBadge team={p.team} size="sm" showName={false} />
                            {teamAbbr(p.team)}
                          </span>
                        </p>
                        <span className="text-sm font-semibold num shrink-0">
                          {formatVotes(p.expectedVotes)}
                        </span>
                      </div>
                      <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-slate-100">
                        <div
                          className="h-full rounded-full"
                          style={{
                            width: `${(p.expectedVotes / maxVotes) * 100}%`,
                            background: teamColor(p.team),
                          }}
                        />
                      </div>
                    </div>
                  </li>
                );
              })}
            </ul>
          </div>
        </div>
      </article>

      {/* Full Top 20 table + bars */}
      <article id="full-top-20" className="card shadow-card p-5 md:p-6">
        <h2 className="text-sm font-semibold uppercase tracking-[0.12em]">
          2026 Predicted Brownlow Leaderboard
        </h2>
        <p className="mt-1 text-sm text-muted">Full Top 20 by expected votes.</p>

        <div className="mt-5 overflow-x-auto">
          <table className="w-full min-w-[640px] text-sm">
            <thead>
              <tr className="border-b border-line text-left text-[11px] uppercase tracking-[0.12em] text-muted">
                <th className="pb-2 pr-2 font-medium">#</th>
                <th className="pb-2 pr-2 font-medium">Player</th>
                <th className="pb-2 pr-2 font-medium">Team</th>
                <th className="pb-2 pr-2 font-medium">Pos</th>
                <th className="pb-2 pr-2 font-medium text-right">Exp. Votes</th>
                <th className="pb-2 font-medium text-right">Proj. Games</th>
              </tr>
            </thead>
            <tbody>
              {top20.map((p) => {
                const profile = playerProfiles.find((x) => x.playerId === p.playerId);
                return (
                  <tr
                    key={p.playerId}
                    className="border-b border-line/70 last:border-0 hover:bg-slate-50/80"
                  >
                    <td className="py-2.5 pr-2 num text-muted">{p.rank}</td>
                    <td className="py-2.5 pr-2">
                      <div className="flex items-center gap-2">
                        <PlayerAvatar
                          name={p.player}
                          team={p.team}
                          imageUrl={resolveImage(p.playerId, profile?.imageUrl)}
                          size="sm"
                        />
                        <Link
                          href={`/players?id=${p.playerId}`}
                          className="font-medium hover:text-gold"
                        >
                          {p.player}
                        </Link>
                      </div>
                    </td>
                    <td className="py-2.5 pr-2 text-muted">
                      <TeamBadge team={p.team} size="sm" showName={false} />
                      <span className="ml-1.5">{teamAbbr(p.team)}</span>
                    </td>
                    <td className="py-2.5 pr-2 text-muted">
                      {positionLabel(p.position)}
                    </td>
                    <td className="py-2.5 pr-2 text-right">
                      <div className="inline-flex w-40 flex-col items-end gap-1">
                        <span className="font-semibold num">
                          {formatVotes(p.expectedVotes)}
                        </span>
                        <div className="h-1 w-full overflow-hidden rounded-full bg-slate-100">
                          <div
                            className="h-full rounded-full bg-gold"
                            style={{
                              width: `${(p.expectedVotes / maxVotes) * 100}%`,
                            }}
                          />
                        </div>
                      </div>
                    </td>
                    <td className="py-2.5 text-right num text-muted">{p.games}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </article>

      <RaceChart />
    </div>
  );
}
