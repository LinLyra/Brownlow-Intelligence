export function formatVotes(n: number, digits = 2): string {
  return n.toFixed(digits);
}

export function formatInt(n: number): string {
  return new Intl.NumberFormat("en-AU").format(n);
}

export function formatPct(n: number, digits = 1): string {
  return `${(n * 100).toFixed(digits)}%`;
}

export function formatRmse(n: number): string {
  return n.toFixed(6);
}

export function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase() ?? "")
    .join("");
}

export function slugify(name: string): string {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
}

export function roundLabel(round: number): string {
  return `Round ${round}`;
}
