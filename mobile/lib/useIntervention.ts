import { useEffect, useRef, useState } from "react";
import { api } from "./api";
import { POLL_INTERVAL_MS } from "./config";
import type { AgentKey, Decision, InterventionPoll, SwarmEvent } from "./types";

export type AgentState = "idle" | "engaged" | "done";

export interface TranscriptTurn {
  index: number;
  speaker: "agent" | "customer" | "system";
  text: string;
  tags: string[];
}

export interface InterventionView {
  risk: { score: number; band: string; rationale: string; signals: any[] } | null;
  agents: Record<AgentKey, AgentState>;
  activeAgent: AgentKey | null;
  call: { live: boolean } | null;
  transcript: TranscriptTurn[];
  classification: { title: string; confidence: number; indicators: string[]; guidance: string; archetype: string } | null;
  guardian: { name: string; relationship: string; channel: string; acknowledged: boolean; message: string } | null;
  decision: Decision | null;
  narrative: string | null;
  hasEvidence: boolean;
  done: boolean;
  balance: number | null;
}

const AGENTS: AgentKey[] = [
  "digital_twin",
  "voice_negotiator",
  "educator",
  "guardian",
  "recovery_coordinator",
];

function blank(): InterventionView {
  return {
    risk: null,
    agents: AGENTS.reduce((a, k) => ({ ...a, [k]: "idle" }), {} as Record<AgentKey, AgentState>),
    activeAgent: null,
    call: null,
    transcript: [],
    classification: null,
    guardian: null,
    decision: null,
    narrative: null,
    hasEvidence: false,
    done: false,
    balance: null,
  };
}

function reduce(poll: InterventionPoll): InterventionView {
  const v = blank();
  v.done = poll.done;
  v.balance = poll.balance;

  for (const ev of poll.events as SwarmEvent[]) {
    const agent = ev.agent;
    switch (ev.type) {
      case "risk.scored":
        v.risk = ev.payload.risk;
        break;
      case "agent.engaged":
        if (agent && agent !== "arbiter") {
          v.agents[agent] = "engaged";
          v.activeAgent = agent;
        }
        break;
      case "agent.completed":
        if (agent && agent !== "arbiter") v.agents[agent] = "done";
        break;
      case "call.started":
        v.call = { live: !!ev.payload.live };
        break;
      case "transcript.turn": {
        const t = ev.payload.turn;
        if (!v.transcript.some((x) => x.index === t.index)) v.transcript.push(t);
        break;
      }
      case "scam.classified":
        v.classification = ev.payload.classification;
        break;
      case "guardian.alerted": {
        const a = ev.payload.alert;
        v.guardian = {
          name: a.contact.name,
          relationship: a.contact.relationship,
          channel: a.channel,
          acknowledged: a.acknowledged,
          message: a.message,
        };
        break;
      }
      case "decision.made":
        v.decision = ev.payload.decision;
        v.narrative = ev.payload.narrative;
        break;
      case "evidence.built":
        v.hasEvidence = true;
        break;
      case "case.closed":
        v.activeAgent = null;
        break;
    }
  }

  // Outcome is authoritative once present.
  if (poll.outcome) {
    v.decision = poll.outcome.decision;
    v.narrative = poll.outcome.narrative;
    v.hasEvidence = !!poll.outcome.evidence;
    if (poll.outcome.risk) v.risk = poll.outcome.risk;
  }
  return v;
}

export function useIntervention(caseId: string): InterventionView {
  const [view, setView] = useState<InterventionView>(blank);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    let active = true;

    const tick = async () => {
      try {
        const poll = await api.intervention(caseId);
        if (!active) return;
        setView(reduce(poll));
        if (!poll.done) timer.current = setTimeout(tick, POLL_INTERVAL_MS);
      } catch {
        if (active) timer.current = setTimeout(tick, POLL_INTERVAL_MS * 2);
      }
    };
    tick();

    return () => {
      active = false;
      if (timer.current) clearTimeout(timer.current);
    };
  }, [caseId]);

  return view;
}
