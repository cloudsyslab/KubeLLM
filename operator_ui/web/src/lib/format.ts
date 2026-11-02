const integer = new Intl.NumberFormat("en-US");

export const count = (value: number) => integer.format(value);

export function pct(value: number | null | undefined, digits = 1): string {
  return typeof value === "number" ? `${(value * 100).toFixed(digits)}%` : "—";
}

export function duration(seconds: number | null | undefined): string {
  if (typeof seconds !== "number" || !Number.isFinite(seconds)) return "—";
  if (seconds < 59.5) return `${seconds.toFixed(seconds < 10 ? 1 : 0)}s`;
  const whole = Math.round(seconds);
  const minutes = Math.floor(whole / 60);
  if (minutes < 60) return `${minutes}m ${String(whole % 60).padStart(2, "0")}s`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ${String(minutes % 60).padStart(2, "0")}m`;
}

export function usd(value: number | null | undefined): string {
  if (typeof value !== "number") return "—";
  if (value === 0) return "$0";
  if (value < 0.01) return `$${value.toFixed(4)}`;
  if (value < 1) return `$${value.toFixed(3)}`;
  return `$${value.toFixed(2)}`;
}

export function compact(value: number | null | undefined): string {
  if (typeof value !== "number") return "—";
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(value >= 10_000 ? 0 : 1)}k`;
  return integer.format(Math.round(value));
}

// Run IDs are ISO-like timestamps (2026-09-23T00-57-28).
export function runDate(runId: string): string {
  const match = runId.match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2})-(\d{2})/);
  if (!match) return runId;
  const [, y, m, d, hh, mm] = match;
  const date = new Date(Date.UTC(Number(y), Number(m) - 1, Number(d), Number(hh), Number(mm)));
  return `${date.toLocaleDateString("en-US", { month: "short", day: "numeric", timeZone: "UTC" })} · ${hh}:${mm}`;
}
