"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ControlShell } from "@/components/control/ControlShell";
import { MetricTile, SectionTitle } from "@/components/control/atoms";
import { CaseRow } from "@/components/control/CaseRow";
import { CustomerRow } from "@/components/control/CustomerRow";
import { admin, type Overview, type UserRow } from "@/lib/admin";
import { money } from "@/lib/format";

export default function ControlCentre() {
  const [ov, setOv] = useState<Overview | null>(null);
  const [users, setUsers] = useState<UserRow[]>([]);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    admin.overview().then(setOv).catch((e) => setErr(String(e.message ?? e)));
    admin.users().then(setUsers).catch(() => {});
  }, []);

  return (
    <ControlShell>
      <div className="mb-7">
        <h1 className="font-display text-2xl font-semibold tracking-tight text-ink sm:text-3xl">
          Agentic protection, across your book
        </h1>
        <p className="mt-2 max-w-2xl text-[0.95rem] leading-relaxed text-muted">
          Every customer below runs your banking app with the HyperGuard layer wired in. The layer
          scores, calls, educates, escalates and adjudicates each transfer in real time, here's
          what it's doing right now.
        </p>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <MetricTile label="Customers" value={ov ? String(ov.customers) : "—"} />
        <MetricTile label="Transfers reviewed" value={ov ? String(ov.transactions) : "—"} />
        <MetricTile label="Approved" value={ov ? String(ov.approved) : "—"} accent="var(--signal)" />
        <MetricTile label="Intervened" value={ov ? String(ov.blocked) : "—"} accent="var(--crimson)" sub="blocked mid-transfer" />
        <MetricTile label="Protected" value={ov ? money(ov.amount_protected).replace(".00", "") : "—"} accent="var(--signal)" />
        <MetricTile label="Escalations" value={ov ? String(ov.escalations) : "—"} accent="var(--ice)" sub="to next of kin" />
      </div>

      {err && (
        <p className="mt-5 text-[0.82rem] text-ember">
          Can't reach the backend ({err}). Start it with <span className="numeric">uvicorn app.main:app</span>.
        </p>
      )}

      {/* Recent interventions + customers */}
      <div className="mt-9 grid gap-6 lg:grid-cols-2">
        <section>
          <SectionTitle
            right={
              <Link href="/console/live" className="readout text-signal transition hover:brightness-110">
                run live →
              </Link>
            }
          >
            Recent interventions
          </SectionTitle>
          <div className="divide-y divide-hairline overflow-hidden rounded-lg border border-hairline bg-surface/40">
            {(ov?.recent_cases ?? []).map((c) => (
              <CaseRow key={c.case_id} c={c} />
            ))}
            {ov && ov.recent_cases.length === 0 && (
              <p className="p-5 text-[0.85rem] text-faint">No interventions yet.</p>
            )}
          </div>
        </section>

        <section>
          <SectionTitle right={<span className="readout">{users.length} accounts</span>}>Customers</SectionTitle>
          <div className="divide-y divide-hairline overflow-hidden rounded-lg border border-hairline bg-surface/40">
            {users.map((u) => (
              <CustomerRow key={u.id} u={u} />
            ))}
          </div>
        </section>
      </div>
    </ControlShell>
  );
}
