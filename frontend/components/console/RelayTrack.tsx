"use client";

import { StatusDot } from "@/components/primitives/StatusDot";
import { cn } from "@/lib/format";
import type { AgentState } from "@/lib/useSwarmStream";
import type { AgentKey } from "@/lib/types";

const ROSTER: { key: AgentKey; n: string; name: string }[] = [
  { key: "digital_twin", n: "01", name: "Digital Twin" },
  { key: "voice_negotiator", n: "02", name: "Negotiator" },
  { key: "educator", n: "03", name: "Educator" },
  { key: "guardian", n: "04", name: "Guardian" },
  { key: "recovery_coordinator", n: "05", name: "Recovery" },
];

const COLOR: Record<AgentState, string> = {
  idle: "var(--faint)",
  engaged: "var(--signal)",
  done: "var(--ice)",
};

export function RelayTrack({ agents }: { agents: Record<AgentKey, AgentState> }) {
  return (
    <ol className="flex items-stretch">
      {ROSTER.map((a, i) => {
        const st = agents[a.key];
        const color = COLOR[st];
        const prevDone = i > 0 && agents[ROSTER[i - 1].key] === "done";
        return (
          <li key={a.key} className="flex flex-1 flex-col">
            <div className="flex items-center">
              {i > 0 && (
                <span
                  className="h-[1.5px] flex-1"
                  style={{
                    background: prevDone ? "var(--ice)" : "var(--hairline)",
                    boxShadow: prevDone ? "0 0 8px var(--ice)" : "none",
                    transition: "background 500ms, box-shadow 500ms",
                  }}
                />
              )}
              <span
                className={cn(
                  "relative grid h-9 w-9 place-items-center rounded-[10px] border bg-abyss",
                  st === "engaged" && "animate-breathe",
                )}
                style={{ borderColor: color, boxShadow: st !== "idle" ? `0 0 14px -2px ${color}` : "none" }}
              >
                <span className="numeric text-[0.62rem] font-semibold" style={{ color }}>
                  {a.n}
                </span>
              </span>
              {i < ROSTER.length - 1 && (
                <span
                  className="h-[1.5px] flex-1"
                  style={{
                    background: st === "done" ? "var(--ice)" : "var(--hairline)",
                    boxShadow: st === "done" ? "0 0 8px var(--ice)" : "none",
                    transition: "background 500ms, box-shadow 500ms",
                  }}
                />
              )}
            </div>
            <div className="mt-2 flex items-center gap-1.5 pl-0.5">
              <StatusDot color={color} pulse={st === "engaged"} size={6} />
              <span
                className="text-[0.72rem]"
                style={{ color: st === "idle" ? "var(--faint)" : "var(--ink)" }}
              >
                {a.name}
              </span>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
