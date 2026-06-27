"use client";

import { StatusDot } from "@/components/primitives/StatusDot";
import type { Link as LinkState } from "@/lib/useSwarmStream";

const LABELS: { key: string; name: string }[] = [
  { key: "llm", name: "LLM" },
  { key: "telephony", name: "Voice" },
  { key: "persistence", name: "Store" },
  { key: "distributed_bus", name: "Bus" },
];

export function CapabilityStrip({
  capabilities,
  link,
}: {
  capabilities: Record<string, boolean> | null;
  link: LinkState;
}) {
  const linkColor =
    link === "online" ? "var(--signal)" : link === "connecting" ? "var(--amber)" : "var(--crimson)";

  return (
    <div className="flex items-center gap-4">
      <div className="flex items-center gap-2">
        <StatusDot color={linkColor} pulse={link !== "offline"} size={6} />
        <span className="readout" style={{ color: linkColor }}>
          {link === "online" ? "stream live" : link}
        </span>
      </div>

      <span className="h-3.5 w-px bg-hairline" />

      <div className="flex items-center gap-3">
        {LABELS.map((c) => {
          const on = capabilities?.[c.key] ?? false;
          return (
            <span key={c.key} className="flex items-center gap-1.5" title={on ? "live" : "simulated"}>
              <StatusDot color={on ? "var(--ice)" : "var(--faint)"} size={5} />
              <span
                className="readout text-[0.55rem]"
                style={{ color: on ? "var(--muted)" : "var(--faint)" }}
              >
                {c.name}
              </span>
            </span>
          );
        })}
      </div>

      {capabilities?.demo_mode && (
        <>
          <span className="h-3.5 w-px bg-hairline" />
          <span className="rounded-full border border-signal/30 bg-signal/5 px-2 py-0.5 text-[0.55rem] font-semibold uppercase tracking-wider text-signal">
            Simulation
          </span>
        </>
      )}
    </div>
  );
}
