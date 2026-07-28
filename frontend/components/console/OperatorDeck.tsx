"use client";

import { StatusDot } from "@/components/primitives/StatusDot";
import type { CaseState } from "@/lib/useSwarmStream";
import type { OperatorInfo, OperatorPresence, OverrideAction } from "@/lib/types";

const ACTIONS: {
  action: OverrideAction;
  label: string;
  detail: string;
  color: string;
  applied: string;
}[] = [
  {
    action: "escalate_guardian",
    label: "Escalate to guardian",
    detail: "Alert the trusted contact immediately",
    color: "var(--ice)",
    applied: "guardian alerted",
  },
  {
    action: "freeze_transfer",
    label: "Freeze transfer",
    detail: "Hard-stop the money before adjudication",
    color: "var(--crimson)",
    applied: "transfer frozen",
  },
  {
    action: "human_handoff",
    label: "Hand to human",
    detail: "Park the case for a specialist review",
    color: "var(--amber)",
    applied: "with a human",
  },
];

export function OperatorDeck({
  state,
  operators,
  self,
  onOverride,
}: {
  state: CaseState;
  operators: OperatorPresence[];
  self: OperatorInfo;
  onOverride: (action: OverrideAction) => void;
}) {
  const live = state.phase === "running";
  const applied = new Set(state.overrides.map((o) => o.action));

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-col gap-2">
        {ACTIONS.map(({ action, label, detail, color, applied: appliedLabel }) => {
          const done = applied.has(action);
          const by = state.overrides.find((o) => o.action === action)?.operator.name;
          return (
            <button
              key={action}
              type="button"
              disabled={!live || done}
              onClick={() => onOverride(action)}
              className="w-full rounded-md border px-3 py-2.5 text-left transition active:scale-[0.99] disabled:cursor-not-allowed"
              style={{
                borderColor: done ? color : "var(--hairline)",
                background: done ? `${color}14` : "transparent",
                opacity: !live && !done ? 0.45 : 1,
              }}
            >
              <div className="flex items-center justify-between">
                <span className="text-[0.84rem] font-medium text-ink">{label}</span>
                <span className="readout text-[0.55rem]" style={{ color }}>
                  {done ? `● ${appliedLabel}${by ? ` · ${by}` : ""}` : "○ armed"}
                </span>
              </div>
              <p className="mt-0.5 text-[0.7rem] leading-snug text-faint">{detail}</p>
            </button>
          );
        })}
      </div>
      {!live && (
        <p className="text-[0.68rem] leading-snug text-faint">
          Overrides arm while a case is live; they trump the swarm's own adjudication.
        </p>
      )}

      {/* Presence roster — every connected console and what it's watching. */}
      <div className="border-t border-hairline pt-2.5">
        <p className="readout mb-1.5 text-[0.55rem]">
          {operators.length || 1} console{operators.length === 1 ? "" : "s"} online
        </p>
        <ul className="flex flex-col gap-1.5">
          {(operators.length ? operators : [{ ...self, viewing: state.caseId, since: "" }]).map(
            (op) => {
              const you = op.id === self.id;
              return (
                <li key={op.id} className="flex items-center justify-between">
                  <span className="flex items-center gap-2">
                    <StatusDot color={you ? "var(--signal)" : "var(--ice)"} pulse={you} size={6} />
                    <span className="text-[0.74rem] text-ink">
                      {op.name}
                      {you && <span className="text-faint"> · you</span>}
                    </span>
                  </span>
                  <span className="numeric text-[0.62rem] text-faint">{op.viewing ?? "idle"}</span>
                </li>
              );
            },
          )}
        </ul>
      </div>
    </div>
  );
}
