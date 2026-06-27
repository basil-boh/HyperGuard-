"use client";

import type { GuardianAlert } from "@/lib/types";

export function GuardianCard({ alerts }: { alerts: GuardianAlert[] }) {
  if (!alerts.length) {
    return (
      <p className="text-[0.8rem] text-faint">
        On confirmed coercion, a pre-authorised trusted contact is pulled into the loop.
      </p>
    );
  }

  return (
    <ul className="flex flex-col gap-3">
      {alerts.map((a, i) => {
        const ack = a.acknowledged;
        return (
          <li
            key={i}
            className="animate-rise rounded-md border border-hairline bg-abyss/60 p-3"
            style={{ borderLeft: `2px solid ${ack ? "var(--signal)" : "var(--amber)"}` }}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <span className="grid h-8 w-8 place-items-center rounded-full bg-raised numeric text-[0.7rem] text-ice">
                  {a.contact.name
                    .split(" ")
                    .map((p) => p[0])
                    .join("")}
                </span>
                <div className="leading-tight">
                  <p className="text-[0.84rem] font-medium text-ink">{a.contact.name}</p>
                  <p className="text-[0.68rem] capitalize text-faint">
                    {a.contact.relationship} · via {a.channel}
                  </p>
                </div>
              </div>
              <span
                className="rounded-full px-2 py-0.5 text-[0.6rem] font-semibold uppercase tracking-wider"
                style={{
                  color: ack ? "var(--signal)" : "var(--amber)",
                  background: ack ? "var(--signal-dim)" : "rgba(255,194,75,0.12)",
                }}
              >
                {ack ? "acknowledged" : a.status}
              </span>
            </div>
            <p className="mt-2 text-[0.74rem] leading-snug text-muted">{a.message}</p>
          </li>
        );
      })}
    </ul>
  );
}
