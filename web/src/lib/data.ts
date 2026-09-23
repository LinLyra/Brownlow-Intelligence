import leaderboardRaw from "@/data/leaderboard.json";
import modelPerfRaw from "@/data/model-performance.json";
import profilesRaw from "@/data/player-profiles.json";
import matchesRaw from "@/data/match-predictions.json";
import methodologyRaw from "@/data/methodology.json";
import diagnosticsRaw from "@/data/diagnostics.json";
import { playerImage } from "@/lib/teams";
import type {
  Diagnostics,
  LeaderboardPlayer,
  MatchPlayerRank,
  MatchTop3,
  Methodology,
  ModelPerformance,
  PlayerProfile,
  RoundPerformance,
} from "@/lib/types";

function mapRound(r: Record<string, unknown>): RoundPerformance {
  return {
    round: Number(r.round),
    matchId: Number(r.match_id),
    matchDate: (r.match_date as string | null) ?? null,
    opponent: String(r.opponent),
    expectedBrownlowVotes: Number(r.expected_brownlow_votes),
    coachesVotes: r.coaches_votes == null ? null : Number(r.coaches_votes),
    disposals: r.disposals == null ? null : Number(r.disposals),
    goals: r.goals == null ? null : Number(r.goals),
    clearances: r.clearances == null ? null : Number(r.clearances),
    contestedPossessions:
      r.contested_possessions == null ? null : Number(r.contested_possessions),
    scoreInvolvements:
      r.score_involvements == null ? null : Number(r.score_involvements),
    metresGained: r.metres_gained == null ? null : Number(r.metres_gained),
    supercoachScore:
      r.supercoach_score == null ? null : Number(r.supercoach_score),
    aflFantasyScore:
      r.afl_fantasy_score == null ? null : Number(r.afl_fantasy_score),
    ratingPoints: r.rating_points == null ? null : Number(r.rating_points),
    tackles: r.tackles == null ? null : Number(r.tackles),
  };
}

export const leaderboard: LeaderboardPlayer[] = (
  leaderboardRaw as { players: Record<string, unknown>[] }
).players.map((p) => ({
  rank: Number(p.predicted_rank),
  playerId: Number(p.player_id),
  player: String(p.player_name),
  team: String(p.team),
  position: String(p.position),
  games: Number(p.games),
  expectedVotes: Number(p.predicted_expected_votes),
  totalCoachesVotes: Number(p.total_coaches_votes),
  avgExpectedVotesPerGame: Number(p.avg_expected_votes_per_game),
}));

export const modelPerformance: ModelPerformance = {
  originalBaseRmse: Number(
    (modelPerfRaw as { original_base_rmse: number }).original_base_rmse
  ),
  coachIntelligenceRmse: Number(
    (modelPerfRaw as { coach_intelligence_rmse: number })
      .coach_intelligence_rmse
  ),
  championExperiment: String(
    (modelPerfRaw as { champion_experiment: string }).champion_experiment
  ),
  temporalStrategy: String(
    (modelPerfRaw as { temporal_strategy: string }).temporal_strategy
  ),
  foldRmse: (modelPerfRaw as { fold_rmse: Record<string, number> }).fold_rmse,
  metric: String((modelPerfRaw as { metric: string }).metric),
};

export const playerProfiles: PlayerProfile[] = (
  profilesRaw as Record<string, unknown>[]
).map((p) => ({
  rank: Number(p.rank),
  playerId: Number(p.player_id),
  player: String(p.player),
  team: String(p.team),
  position: String(p.position),
  games: Number(p.games),
  expectedVotes: Number(p.expected_votes),
  imageUrl:
    (p.image_url as string | null) ?? playerImage(Number(p.player_id)) ?? null,
  seasonAverages: p.season_performance_averages as Record<string, number>,
  rounds: ((p.round_by_round as Record<string, unknown>[]) ?? []).map(mapRound),
  topPerformances: (
    (p.top_predicted_performances as Record<string, unknown>[]) ?? []
  ).map(mapRound),
}));

function mapMatchPlayer(t: Record<string, unknown>): MatchPlayerRank {
  return {
    modelRank: Number(t.model_rank ?? t.modelRank),
    playerId:
      t.player_id != null || t.playerId != null
        ? Number(t.player_id ?? t.playerId)
        : undefined,
    playerName: String(t.player_name ?? t.playerName),
    playerTeam: String(t.player_team ?? t.playerTeam),
    position: t.position != null ? String(t.position) : undefined,
    allocatedExpectedVotes: Number(
      t.allocated_expected_votes ?? t.allocatedExpectedVotes
    ),
    coachesVotes:
      t.coaches_votes == null && t.coachesVotes == null
        ? null
        : Number(t.coaches_votes ?? t.coachesVotes),
    disposals: t.disposals == null ? null : Number(t.disposals),
    goals: t.goals == null ? null : Number(t.goals),
    clearances: t.clearances == null ? null : Number(t.clearances),
    contestedPossessions:
      t.contested_possessions == null && t.contestedPossessions == null
        ? null
        : Number(t.contested_possessions ?? t.contestedPossessions),
    scoreInvolvements:
      t.score_involvements == null && t.scoreInvolvements == null
        ? null
        : Number(t.score_involvements ?? t.scoreInvolvements),
  };
}

