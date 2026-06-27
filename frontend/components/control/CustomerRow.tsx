import Link from "next/link";
import { money } from "@/lib/format";
import type { UserRow } from "@/lib/admin";
import { Avatar, RiskBadge } from "./atoms";

export function CustomerRow({ u }: { u: UserRow }) {
  return (
    <Link
      href={`/console/users/${u.id}`}
      className="group flex items-center gap-4 px-4 py-3.5 transition-colors hover:bg-surface/60"
    >
      <Avatar name={u.name} tint={u.is_app_user ? "var(--signal)" : "var(--ice)"} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <p className="truncate text-[0.92rem] font-semibold text-ink">{u.name}</p>
          {u.is_app_user && (
            <span className="rounded border border-signal/40 bg-signal/10 px-1.5 py-px text-[0.55rem] font-semibold uppercase tracking-wide text-signal">
              app user
            </span>
          )}
        </div>
        <p className="truncate text-[0.74rem] text-faint">
          {u.age ? `${u.age} · ` : ""}
          {u.account_number}
          {u.vulnerability_flags.length ? ` · ${u.vulnerability_flags[0].replace(/_/g, " ")}` : ""}
        </p>
      </div>

      <div className="hidden w-20 text-right sm:block">
        <p className="numeric text-[0.84rem] text-ink">{money(u.balance, u.currency)}</p>
        <p className="text-[0.66rem] text-faint">balance</p>
      </div>
      <div className="hidden w-16 text-center md:block">
        <p className="numeric text-[0.84rem] text-ink">{u.transactions}</p>
        <p className="text-[0.66rem] text-faint">transfers</p>
      </div>
      <div className="hidden w-16 text-center md:block">
        <p className="numeric text-[0.84rem]" style={{ color: u.blocked ? "var(--crimson)" : "var(--muted)" }}>
          {u.blocked}
        </p>
        <p className="text-[0.66rem] text-faint">blocked</p>
      </div>
      <div className="w-[88px] text-right">
        <RiskBadge risk={u.risk} />
      </div>
      <span className="text-faint transition group-hover:translate-x-0.5 group-hover:text-ink">→</span>
    </Link>
  );
}
