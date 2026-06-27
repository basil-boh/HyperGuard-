"use client";

import { useCallback, useEffect, useReducer, useRef } from "react";
import { runIntervention, wsURL } from "./api";
import type {
  AgentKey,
  Decision,
  EvidencePackage,
  GuardianAlert,
  RiskAssessment,
  ScamClassification,
  SwarmEvent,
  TranscriptTurn,
  Verification,
} from "./types";

export type Link = "connecting" | "online" | "offline";
export type Phase = "idle" | "arming" | "running" | "closed";
export type AgentState = "idle" | "engaged" | "done";

const AGENTS: AgentKey[] = [
  "digital_twin",
  "voice_negotiator",
  "educator",
  "guardian",
  "recovery_coordinator",
];

export interface CaseState {
  caseId: string | null;
  phase: Phase;
  customer: { name: string; phone: string; vulnerability_flags: string[] } | null;
  transaction: {
    amount: number;
    currency: string;
    payee_name: string;
    payee_account: string;
    memo: string | null;
  } | null;
  capabilities: Record<string, boolean> | null;
  risk: RiskAssessment | null;
  agents: Record<AgentKey, AgentState>;
  activeAgent: AgentKey | null;
  call: { sid: string; live: boolean; to: string } | null;
  transcript: TranscriptTurn[];
  classification: ScamClassification | null;
  verification: Verification;
  guardianAlerts: GuardianAlert[];
  decision: Decision | null;
  narrative: string | null;
  evidence: EvidencePackage | null;
}

const idleAgents = (): Record<AgentKey, AgentState> =>
  AGENTS.reduce((acc, k) => ({ ...acc, [k]: "idle" }), {} as Record<AgentKey, AgentState>);

const blank = (): CaseState => ({
  caseId: null,
  phase: "idle",
  customer: null,
  transaction: null,
  capabilities: null,
  risk: null,
  agents: idleAgents(),
  activeAgent: null,
  call: null,
  transcript: [],
  classification: null,
  verification: "unknown",
  guardianAlerts: [],
  decision: null,
  narrative: null,
  evidence: null,
});

type Action = { kind: "reset" } | { kind: "arm" } | { kind: "event"; event: SwarmEvent };

function reduce(state: CaseState, action: Action): CaseState {
  if (action.kind === "reset") return blank();
  if (action.kind === "arm") return { ...blank(), phase: "arming" };

  const ev = action.event;

  // Adopt a brand-new case; ignore stray events from any other case.
  if (ev.type === "case.opened") {
    return {
      ...blank(),
      caseId: ev.case_id,
      phase: "running",
      customer: ev.payload.customer ?? null,
      transaction: ev.payload.transaction ?? null,
      capabilities: ev.payload.capabilities ?? null,
    };
  }
  if (state.caseId && ev.case_id !== state.caseId) return state;

  const agent = ev.agent as AgentKey | "arbiter" | null;
  switch (ev.type) {
    case "risk.scored":
      return { ...state, risk: ev.payload.risk };
    case "agent.engaged":
      if (!agent || agent === "arbiter") return state;
      return { ...state, activeAgent: agent, agents: { ...state.agents, [agent]: "engaged" } };
    case "agent.completed":
      if (!agent || agent === "arbiter") return state;
      return { ...state, agents: { ...state.agents, [agent]: "done" } };
    case "call.started":
      return { ...state, call: ev.payload as CaseState["call"] };
    case "transcript.turn": {
      const turn = ev.payload.turn as TranscriptTurn;
      if (state.transcript.some((t) => t.index === turn.index)) return state;
      return { ...state, transcript: [...state.transcript, turn] };
    }
    case "scam.classified":
      return {
        ...state,
        classification: ev.payload.classification,
        verification: ev.payload.verification,
      };
    case "guardian.alerted":
      return { ...state, guardianAlerts: [...state.guardianAlerts, ev.payload.alert] };
    case "decision.made":
      return { ...state, decision: ev.payload.decision, narrative: ev.payload.narrative };
    case "evidence.built":
      return { ...state, evidence: ev.payload.evidence };
    case "case.closed":
      return { ...state, phase: "closed", activeAgent: null };
    default:
      return state;
  }
}

export function useSwarmStream() {
  const [state, dispatch] = useReducer(reduce, undefined, blank);
  const linkRef = useRef<Link>("connecting");
  const [, force] = useReducer((x) => x + 1, 0);
  const socketRef = useRef<WebSocket | null>(null);

  const setLink = (l: Link) => {
    linkRef.current = l;
    force();
  };

  useEffect(() => {
    let closed = false;
    let retry: ReturnType<typeof setTimeout>;

    const connect = () => {
      const url = wsURL();
      if (!url) return;
      setLink("connecting");
      const ws = new WebSocket(url);
      socketRef.current = ws;

      ws.onopen = () => setLink("online");
      ws.onmessage = (msg) => {
        try {
          dispatch({ kind: "event", event: JSON.parse(msg.data) as SwarmEvent });
        } catch {
          /* ignore malformed frames */
        }
      };
      ws.onclose = () => {
        if (closed) return;
        setLink("offline");
        retry = setTimeout(connect, 1500);
      };
      ws.onerror = () => ws.close();
    };

    connect();
    return () => {
      closed = true;
      clearTimeout(retry);
      socketRef.current?.close();
    };
  }, []);

  // Persist the freshest evidence so the recovery dossier can render standalone.
  useEffect(() => {
    if (state.evidence && typeof window !== "undefined") {
      sessionStorage.setItem("hg:evidence", JSON.stringify(state.evidence));
    }
  }, [state.evidence]);

  const launch = useCallback(async (scenarioId: string) => {
    dispatch({ kind: "arm" });
    try {
      await runIntervention(scenarioId);
    } catch (err) {
      console.error("intervention failed", err);
    }
  }, []);

  const reset = useCallback(() => dispatch({ kind: "reset" }), []);

  return { state, link: linkRef.current, launch, reset };
}