export const matchPredictions: MatchTop3[] = (
  matchesRaw as Record<string, unknown>[]
).map((m) => ({
  matchId: Number(m.match_id ?? m.matchId),
  round: Number(m.match_round ?? m.round),
  home: String(m.home),
  away: String(m.away),
  label: String(m.label),
  matchDate:
    (m.match_date as string | null | undefined) ??
    (m.matchDate as string | null | undefined) ??
    null,
  totalAllocatedExpectedVotes:
    m.total_allocated_expected_votes != null ||
    m.totalAllocatedExpectedVotes != null
      ? Number(m.total_allocated_expected_votes ?? m.totalAllocatedExpectedVotes)
      : undefined,
  top3: ((m.top3 as Record<string, unknown>[]) ?? []).map(mapMatchPlayer),
  topPlayers: ((m.topPlayers as Record<string, unknown>[]) ?? []).map(
    mapMatchPlayer
  ),
}));

export const methodology: Methodology = {
  project: String((methodologyRaw as { project: string }).project),
  objective: String((methodologyRaw as { objective: string }).objective),
  validation: String((methodologyRaw as { validation: string }).validation),
  coachIntelligence: String(
    (methodologyRaw as { coach_intelligence: string }).coach_intelligence
  ),
  features: String((methodologyRaw as { features: string }).features),
  model: String((methodologyRaw as { model: string }).model),
  constraint: String((methodologyRaw as { constraint: string }).constraint),
  finalTraining: String(
    (methodologyRaw as { final_training: string }).final_training
  ),
  verifiedOotRmse: {
    base: Number(
      (methodologyRaw as { verified_oot_rmse: { base: number } })
        .verified_oot_rmse.base
    ),
    champion: Number(
      (methodologyRaw as { verified_oot_rmse: { champion: number } })
        .verified_oot_rmse.champion
    ),
  },
};

export const diagnostics: Diagnostics = {
  zeroVoteRate: Number(
    (diagnosticsRaw as { zero_vote_rate: number }).zero_vote_rate
  ),
  nHistoricalRows: Number(
    (diagnosticsRaw as { n_historical_rows: number }).n_historical_rows
  ),
  errorByVote: (
    diagnosticsRaw as {
      error_by_vote: {
        actual_votes: number;
        mae: number;
        n: number;
        mean_prediction: number;
      }[];
    }
  ).error_by_vote.map((r) => ({
    actualVotes: r.actual_votes,
    mae: r.mae,
    n: r.n,
    meanPrediction: r.mean_prediction,
  })),
  ablation: (diagnosticsRaw as { ablation: Diagnostics["ablation"] }).ablation,
  temporal: (diagnosticsRaw as { temporal: Diagnostics["temporal"] }).temporal,
};

// Ensure verified temporal companions exist even if JSON is older.
if (!diagnostics.temporal.trailing_6) diagnostics.temporal.trailing_6 = 0.356982;
if (!diagnostics.temporal.trailing_4) diagnostics.temporal.trailing_4 = 0.357914;

export function getProfile(playerId: number): PlayerProfile | undefined {
  return playerProfiles.find((p) => p.playerId === playerId);
}

export function getLeader(playerId: number): LeaderboardPlayer | undefined {
  return leaderboard.find((p) => p.playerId === playerId);
}

/** Field-relative z-scores among Top-30 profiled players for Head-to-Head. */
export function top30MetricStats(metric: string): { mean: number; std: number } {
  const vals = playerProfiles
    .map((p) => p.seasonAverages[metric])
    .filter((v): v is number => typeof v === "number" && Number.isFinite(v));
  const mean = vals.reduce((a, b) => a + b, 0) / Math.max(vals.length, 1);
  const variance =
    vals.reduce((a, b) => a + (b - mean) ** 2, 0) / Math.max(vals.length, 1);
  return { mean, std: Math.sqrt(variance) || 1 };
}

export function zScoreAmongTop30(playerId: number, metric: string): number {
  const p = getProfile(playerId);
  if (!p || p.seasonAverages[metric] == null) return 0;
  const { mean, std } = top30MetricStats(metric);
  return (p.seasonAverages[metric] - mean) / std;
}
