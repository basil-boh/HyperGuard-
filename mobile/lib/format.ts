export function money(amount: number, currency = "SGD"): string {
  const n = new Intl.NumberFormat("en-SG", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(Math.abs(amount));
  return `${currency} ${n}`;
}

export function compact(amount: number): string {
  return new Intl.NumberFormat("en-SG", { maximumFractionDigits: 0 }).format(amount);
}

export function pct(v: number): string {
  return `${Math.round(v * 100)}%`;
}

export function initials(name: string): string {
  return name
    .split(" ")
    .map((p) => p[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

export function relativeDay(iso: string): string {
  const d = new Date(iso);
  const now = new Date();
  const days = Math.floor((now.getTime() - d.getTime()) / 86_400_000);
  if (days <= 0) return "Today";
  if (days === 1) return "Yesterday";
  if (days < 7) return `${days} days ago`;
  return d.toLocaleDateString("en-SG", { day: "numeric", month: "short" });
}

export function bandFor(score: number): string {
  if (score >= 0.85) return "critical";
  if (score >= 0.6) return "high";
  if (score >= 0.35) return "elevated";
  return "minimal";
}
