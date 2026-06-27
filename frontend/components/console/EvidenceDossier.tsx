"use client";

import { clock, money, pct } from "@/lib/format";
import type { EvidencePackage } from "@/lib/types";

// A formal, print-ready evidence dossier, intentionally "document", not "HUD".
export function EvidenceDossier({ pkg }: { pkg: EvidencePackage }) {
  const t = pkg.transaction;
  return (
    <article className="mx-auto max-w-3xl rounded-lg border border-hairline bg-surface">
      {/* Masthead */}
      <header className="flex items-start justify-between gap-4 border-b border-hairline px-7 py-6">
        <div>
          <p className="readout text-crimson">Evidence package · confidential</p>
          <h1 className="mt-2 font-display text-2xl font-semibold text-ink">
            Fraud Incident Dossier
          </h1>
          <p className="numeric mt-1 text-[0.78rem] text-faint">
            {pkg.case_id} · generated {clock(pkg.generated_at)}
          </p>
        </div>
        <button
          type="button"
          onClick={() => window.print()}
          className="rounded-md border border-hairline px-3 py-2 text-[0.74rem] text-muted transition hover:text-ink print:hidden"
        >
          Print / export
        </button>
      </header>

      <div className="flex flex-col gap-7 px-7 py-7">
        <Section n="01" title="Executive summary">
          <p className="text-[0.9rem] leading-relaxed text-muted">{pkg.executive_summary}</p>
        </Section>

        <Section n="02" title="Transaction">
          <dl className="grid grid-cols-2 gap-x-6 gap-y-3 text-[0.85rem]">
            <Field k="Amount" v={money(t.amount, t.currency)} />
            <Field k="Payee" v={t.payee_name} />
            <Field k="Beneficiary account" v={t.payee_account} mono />
            <Field k="Channel" v={t.channel} />
            <Field k="Risk score" v={`${pct(pkg.risk.score)} (${pkg.risk.band})`} />
            <Field k="Status" v={t.status} />
          </dl>
          {t.memo && (
            <p className="mt-3 rounded border-l-2 border-ember/50 bg-ember/5 px-3 py-2 text-[0.8rem] italic text-muted">
              Transfer note: “{t.memo}”
            </p>
          )}
        </Section>

        {pkg.classification && pkg.classification.archetype !== "none" && (
          <Section n="03" title="Scam classification">
            <p className="font-display text-base text-ink">{pkg.classification.title}</p>
            <p className="readout mt-1 text-crimson">
              {pct(pkg.classification.confidence)} confidence
            </p>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {pkg.classification.indicators.map((i) => (
                <span
                  key={i}
                  className="rounded border border-crimson/30 bg-crimson/5 px-2 py-0.5 text-[0.66rem] text-ember"
                >
                  {i}
                </span>
              ))}
            </div>
          </Section>
        )}

        <Section n="04" title="Risk signals">
          <ul className="flex flex-col gap-2">
            {pkg.risk.signals.map((s) => (
              <li key={s.code} className="flex items-baseline justify-between gap-4 text-[0.84rem]">
                <span className="text-ink">{s.label}</span>
                <span className="numeric text-[0.72rem] text-faint">+{Math.round(s.contribution * 100)}</span>
              </li>
            ))}
          </ul>
        </Section>

        {pkg.transcript.length > 0 && (
          <Section n="05" title="Call transcript">
            <ol className="flex flex-col gap-2">
              {pkg.transcript.map((turn) => (
                <li key={turn.index} className="text-[0.82rem] leading-relaxed">
                  <span
                    className="readout mr-2"
                    style={{ color: turn.speaker === "agent" ? "var(--signal)" : "var(--amber)" }}
                  >
                    {turn.speaker === "agent" ? "HG" : "CX"}
                  </span>
                  <span className="text-muted">{turn.text}</span>
                </li>
              ))}
            </ol>
          </Section>
        )}

        <Section n="06" title="Timeline">
          <ol className="relative ml-2 flex flex-col gap-3 border-l border-hairline pl-5">
            {pkg.timeline.map((e, i) => (
              <li key={i} className="relative">
                <span className="absolute -left-[1.42rem] top-1 h-2 w-2 rounded-full bg-ice" />
                <p className="numeric text-[0.66rem] text-faint">
                  {clock(e.at)} · {e.actor}
                </p>
                <p className="text-[0.82rem] text-muted">{e.event}</p>
              </li>
            ))}
          </ol>
        </Section>

        <Section n="07" title="Recommended actions">
          <ol className="flex flex-col gap-2">
            {pkg.recommended_actions.map((a, i) => (
              <li key={i} className="flex gap-3 text-[0.85rem] text-ink">
                <span className="numeric text-signal">{String(i + 1).padStart(2, "0")}</span>
                <span className="text-muted">{a}</span>
              </li>
            ))}
          </ol>
        </Section>
      </div>
    </article>
  );
}

function Section({ n, title, children }: { n: string; title: string; children: React.ReactNode }) {
  return (
    <section>
      <div className="mb-3 flex items-center gap-3">
        <span className="numeric text-[0.7rem] font-semibold text-faint">{n}</span>
        <h2 className="font-display text-[0.95rem] font-semibold uppercase tracking-wide text-ink">
          {title}
        </h2>
        <span className="h-px flex-1 bg-hairline" />
      </div>
      {children}
    </section>
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
