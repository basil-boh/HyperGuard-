"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ControlShell } from "@/components/control/ControlShell";
import { Avatar, DecisionPill, MetricTile, SectionTitle, bandColor } from "@/components/control/atoms";
import { admin, type UserDetail } from "@/lib/admin";
import { money, pct, clock } from "@/lib/format";

export default function CustomerPage() {
  const { id } = useParams<{ id: string }>();
  const [d, setD] = useState<UserDetail | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    admin.user(id).then(setD).catch((e) => setErr(String(e.message ?? e)));
  }, [id]);

  if (err) {
    return (
      <ControlShell crumbs={[{ label: "Control centre", href: "/console" }, { label: "Customer" }]}>
        <p className="text-ember">Couldn't load customer ({err}).</p>
      </ControlShell>
    );
  }
  if (!d) {
    return (
      <ControlShell crumbs={[{ label: "Control centre", href: "/console" }, { label: "Customer" }]}>
        <p className="readout text-faint">loading…</p>
      </ControlShell>
    );
  }

  const p = d.profile;
  return (
    <ControlShell crumbs={[{ label: "Control centre", href: "/console" }, { label: p.name }]}>
      {/* Profile */}
      <div className="flex flex-col gap-5 rounded-xl border border-hairline bg-surface/60 p-6 sm:flex-row sm:items-center">
        <Avatar name={p.name} size={64} />
        <div className="flex-1">
          <h1 className="font-display text-2xl font-semibold tracking-tight text-ink">{p.name}</h1>
          <p className="numeric mt-1 text-[0.82rem] text-faint">
            {p.age ? `${p.age} yrs · ` : ""}
            {p.phone} · {d.account.account_number}
          </p>
          {p.vulnerability_flags.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-1.5">
              {p.vulnerability_flags.map((f) => (
                <span key={f} className="rounded border border-amber/30 bg-amber/5 px-2 py-0.5 text-[0.64rem] text-amber">
                  {f.replace(/_/g, " ")}
                </span>
              ))}
            </div>
          )}
        </div>
        <div className="text-right">
          <p className="numeric text-2xl font-bold text-ink">{money(d.account.balance, d.account.currency)}</p>
          <p className="readout mt-1">balance</p>
        </div>
      </div>

      {/* Metrics */}
      <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <MetricTile label="Transfers" value={String(d.metrics.transactions)} />
        <MetricTile label="Approved" value={String(d.metrics.succeeded)} accent="var(--signal)" />
        <MetricTile label="Intervened" value={String(d.metrics.blocked)} accent="var(--crimson)" />
        <MetricTile label="Protected" value={money(d.metrics.protected).replace(".00", "")} accent="var(--signal)" />
      </div>

      <div className="mt-7 grid gap-6 lg:grid-cols-[1.6fr_1fr]">
        {/* Transactions */}
        <section>
          <SectionTitle>Transaction ledger</SectionTitle>
          <div className="divide-y divide-hairline overflow-hidden rounded-lg border border-hairline bg-surface/40">
            {d.transactions.map((t) => {
              const blocked = t.status === "blocked";
              const inbound = t.direction === "in";
              const body = (
                <div className="flex items-center gap-3 px-4 py-3">
                  <span
                    className="grid h-8 w-8 shrink-0 place-items-center rounded-lg text-[0.8rem]"
                    style={{
                      background: blocked ? "color-mix(in srgb, var(--crimson) 14%, transparent)" : "var(--raised)",
                      color: blocked ? "var(--crimson)" : inbound ? "var(--signal)" : "var(--ice)",
                    }}
                  >
                    {blocked ? "⊘" : inbound ? "↓" : "↑"}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-[0.86rem] font-medium text-ink">{t.counterparty}</p>
                    <p className="truncate text-[0.72rem] text-faint">
                      {t.scam_type ? t.scam_type.replace(/_/g, " ") : t.memo || clock(t.ts)}
                    </p>
                  </div>
                  {t.risk_score != null && (
                    <span className="numeric hidden text-[0.7rem] sm:inline" style={{ color: t.risk_score >= 0.6 ? "var(--crimson)" : "var(--faint)" }}>
                      {pct(t.risk_score)}
                    </span>
                  )}
                  <span className="numeric w-24 text-right text-[0.84rem]" style={{ color: blocked ? "var(--faint)" : inbound ? "var(--signal)" : "var(--ink)", textDecoration: blocked ? "line-through" : "none" }}>
                    {inbound ? "+" : "−"}
                    {money(t.amount).replace("SGD ", "")}
                  </span>
                  <DecisionPill decision={t.decision} status={t.status} />
                  {t.case_id && <span className="text-faint">→</span>}
                </div>
              );
              return t.case_id ? (
                <Link key={t.id} href={`/console/cases/${t.case_id}`} className="block transition-colors hover:bg-surface/60">
                  {body}
                </Link>
              ) : (
                <div key={t.id}>{body}</div>
              );
            })}
          </div>
        </section>

        {/* Guardians + escalations */}
        <div className="flex flex-col gap-6">
          <section>
            <SectionTitle>Guardian network</SectionTitle>
            <div className="flex flex-col gap-2.5">
              {d.guardians.map((g) => (
                <div key={g.id} className="flex items-center gap-3 rounded-lg border border-hairline bg-surface/40 p-3">
                  <Avatar name={g.name} size={36} tint="var(--ice)" />
                  <div className="flex-1">
                    <p className="text-[0.86rem] font-medium text-ink">{g.name}</p>
                    <p className="numeric text-[0.7rem] capitalize text-faint">{g.relationship} · {g.phone}</p>
                  </div>
                  {g.priority === 1 && (
                    <span className="rounded bg-ice/15 px-1.5 py-0.5 text-[0.58rem] font-bold uppercase text-ice">1st</span>
                  )}
                </div>
              ))}
              {d.guardians.length === 0 && <p className="text-[0.82rem] text-faint">No guardians enrolled.</p>}
            </div>
          </section>

          <section>
            <SectionTitle>Escalations</SectionTitle>
            <div className="flex flex-col gap-2.5">
              {d.escalations.map((e, i) => (
                <Link
                  key={i}
                  href={`/console/cases/${e.case_id}`}
                  className="block rounded-lg border border-hairline bg-surface/40 p-3 transition-colors hover:bg-surface/70"
                  style={{ borderLeft: `2px solid ${e.acknowledged ? "var(--signal)" : "var(--amber)"}` }}
                >
                  <div className="flex items-center justify-between">
                    <p className="text-[0.84rem] font-medium text-ink">{e.contact.name}</p>
                    <span className="text-[0.6rem] font-semibold uppercase tracking-wide" style={{ color: e.acknowledged ? "var(--signal)" : "var(--amber)" }}>
                      {e.acknowledged ? "acknowledged" : e.status}
                    </span>
                  </div>
                  <p className="mt-1 text-[0.72rem] text-faint">re: {e.payee} · {clock(e.at)}</p>
                </Link>
              ))}
              {d.escalations.length === 0 && <p className="text-[0.82rem] text-faint">No escalations on file.</p>}
            </div>
          </section>
        </div>
      </div>
    </ControlShell>
  );
}
