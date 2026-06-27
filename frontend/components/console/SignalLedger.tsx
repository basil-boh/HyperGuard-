"use client";

import { SEVERITY_VAR } from "@/lib/format";
import type { RiskSignal } from "@/lib/types";

// The "why" behind the score: each contributing signal as a labelled evidence bar.
export function SignalLedger({ signals }: { signals: RiskSignal[] }) {
  if (!signals.length) {
    return (
      <p className="text-[0.8rem] text-faint">
        No anomalies detected, every behavioural axis matches the customer's baseline.
      </p>
    );
  }
  const max = Math.max(...signals.map((s) => s.contribution), 0.0001);

  return (
    <ul className="flex flex-col gap-3.5">
      {signals.map((s) => {
        const color = SEVERITY_VAR[s.severity] ?? "var(--ice)";
        return (
          <li key={s.code} className="animate-rise">
            <div className="flex items-baseline justify-between gap-3">
              <span className="text-[0.82rem] font-medium text-ink">{s.label}</span>
              <span className="numeric text-[0.68rem]" style={{ color }}>
                +{Math.round(s.contribution * 100)}
              </span>
            </div>
            <div className="mt-1.5 h-[3px] w-full overflow-hidden rounded-full bg-raised">
              <div
                className="h-full rounded-full"
                style={{
                  width: `${(s.contribution / max) * 100}%`,
                  background: color,
                  boxShadow: `0 0 8px ${color}`,
                  transition: "width 700ms cubic-bezier(0.22,1,0.36,1)",
                }}
              />
            </div>
            <p className="mt-1 text-[0.72rem] leading-snug text-faint">{s.detail}</p>
          </li>
        );
      })}
    </ul>
  );
}
