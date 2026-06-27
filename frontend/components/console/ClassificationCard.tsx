"use client";

import { pct } from "@/lib/format";
import type { ScamClassification } from "@/lib/types";

export function ClassificationCard({ c }: { c: ScamClassification | null }) {
  const detected = c && c.archetype !== "none" && c.confidence >= 0.4;

  if (!c) {
    return (
      <p className="text-[0.8rem] text-faint">
        The Educator analyses the customer's replies for social-engineering fingerprints.
      </p>
    );
  }

  if (!detected) {
    return (
      <div className="flex items-center gap-3">
        <span className="grid h-8 w-8 place-items-center rounded-full border border-signal/40 text-signal">
          ✓
        </span>
        <p className="text-[0.84rem] text-ink">No scam narrative detected on the call.</p>
      </div>
    );
  }

  return (
    <div className="animate-rise">
      <div className="flex items-start justify-between gap-3">
        <div>
          <span className="readout text-crimson">pattern matched</span>
          <h4 className="mt-1 font-display text-[1.05rem] font-semibold leading-tight text-ink">
            {c.title}
          </h4>
        </div>
        <div className="shrink-0 text-right">
          <span className="numeric text-lg font-semibold text-crimson">{pct(c.confidence)}</span>
          <span className="readout block">confidence</span>
        </div>
      </div>

      <div className="mt-3 flex flex-wrap gap-1.5">
        {c.indicators.map((ind) => (
          <span
            key={ind}
            className="rounded border border-crimson/30 bg-crimson/5 px-2 py-0.5 text-[0.66rem] text-ember"
          >
            {ind}
          </span>
        ))}
      </div>

      <div className="mt-3 rounded-md border-l-2 border-signal bg-signal/5 px-3 py-2.5">
        <span className="readout text-signal">guidance delivered</span>
        <p className="mt-1 text-[0.8rem] leading-relaxed text-ink">{c.guidance}</p>
      </div>
    </div>
  );
}
