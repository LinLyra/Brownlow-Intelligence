"use client";

import { useMemo } from "react";
import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { playerProfiles } from "@/lib/data";
import { formatVotes, roundLabel } from "@/lib/format";
import { teamColor } from "@/lib/teams";

export function RaceChart() {
  const { data, finals, top5 } = useMemo(() => {
    const top5 = playerProfiles.slice(0, 5);
    const series = top5.map((p) => {
      let cum = 0;
      return p.rounds.map((r) => {
        cum += r.expectedBrownlowVotes;
        return {
          round: r.round,
          opponent: r.opponent,
          vote: r.expectedBrownlowVotes,
          cumulative: cum,
          player: p.player,
        };
      });
    });

    const maxGames = Math.max(...series.map((s) => s.length), 1);
    const rows = [];
    for (let g = 0; g < maxGames; g++) {
      const row: Record<string, number | string | undefined> = {
        game: g + 1,
      };
      series.forEach((s, idx) => {
        const pt = s[g];
        const key = top5[idx].player;
        if (pt) {
          row[key] = Number(pt.cumulative.toFixed(3));
          row[`${key}__round`] = pt.round;
          row[`${key}__opp`] = pt.opponent;
          row[`${key}__vote`] = pt.vote;
        }
      });
      rows.push(row);
    }

    const finalsMap = Object.fromEntries(
      top5.map((p, i) => {
        const last = series[i][series[i].length - 1];
        return [p.player, last?.cumulative ?? 0];
      })
    );

    return { data: rows, finals: finalsMap, top5 };
  }, []);

  return (
    <article className="card shadow-card p-5 md:p-6">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-[0.12em]">
            How the Race Develops
          </h2>
          <p className="mt-1 text-sm text-muted">
            Cumulative expected votes by game for the Top 5.
          </p>
        </div>
        <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs">
          {top5.map((p) => (
            <li key={p.playerId} className="flex items-center gap-1.5">
              <span
                className="inline-block h-2 w-2 rounded-full"
                style={{ background: teamColor(p.team) }}
              />
              <span className="text-muted">{p.player.split(" ").pop()}</span>
              <span className="font-medium num">
                {formatVotes(finals[p.player] ?? 0)}
              </span>
            </li>
          ))}
        </ul>
      </div>

      <div className="h-[280px] w-full md:h-[360px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <XAxis
              dataKey="game"
              tickLine={false}
              axisLine={false}
              tick={{ fill: "#64748b", fontSize: 11 }}
              ticks={[1, 5, 10, 15, 20]}
            />
            <YAxis
              tickLine={false}
              axisLine={false}
              tick={{ fill: "#64748b", fontSize: 11 }}
              width={36}
              domain={[0, "auto"]}
            />
            <Tooltip
              content={({ active, payload, label }) => {
                if (!active || !payload?.length) return null;
                return (
                  <div className="rounded-md border border-line bg-white px-3 py-2 text-xs shadow-card">
                    <p className="mb-1 font-medium text-ink">Game {label}</p>
                    <ul className="space-y-1">
                      {payload.map((item) => {
                        const name = String(item.name);
                        const pl = item.payload as Record<string, unknown>;
                        const round = pl[`${name}__round`];
                        const opp = pl[`${name}__opp`];
                        const vote = pl[`${name}__vote`];
                        return (
                          <li key={name} className="text-muted">
                            <span className="font-medium text-ink">{name}</span>
                            {round != null ? (
                              <>
                                {" "}
                                · {roundLabel(Number(round))} vs {String(opp)}
                                {" · "}+{formatVotes(Number(vote))}
                                {" · cum "}
                                {formatVotes(Number(item.value))}
                              </>
                            ) : null}
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                );
              }}
            />
            {top5.map((p) => (
              <Line
                key={p.playerId}
                type="monotone"
                dataKey={p.player}
                stroke={teamColor(p.team)}
                strokeWidth={p.rank === 1 ? 2.4 : 1.6}
                dot={false}
                activeDot={{ r: 3 }}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </article>
  );
}
