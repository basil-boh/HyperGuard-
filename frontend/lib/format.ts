import type { RiskBand } from "./types";

export function cn(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(" ");
}

export function money(amount: number, currency = "SGD"): string {
  return new Intl.NumberFormat("en-SG", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(amount);
}

export function pct(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function clock(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString("en-GB", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return "--:--:--";
  }
}

// Maps a band/severity to its token CSS variable so colour is derived, not hardcoded.
export const BAND_VAR: Record<RiskBand, string> = {
  minimal: "var(--signal)",
  elevated: "var(--amber)",
  high: "var(--ember)",
  critical: "var(--crimson)",
};

export function bandForScore(score: number): RiskBand {
  if (score >= 0.85) return "critical";
  if (score >= 0.6) return "high";
  if (score >= 0.35) return "elevated";
  return "minimal";
}

export const SEVERITY_VAR: Record<string, string> = {
  info: "var(--ice)",
  warn: "var(--amber)",
  alarm: "var(--crimson)",
};
