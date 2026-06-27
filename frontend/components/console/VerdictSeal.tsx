"use client";

import Link from "next/link";
import type { Decision } from "@/lib/types";

const FACE: Record<
  Decision,
  { label: string; color: string; glyph: string; sub: string }
> = {
  block: { label: "Transfer Blocked", color: "var(--crimson)", glyph: "⊘", sub: "Funds held in account" },
  hold: { label: "Held for Review", color: "var(--amber)", glyph: "⏸", sub: "Pending verification" },
  approve: { label: "Transfer Approved", color: "var(--signal)", glyph: "✓", sub: "Released to payee" },
};

export function VerdictSeal({
  decision,
  narrative,
  hasEvidence,
  pending,
}: {
  decision: Decision | null;
  narrative: string | null;
  hasEvidence: boolean;
  pending: boolean;
}) {
  if (!decision) {
    return (
      <div className="flex min-h-[120px] flex-col items-center justify-center gap-2 text-center">
        <span className="readout text-faint">{pending ? "deliberating" : "awaiting decision"}</span>
        {pending && (
          <span className="h-1.5 w-24 overflow-hidden rounded-full bg-raised">
            <span className="block h-full w-1/3 animate-sweep bg-signal" />
          </span>
        )}
      </div>
    );
  }

  const f = FACE[decision];
  return (
    <div className="animate-rise">
      <div
        className="relative flex items-center gap-4 overflow-hidden rounded-lg border p-4"
        style={{ borderColor: f.color, background: `${f.color}0d` }}
      >
        <div
          className="grid h-14 w-14 shrink-0 place-items-center rounded-full border-2 text-2xl"
          style={{ borderColor: f.color, color: f.color, boxShadow: `0 0 24px -4px ${f.color}` }}
        >
          {f.glyph}
        </div>
        <div>
          <p className="font-display text-lg font-semibold leading-none" style={{ color: f.color }}>
            {f.label}
          </p>
          <p className="readout mt-1.5">{f.sub}</p>
        </div>
      </div>

      {narrative && (
        <p className="mt-3 text-[0.82rem] leading-relaxed text-muted">{narrative}</p>
      )}

      {hasEvidence && (
        <Link
          href="/recovery"
          className="mt-3 inline-flex items-center gap-2 rounded-md border border-ice/40 bg-ice/5 px-3 py-2 text-[0.76rem] font-medium text-ice transition hover:bg-ice/10"
        >
          Open recovery dossier
          <span aria-hidden>→</span>
        </Link>
      )}
    </div>
  );
}
