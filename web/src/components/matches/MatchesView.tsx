"use client";

import { useMemo, useState, useEffect } from "react";
import { ChevronDown, ChevronLeft, ChevronRight } from "lucide-react";
import { matchPredictions } from "@/lib/data";
import { formatVotes, roundLabel } from "@/lib/format";
import { teamAbbr } from "@/lib/teams";
import { PageHeader } from "@/components/layout/PageHeader";
import { TeamBadge } from "@/components/ui/TeamBadge";

const PAGE_SIZE = 6;

export function MatchesView() {
  const rounds = useMemo(
    () =>
      Array.from(new Set(matchPredictions.map((m) => m.round))).sort(
        (a, b) => a - b
      ),
    []
  );
  const teams = useMemo(() => {
    const set = new Set<string>();
    matchPredictions.forEach((m) => {
      set.add(m.home);
      set.add(m.away);
    });
    return Array.from(set).sort();
  }, []);

  const [round, setRound] = useState<string>("all");
  const [team, setTeam] = useState<string>("all");
  const [playerQ, setPlayerQ] = useState("");
  const [openId, setOpenId] = useState<number | null>(null);
  const [page, setPage] = useState(1);

  const filtered = useMemo(() => {
    const q = playerQ.trim().toLowerCase();
    return matchPredictions.filter((m) => {
      if (round !== "all" && m.round !== Number(round)) return false;
      if (team !== "all" && m.home !== team && m.away !== team) return false;
      if (q) {
        const pool = [...m.top3, ...(m.topPlayers ?? [])];
        if (!pool.some((p) => p.playerName.toLowerCase().includes(q))) {
          return false;
        }
      }
      return true;
    });
  }, [round, team, playerQ]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));

  useEffect(() => {
    setPage(1);
    setOpenId(null);
  }, [round, team, playerQ]);

  useEffect(() => {
    if (page > pageCount) setPage(pageCount);
  }, [page, pageCount]);

  const pageItems = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  const from = filtered.length === 0 ? 0 : (page - 1) * PAGE_SIZE + 1;
  const to = Math.min(page * PAGE_SIZE, filtered.length);

  return (
    <div className="page-wrap space-y-6">
      <PageHeader
        kicker="Match Level"
        title="Matches"
        subtitle="Inspect the model at the individual-match level. Rankings show expected votes — not official 3–2–1 ballots."
      />

      <div className="card shadow-card grid gap-3 p-4 sm:grid-cols-3">
        <label className="block text-sm">
          <span className="label">Round</span>
          <select
            className="mt-1.5 w-full rounded-md border border-line bg-white px-3 py-2 text-sm outline-none focus:border-gold"
            value={round}
            onChange={(e) => setRound(e.target.value)}
          >
            <option value="all">All rounds</option>
            {rounds.map((r) => (
              <option key={r} value={r}>
                {roundLabel(r)}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-sm">
          <span className="label">Team</span>
          <select
            className="mt-1.5 w-full rounded-md border border-line bg-white px-3 py-2 text-sm outline-none focus:border-gold"
            value={team}
            onChange={(e) => setTeam(e.target.value)}
          >
            <option value="all">All teams</option>
            {teams.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-sm">
          <span className="label">Player</span>
          <input
            type="search"
            value={playerQ}
            onChange={(e) => setPlayerQ(e.target.value)}
            placeholder="Filter by player name…"
            className="mt-1.5 w-full rounded-md border border-line bg-white px-3 py-2 text-sm outline-none focus:border-gold"
          />
        </label>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 text-sm text-muted">
        <p>
          Showing {from}–{to} of {filtered.length} matches
          {filtered.length !== matchPredictions.length
            ? ` (filtered from ${matchPredictions.length})`
            : ""}
        </p>
        <div className="flex items-center gap-2">
          <button
            type="button"
            className="inline-flex items-center gap-1 rounded-md border border-line bg-white px-2.5 py-1.5 text-ink disabled:opacity-40"
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
          >
            <ChevronLeft size={14} /> Prev
          </button>
          <span className="num text-ink">
            {page} / {pageCount}
          </span>
          <button
            type="button"
            className="inline-flex items-center gap-1 rounded-md border border-line bg-white px-2.5 py-1.5 text-ink disabled:opacity-40"
            disabled={page >= pageCount}
            onClick={() => setPage((p) => Math.min(pageCount, p + 1))}
          >
            Next <ChevronRight size={14} />
          </button>
        </div>
      </div>

      <ul className="space-y-3">
        {pageItems.map((m) => {
          const open = openId === m.matchId;
          const detail = m.topPlayers?.length ? m.topPlayers : m.top3;
          const total = m.totalAllocatedExpectedVotes ?? 6;
          return (
            <li key={m.matchId} className="card shadow-card overflow-hidden">
              <button
                type="button"
                className="flex w-full items-start gap-3 p-4 text-left hover:bg-slate-50/80"
                onClick={() => setOpenId(open ? null : m.matchId)}
                aria-expanded={open}
              >
                <span className="mt-0.5 text-muted">
                  {open ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <p className="text-xs text-muted">{roundLabel(m.round)}</p>
                      <p className="mt-1 flex flex-wrap items-center gap-2 font-semibold">
                        <TeamBadge team={m.home} size="sm" />
                        <span className="font-normal text-muted">vs</span>
                        <TeamBadge team={m.away} size="sm" />
                      </p>
                    </div>
                    <p className="text-xs text-muted">
                      Total allocated expected votes ={" "}
                      <span className="font-semibold num text-ink">
                        {formatVotes(total)}
                      </span>
                    </p>
                  </div>

                  <p className="mt-3 label">Model-Ranked Top 3 · Expected Votes</p>
                  <ol className="mt-2 grid gap-1.5 sm:grid-cols-3">
                    {m.top3.map((t) => (
                      <li
                        key={`${t.modelRank}-${t.playerName}`}
                        className="rounded-md border border-line bg-slate-50/70 px-3 py-2"
                      >
                        <span className="text-xs text-gold font-semibold">
                          {t.modelRank}
                        </span>{" "}
                        <span className="text-sm font-medium">{t.playerName}</span>
                        <span className="ml-1.5 inline-flex items-center gap-1 text-xs text-muted">
                          <TeamBadge
                            team={t.playerTeam}
                            size="sm"
                            showName={false}
                          />
                          {teamAbbr(t.playerTeam)}
                        </span>
                        <p className="mt-0.5 text-sm font-semibold num">
                          {formatVotes(t.allocatedExpectedVotes)} EV
                        </p>
                      </li>
                    ))}
                  </ol>
                </div>
              </button>

              {open ? (
                <div className="border-t border-line bg-slate-50/40 px-4 py-4">
                  <p className="label mb-2">
                    Model-ranked Top {detail.length} · Expected Votes
                  </p>
                  <p className="mb-3 text-xs text-muted">
                    Continuous expected votes under the match constraint — not
                    an official ballot.
                  </p>
                  <div className="overflow-x-auto">
                    <table className="w-full min-w-[640px] text-sm">
                      <thead>
                        <tr className="border-b border-line text-left text-[11px] uppercase tracking-[0.1em] text-muted">
                          <th className="pb-2 font-medium">#</th>
                          <th className="pb-2 font-medium">Player</th>
                          <th className="pb-2 font-medium">Team</th>
                          <th className="pb-2 font-medium text-right">Exp. Votes</th>
                          <th className="pb-2 font-medium text-right">Coach</th>
                          <th className="pb-2 font-medium text-right">Disp</th>
                          <th className="pb-2 font-medium text-right">Goals</th>
                          <th className="pb-2 font-medium text-right">Clr</th>
                        </tr>
                      </thead>
                      <tbody>
                        {detail.map((t) => (
                          <tr
                            key={`${t.modelRank}-${t.playerName}`}
                            className="border-b border-line/70 last:border-0"
                          >
                            <td className="py-2 num text-muted">{t.modelRank}</td>
                            <td className="py-2 font-medium">{t.playerName}</td>
                            <td className="py-2 text-muted">
                              <TeamBadge
                                team={t.playerTeam}
                                size="sm"
                                showName={false}
                              />
                              <span className="ml-1.5">{teamAbbr(t.playerTeam)}</span>
                            </td>
                            <td className="py-2 text-right font-semibold num">
                              {formatVotes(t.allocatedExpectedVotes)}
                            </td>
                            <td className="py-2 text-right num text-muted">
                              {t.coachesVotes ?? "—"}
                            </td>
                            <td className="py-2 text-right num text-muted">
                              {t.disposals ?? "—"}
                            </td>
                            <td className="py-2 text-right num text-muted">
                              {t.goals ?? "—"}
                            </td>
                            <td className="py-2 text-right num text-muted">
                              {t.clearances ?? "—"}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : null}
            </li>
          );
        })}
      </ul>

      {filtered.length === 0 ? (
        <p className="text-sm text-muted">No matches match the current filters.</p>
      ) : (
        <div className="flex items-center justify-center gap-2">
          <button
            type="button"
            className="inline-flex items-center gap-1 rounded-md border border-line bg-white px-3 py-2 text-sm disabled:opacity-40"
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
          >
            <ChevronLeft size={14} /> Previous
          </button>
          <span className="text-sm num text-muted">
            Page {page} of {pageCount}
          </span>
          <button
            type="button"
            className="inline-flex items-center gap-1 rounded-md border border-line bg-white px-3 py-2 text-sm disabled:opacity-40"
            disabled={page >= pageCount}
            onClick={() => setPage((p) => Math.min(pageCount, p + 1))}
          >
            Next <ChevronRight size={14} />
          </button>
        </div>
      )}
    </div>
  );
}
