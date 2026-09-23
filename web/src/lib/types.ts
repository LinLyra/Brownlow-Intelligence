export type LeaderboardPlayer = {
  rank: number;
  playerId: number;
  player: string;
  team: string;
  position: string;
  games: number;
  expectedVotes: number;
  totalCoachesVotes: number;
  avgExpectedVotesPerGame: number;
};

export type RoundPerformance = {
  round: number;
  matchId: number;
  matchDate: string | null;
  opponent: string;
  expectedBrownlowVotes: number;
  coachesVotes: number | null;
  disposals?: number | null;
  goals?: number | null;
  clearances?: number | null;
  contestedPossessions?: number | null;
  scoreInvolvements?: number | null;
  metresGained?: number | null;
  supercoachScore?: number | null;
  aflFantasyScore?: number | null;
  ratingPoints?: number | null;
  tackles?: number | null;
};

export type PlayerProfile = {
  rank: number;
  playerId: number;
  player: string;
  team: string;
  position: string;
  games: number;
  expectedVotes: number;
  imageUrl: string | null;
  seasonAverages: Record<string, number>;
  rounds: RoundPerformance[];
  topPerformances: RoundPerformance[];
};

export type MatchPlayerRank = {
  modelRank: number;
  playerId?: number;
  playerName: string;
  playerTeam: string;
  position?: string;
  allocatedExpectedVotes: number;
  coachesVotes?: number | null;
  disposals?: number | null;
  goals?: number | null;
  clearances?: number | null;
  contestedPossessions?: number | null;
  scoreInvolvements?: number | null;
};

export type MatchTop3 = {
  matchId: number;
  round: number;
  home: string;
  away: string;
  label: string;
  matchDate?: string | null;
  totalAllocatedExpectedVotes?: number;
  top3: MatchPlayerRank[];
  topPlayers?: MatchPlayerRank[];
};

export type ModelPerformance = {
  originalBaseRmse: number;
  coachIntelligenceRmse: number;
  championExperiment: string;
  temporalStrategy: string;
  foldRmse: Record<string, number>;
  metric: string;
};

export type Diagnostics = {
  zeroVoteRate: number;
  nHistoricalRows: number;
  errorByVote: {
    actualVotes: number;
    mae: number;
    n: number;
    meanPrediction: number;
  }[];
  ablation: {
    base: number;
    base_no_coach: number;
    base_plus_components: number;
  };
  temporal: {
    expanding_all: number;
    trailing_8: number;
    expanding_exclude_2020: number;
    trailing_6: number;
    trailing_4: number;
  };
};

export type Methodology = {
  project: string;
  objective: string;
  validation: string;
  coachIntelligence: string;
  features: string;
  model: string;
  constraint: string;
  finalTraining: string;
  verifiedOotRmse: { base: number; champion: number };
};

export const SITE = {
  shortName: "BIS 2026",
  title: "Brownlow Intelligence",
  productName: "Brownlow Intelligence System",
  brand: "LLyra",
  brandTag: "Sports Intelligence",
  matches: 207,
  forecasts: 9522,
  totalExpectedVotes: 1242,
  featureCount: 178,
  numericFeatures: 173,
  categoricalFeatures: 5,
  trainingYears: "2015–2025",
  forecastYear: 2026,
  githubUrl: null as string | null,
  portfolioUrl: null as string | null,
  linkedinUrl: null as string | null,
};

export const NAV_ITEMS = [
  { href: "/race", label: "Race" },
  { href: "/players", label: "Players" },
  { href: "/matches", label: "Matches" },
  { href: "/insights", label: "Insights" },
  { href: "/methodology", label: "Methodology" },
] as const;
