"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { ControlShell } from "@/components/control/ControlShell";
import { SectionTitle } from "@/components/control/atoms";
import { admin, type CaseDetail } from "@/lib/admin";
import { money, pct, clock } from "@/lib/format";

export default function CasePage() {
  const { id } = useParams<{ id: string }>();
  const [c, setC] = useState<CaseDetail | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    admin.case(id).then(setC).catch((e) => setErr(String(e.message ?? e)));
  }, [id]);

  if (err || !c) {
    return (
      <ControlShell crumbs={[{ label: "Control centre", href: "/console" }, { label: "Case" }]}>
        <p className={err ? "text-ember" : "readout text-faint"}>{err ? `Couldn't load case (${err}).` : "loading…"}</p>
      </ControlShell>
    );
  }

  const blocked = c.status === "blocked";
  const tint = blocked ? "var(--crimson)" : "var(--signal)";
  const t = c.transaction;

  return (
    <ControlShell
      crumbs={[
        { label: "Control centre", href: "/console" },
        { label: c.user_name, href: `/console/users/${c.user_id}` },
        { label: c.case_id },
      ]}
    >
      {/* Verdict banner */}
      <div className="overflow-hidden rounded-xl border p-6" style={{ borderColor: tint, background: `color-mix(in srgb, ${tint} 8%, transparent)` }}>
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <span className="grid h-14 w-14 place-items-center rounded-full border-2 text-2xl" style={{ borderColor: tint, color: tint }}>
              {blocked ? "⊘" : "✓"}
            </span>
            <div>
              <p className="font-display text-xl font-semibold" style={{ color: tint }}>
                {blocked ? "Transfer blocked" : "Transfer approved"}
              </p>
              <p className="numeric mt-1 text-[0.74rem] text-faint">
                {c.case_id} · {clock(c.created_at)}
              </p>
            </div>
          </div>
          <div className="text-right">
            <p className="numeric text-2xl font-bold text-ink">{money(c.amount, c.currency)}</p>
            <p className="text-[0.78rem] text-muted">to {c.payee_name}</p>
          </div>
        </div>
        <p className="mt-4 max-w-3xl text-[0.9rem] leading-relaxed text-muted">{c.narrative}</p>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        {/* Left: transaction, risk, classification */}
        <div className="flex flex-col gap-6">
          <section>
            <SectionTitle>Transaction</SectionTitle>
            <dl className="grid grid-cols-2 gap-x-6 gap-y-3 rounded-lg border border-hairline bg-surface/40 p-5 text-[0.85rem]">
              <Field k="Customer" v={c.user_name} />
              <Field k="Amount" v={money(c.amount, c.currency)} />
              <Field k="Payee" v={c.payee_name} />
              <Field k="Beneficiary acct" v={t.payee_account ?? "—"} mono />
              <Field k="Channel" v={t.channel ?? "—"} />
              <Field k="Risk" v={`${pct(c.risk_score)} · ${c.band}`} />
            </dl>
            {t.memo && (
              <p className="mt-2 rounded border-l-2 border-ember/50 bg-ember/5 px-3 py-2 text-[0.8rem] italic text-muted">
                Transfer note: “{t.memo}”
              </p>
            )}
          </section>

          <section>
            <SectionTitle>Risk signals</SectionTitle>
            <div className="flex flex-col gap-3 rounded-lg border border-hairline bg-surface/40 p-5">
              {c.risk_signals.map((s) => (
                <div key={s.code}>
                  <div className="flex items-baseline justify-between gap-3">
                    <span className="text-[0.84rem] text-ink">{s.label}</span>
                    <span className="numeric text-[0.7rem] text-faint">+{Math.round(s.contribution * 100)}</span>
                  </div>
                  <p className="mt-0.5 text-[0.72rem] text-faint">{s.detail}</p>
                </div>
              ))}
            </div>
          </section>

          {c.classification && c.classification.archetype !== "none" && (
            <section>
              <SectionTitle>Scam classification</SectionTitle>
              <div className="rounded-lg border p-5" style={{ borderColor: "color-mix(in srgb, var(--crimson) 40%, transparent)" }}>
                <div className="flex items-start justify-between">
                  <p className="font-display text-base font-semibold text-ink">{c.classification.title}</p>
                  <span className="numeric text-lg font-bold text-crimson">{pct(c.classification.confidence)}</span>
                </div>
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {c.classification.indicators.map((i) => (
                    <span key={i} className="rounded border border-crimson/30 bg-crimson/5 px-2 py-0.5 text-[0.66rem] text-ember">
                      {i}
                    </span>
                  ))}
                </div>
                <p className="mt-3 border-l-2 border-signal bg-signal/5 px-3 py-2 text-[0.8rem] leading-relaxed text-ink">
                  {c.classification.guidance}
                </p>
              </div>
            </section>
          )}
        </div>

        {/* Right: transcript, guardians */}
        <div className="flex flex-col gap-6">
          <section>
            <SectionTitle>Call transcript</SectionTitle>
            <div className="flex flex-col gap-3 rounded-lg border border-hairline bg-surface/40 p-5">
              {c.transcript.length === 0 && <p className="text-[0.82rem] text-faint">No call (post-hoc case).</p>}
              {c.transcript.map((turn) => {
                const me = turn.speaker === "customer";
                return (
                  <div key={turn.index} className={me ? "items-end self-end text-right" : "self-start"}>
                    <span className="readout" style={{ color: me ? "var(--amber)" : "var(--signal)" }}>
                      {me ? "Customer" : "HyperGuard"}
                    </span>
                    <p
                      className="mt-1 max-w-[92%] rounded-lg px-3 py-2 text-[0.84rem] leading-relaxed text-ink"
                      style={{
                        background: me ? "var(--raised)" : "color-mix(in srgb, var(--signal) 8%, transparent)",
                        borderLeft: me ? "none" : "2px solid var(--signal)",
                        borderRight: me ? "2px solid var(--amber)" : "none",
                        display: "inline-block",
                      }}
                    >
                      {turn.text}
                    </p>
                  </div>
                );
              })}
            </div>
          </section>

          <section>
            <SectionTitle>Guardian escalation</SectionTitle>
            <div className="flex flex-col gap-2.5">
              {c.guardian_alerts.map((a, i) => (
                <div key={i} className="rounded-lg border border-hairline bg-surface/40 p-4" style={{ borderLeft: `2px solid ${a.acknowledged ? "var(--signal)" : "var(--amber)"}` }}>
                  <div className="flex items-center justify-between">
                    <p className="text-[0.86rem] font-medium text-ink">
                      {a.contact.name} <span className="font-normal capitalize text-faint">· {a.contact.relationship}</span>
                    </p>
                    <span className="text-[0.6rem] font-semibold uppercase tracking-wide" style={{ color: a.acknowledged ? "var(--signal)" : "var(--amber)" }}>
                      {a.acknowledged ? "acknowledged" : a.status}
                    </span>
                  </div>
                  <p className="mt-2 text-[0.76rem] leading-snug text-muted">{a.message}</p>
                </div>
              ))}
              {c.guardian_alerts.length === 0 && <p className="text-[0.82rem] text-faint">No escalation was required.</p>}
            </div>
          </section>
        </div>
      </div>
    </ControlShell>
  );
}

function Field({ k, v, mono }: { k: string; v: string; mono?: boolean }) {
  return (
    <div>
      <dt className="readout">{k}</dt>
      <dd className={`mt-0.5 text-ink ${mono ? "numeric text-[0.8rem]" : ""}`}>{v}</dd>
    </div>
  );
}
