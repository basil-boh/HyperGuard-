"use client";

import { useEffect, useState } from "react";
import { BAND_VAR } from "@/lib/format";
import type { RiskBand, Scenario } from "@/lib/types";

export function ScenarioLauncher({
  scenarios,
  busy,
  onLaunch,
}: {
  scenarios: Scenario[];
  busy: boolean;
  onLaunch: (id: string) => void;
}) {
  const [selected, setSelected] = useState<string | null>(null);

  // Scenarios load asynchronously; adopt the first one once it arrives.
  useEffect(() => {
    if (!selected && scenarios.length) setSelected(scenarios[0].id);
  }, [scenarios, selected]);

  return (
    <div className="flex flex-col gap-2.5">
      <ul className="flex flex-col gap-2">
        {scenarios.map((s) => {
          const active = s.id === selected;
          const color = BAND_VAR[s.severity as RiskBand] ?? "var(--faint)";
          return (
            <li key={s.id}>
              <button
                type="button"
                disabled={busy}
                onClick={() => setSelected(s.id)}
                className="group w-full rounded-md border px-3 py-2.5 text-left transition disabled:opacity-50"
                style={{
                  borderColor: active ? color : "var(--hairline)",
                  background: active ? `${color}0e` : "transparent",
                }}
              >
                <div className="flex items-center justify-between">
                  <span className="text-[0.86rem] font-medium text-ink">{s.title}</span>
                  <span
                    className="h-2 w-2 rounded-full"
                    style={{ background: color, boxShadow: `0 0 8px ${color}` }}
                  />
                </div>
                <p className="mt-0.5 text-[0.72rem] leading-snug text-faint">{s.subtitle}</p>
                <div className="mt-1.5 flex items-center gap-2">
                  <span className="readout text-[0.55rem]">{s.customer_name}</span>
                  <span className="text-faint">·</span>
                  <span className="readout text-[0.55rem]" style={{ color }}>
                    {s.expected}
                  </span>
                </div>
              </button>
            </li>
          );
        })}
      </ul>

      <button
        type="button"
        disabled={busy || !selected}
        onClick={() => selected && onLaunch(selected)}
        className="relative mt-1 overflow-hidden rounded-md bg-signal px-4 py-3 font-display text-[0.84rem] font-semibold text-onsignal transition active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-40"
      >
        {busy ? "Intervention in progress…" : "Initiate intervention"}
      </button>
    </div>
  );
}
