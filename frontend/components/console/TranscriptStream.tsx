"use client";

import { useEffect, useRef } from "react";
import { clock } from "@/lib/format";
import type { TranscriptTurn } from "@/lib/types";

const VOICE: Record<
  string,
  { who: string; accent: string; align: string }
> = {
  agent: { who: "HyperGuard", accent: "var(--signal)", align: "items-start" },
  customer: { who: "Customer", accent: "var(--amber)", align: "items-end" },
  system: { who: "System", accent: "var(--faint)", align: "items-start" },
};

export function TranscriptStream({
  turns,
  live,
}: {
  turns: TranscriptTurn[];
  live: boolean;
}) {
  const endRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turns.length]);

  if (!turns.length) {
    return (
      <div className="flex h-full min-h-[260px] items-center justify-center">
        <p className="readout text-faint">line idle, no active call</p>
      </div>
    );
  }

  return (
    <div className="flex h-full max-h-[44vh] flex-col gap-3 overflow-y-auto pr-1">
      {turns.map((t) => {
        const v = VOICE[t.speaker] ?? VOICE.system;
        const isGuidance = t.tags.includes("guidance");
        const mine = t.speaker === "customer";
        return (
          <div key={t.index} className={`flex flex-col gap-1 ${v.align} animate-rise`}>
            <div className="flex items-center gap-2">
              <span className="readout" style={{ color: v.accent }}>
                {v.who}
              </span>
              <span className="numeric text-[0.6rem] text-faint">{clock(t.ts)}</span>
              {isGuidance && (
                <span
                  className="rounded-sm px-1.5 py-px text-[0.55rem] font-semibold uppercase tracking-wider"
                  style={{ color: "var(--signal)", background: "var(--signal-dim)" }}
                >
                  live guidance
                </span>
              )}
            </div>
            <p
              className={`max-w-[88%] rounded-lg px-3.5 py-2.5 text-[0.86rem] leading-relaxed ${
                mine ? "rounded-tr-sm" : "rounded-tl-sm"
              }`}
              style={{
                background: mine ? "var(--raised)" : "rgba(201,242,74,0.05)",
                borderLeft: mine ? "none" : `2px solid ${isGuidance ? "var(--signal)" : v.accent}`,
                borderRight: mine ? `2px solid ${v.accent}` : "none",
                color: "var(--ink)",
              }}
            >
              {t.text}
            </p>
          </div>
        );
      })}
      {live && (
        <div className="flex items-center gap-2 pl-1 text-faint">
          <span className="h-1.5 w-1.5 animate-breathe rounded-full bg-signal" />
          <span className="readout">listening…</span>
        </div>
      )}
      <div ref={endRef} />
    </div>
  );
}
