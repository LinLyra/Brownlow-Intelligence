import media from "@/data/media.json";

const TEAM_ABBR: Record<string, string> = {
  Adelaide: "ADE",
  "Brisbane Lions": "BRI",
  Carlton: "CAR",
  Collingwood: "COL",
  Essendon: "ESS",
  Fremantle: "FRE",
  Geelong: "GEE",
  "Gold Coast": "GCS",
  "Greater Western Sydney": "GWS",
  Hawthorn: "HAW",
  Melbourne: "MEL",
  "North Melbourne": "NTH",
  "Port Adelaide": "PTA",
  Richmond: "RIC",
  "St Kilda": "STK",
  Sydney: "SYD",
  "West Coast": "WCE",
  "Western Bulldogs": "WBD",
};

/** Restrained AFL accent colours for charts/bars (not full kits). */
const TEAM_COLOR: Record<string, string> = {
  Adelaide: "#002B5C",
  "Brisbane Lions": "#A30046",
  Carlton: "#0E1E2D",
  Collingwood: "#000000",
  Essendon: "#CC0000",
  Fremantle: "#2A0A54",
  Geelong: "#001F3F",
  "Gold Coast": "#E21E26",
  "Greater Western Sydney": "#FF7900",
  Hawthorn: "#4D2004",
  Melbourne: "#0F1C2E",
  "North Melbourne": "#003399",
  "Port Adelaide": "#008AAB",
  Richmond: "#FFD200",
  "St Kilda": "#ED0F05",
  Sydney: "#ED171F",
  "West Coast": "#003087",
  "Western Bulldogs": "#0054A4",
};

/** Wikimedia rejects some thumb widths (e.g. 240px → 400). Prefer 250px. */
function normalizeMediaUrl(url: string | null | undefined): string | null {
  if (!url) return null;
  return url.split("?")[0].replace(/\/240px-/g, "/250px-/");
}

export function teamAbbr(team: string): string {
  return TEAM_ABBR[team] ?? team.slice(0, 3).toUpperCase();
}

export function teamColor(team: string): string {
  return TEAM_COLOR[team] ?? "#64748b";
}

export function teamLogo(team: string): string | null {
  return normalizeMediaUrl(
    (media.teams as Record<string, string | undefined>)[team]
  );
}

export function playerImage(playerId: number): string | null {
  return normalizeMediaUrl(
    (media.players as Record<string, string | undefined>)[String(playerId)]
  );
}

export const ALL_TEAMS = Object.keys(TEAM_ABBR);

const POS_LABEL: Record<string, string> = {
  R: "MID",
  C: "MID",
  RR: "MID",
  RK: "RUC",
  FF: "FWD",
  CHF: "FWD",
  HFFL: "FWD",
  HFFR: "FWD",
  FB: "DEF",
  CHB: "DEF",
  HBFL: "DEF",
  HBFR: "DEF",
  W: "MID",
  INT: "UTIL",
};

export function positionLabel(pos: string): string {
  return POS_LABEL[pos] ?? pos;
}
