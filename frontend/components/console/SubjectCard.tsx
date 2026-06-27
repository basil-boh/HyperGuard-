"use client";

import { money } from "@/lib/format";
import type { CaseState } from "@/lib/useSwarmStream";

export function SubjectCard({ state }: { state: CaseState }) {
  const { customer, transaction } = state;
  if (!customer || !transaction) {
    return (
      <p className="text-[0.8rem] text-faint">
        No active case. Launch a scenario to load the subject and transaction under review.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-3">
        <span className="grid h-11 w-11 place-items-center rounded-lg bg-raised font-display text-base font-semibold text-ice">
          {customer.name.split(" ").map((p) => p[0]).join("")}
        </span>
        <div className="leading-tight">
          <p className="text-[0.95rem] font-semibold text-ink">{customer.name}</p>
          <p className="numeric text-[0.7rem] text-faint">{customer.phone}</p>
        </div>
      </div>

      {customer.vulnerability_flags.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {customer.vulnerability_flags.map((f) => (
            <span
              key={f}
              className="rounded border border-amber/30 bg-amber/5 px-2 py-0.5 text-[0.62rem] text-amber"
            >
              {f.replace(/_/g, " ")}
            </span>
          ))}
        </div>
      )}

      <div className="rule" />

      <dl className="flex flex-col gap-2.5">
        <Row label="Amount">
          <span className="numeric text-[0.95rem] font-semibold text-ink">
            {money(transaction.amount, transaction.currency)}
          </span>
        </Row>
        <Row label="Payee">{transaction.payee_name}</Row>
        <Row label="Account">
          <span className="numeric text-[0.78rem] text-muted">{transaction.payee_account}</span>
        </Row>
        {transaction.memo && (
          <div>
            <span className="readout">Transfer note</span>
            <p className="mt-1 rounded border-l-2 border-ember/50 bg-ember/5 px-2.5 py-1.5 text-[0.76rem] italic text-muted">
              “{transaction.memo}”
            </p>
          </div>
        )}
      </dl>
    </div>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <dt className="readout">{label}</dt>
      <dd className="text-right text-[0.84rem] text-ink">{children}</dd>
    </div>
  );
}
