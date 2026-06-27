import { cn } from "@/lib/format";

// Risk band → token colour.
const BAND: Record<string, string> = {
  minimal: "var(--signal)",
  elevated: "var(--amber)",
  high: "var(--ember)",
  critical: "var(--crimson)",
};
const RISK: Record<string, { c: string; label: string }> = {
  clear: { c: "var(--signal)", label: "Clear" },
  elevated: { c: "var(--amber)", label: "Elevated" },
  watch: { c: "var(--crimson)", label: "Watch" },
};

export function bandColor(band: string) {
  return BAND[band] ?? "var(--faint)";
}

export function MetricTile({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: string;
  sub?: string;
  accent?: string;
}) {
  return (
    <div className="relative overflow-hidden rounded-lg border border-hairline bg-surface/70 p-5">
      {accent && (
        <span className="absolute left-0 top-0 h-full w-[3px]" style={{ background: accent }} />
      )}
      <span className="readout">{label}</span>
      <p className="numeric mt-2 text-3xl font-bold tracking-tight text-ink" style={accent ? { color: accent } : undefined}>
        {value}
      </p>
      {sub && <p className="mt-1 text-[0.76rem] text-faint">{sub}</p>}
    </div>
  );
}

export function RiskBadge({ risk }: { risk: string }) {
  const r = RISK[risk] ?? RISK.clear;
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[0.62rem] font-semibold uppercase tracking-wider"
      style={{ color: r.c, background: `color-mix(in srgb, ${r.c} 14%, transparent)` }}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: r.c }} />
      {r.label}
    </span>
  );
}

export function DecisionPill({ decision, status }: { decision: string | null; status?: string }) {
  const blocked = decision === "block" || status === "blocked";
  const c = blocked ? "var(--crimson)" : decision === "approve" ? "var(--signal)" : "var(--amber)";
  const label = blocked ? "Blocked" : decision === "approve" ? "Approved" : status === "completed" ? "Cleared" : "Held";
  return (
    <span
      className="inline-flex items-center rounded-md px-2 py-0.5 text-[0.66rem] font-semibold uppercase tracking-wide"
      style={{ color: c, background: `color-mix(in srgb, ${c} 13%, transparent)` }}
    >
      {label}
    </span>
  );
}

export function SectionTitle({ children, right }: { children: React.ReactNode; right?: React.ReactNode }) {
  return (
    <div className="mb-3 flex items-center justify-between">
      <span className="readout">{children}</span>
      {right}
    </div>
  );
}

export function Avatar({ name, tint, size = 40 }: { name: string; tint?: string; size?: number }) {
  const ini = name.split(" ").map((p) => p[0]).slice(0, 2).join("").toUpperCase();
  return (
    <span
      className={cn("grid shrink-0 place-items-center rounded-lg bg-raised font-display font-semibold")}
      style={{ width: size, height: size, color: tint ?? "var(--ice)", fontSize: size * 0.34 }}
    >
      {ini}
    </span>
  );
}
