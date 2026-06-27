import Link from "next/link";
import { money, pct, clock } from "@/lib/format";
import type { CaseSummary } from "@/lib/admin";
import { DecisionPill, bandColor } from "./atoms";

export function CaseRow({ c, showUser = true }: { c: CaseSummary; showUser?: boolean }) {
  const blocked = c.status === "blocked";
  return (
    <Link
      href={`/console/cases/${c.case_id}`}
      className="group flex items-center gap-4 px-4 py-3 transition-colors hover:bg-surface/60"
    >
      <span
        className="grid h-9 w-9 shrink-0 place-items-center rounded-lg"
        style={{ background: `color-mix(in srgb, ${bandColor(c.band)} 14%, transparent)`, color: bandColor(c.band) }}
      >
        {blocked ? "⊘" : "✓"}
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate text-[0.9rem] font-medium text-ink">{c.payee_name}</p>
        <p className="truncate text-[0.74rem] text-faint">
          {c.scam_title ?? "No scam pattern"}
          {showUser ? ` · ${c.user_name}` : ""}
        </p>
      </div>
      <div className="hidden text-right sm:block">
        <p className="numeric text-[0.84rem] text-ink">{money(c.amount, c.currency)}</p>
        <p className="numeric text-[0.68rem]" style={{ color: bandColor(c.band) }}>
          {pct(c.risk_score)} risk
        </p>
      </div>
      <DecisionPill decision={c.decision} status={c.status} />
      <span className="numeric hidden w-16 text-right text-[0.66rem] text-faint md:inline">{clock(c.created_at)}</span>
      <span className="text-faint transition group-hover:translate-x-0.5 group-hover:text-ink">→</span>
    </Link>
  );
}
