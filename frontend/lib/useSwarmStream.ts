"use client";

import { useCallback, useEffect, useReducer, useRef, useState } from "react";
import { runIntervention, wsURL } from "./api";
import type {
  AgentKey,
  Decision,
  EvidencePackage,
  GuardianAlert,
  OperatorInfo,
  OperatorOverride,
  OperatorPresence,
  OverrideAction,
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

// Reconnect with exponential backoff + jitter; heartbeat keeps presence fresh
// and lets the server prune dead consoles.
const RECONNECT_BASE_MS = 500;
const RECONNECT_CAP_MS = 15_000;
const HEARTBEAT_MS = 15_000;
const SEEN_IDS_CAP = 512;

const CALLSIGNS = ["alpha", "bravo", "cobalt", "delta", "echo", "helix", "nova", "orbit"];

function operatorIdentity(): OperatorInfo {
  if (typeof window === "undefined") return { id: "ssr", name: "console" };
  const cached = sessionStorage.getItem("hg:operator");
  if (cached) {
    try {
      return JSON.parse(cached) as OperatorInfo;
    } catch {
      /* regenerate below */
    }
  }
  const suffix = Math.floor(Math.random() * 0xffff).toString(16).padStart(4, "0");
  const identity: OperatorInfo = {
    id: `op-${suffix}`,
    name: `${CALLSIGNS[Math.floor(Math.random() * CALLSIGNS.length)]}-${suffix.slice(0, 2)}`,
  };
  sessionStorage.setItem("hg:operator", JSON.stringify(identity));
  return identity;
}

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
  overrides: OperatorOverride[];
  frozen: boolean;
  handoff: boolean;
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
  overrides: [],
  frozen: false,
  handoff: false,
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
    case "operator.override": {
      const entry: OperatorOverride = {
        action: ev.payload.action,
        operator: ev.payload.operator ?? { id: "?", name: "console" },
        at: ev.at,
      };
      return {
        ...state,
        overrides: [...state.overrides, entry],
        frozen: state.frozen || entry.action === "freeze_transfer",
        handoff: state.handoff || entry.action === "human_handoff",
      };
    }
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
  const [operators, setOperators] = useState<OperatorPresence[]>([]);
  const linkRef = useRef<Link>("connecting");
  const [, force] = useReducer((x) => x + 1, 0);
  const socketRef = useRef<WebSocket | null>(null);
  const selfRef = useRef<OperatorInfo | null>(null);
  const caseRef = useRef<string | null>(null);
  const lastEventIdRef = useRef<string | null>(null);
  const seenIdsRef = useRef<{ set: Set<string>; order: string[] }>({ set: new Set(), order: [] });
  if (selfRef.current === null) selfRef.current = operatorIdentity();

  const setLink = (l: Link) => {
    linkRef.current = l;
    force();
  };

  const send = useCallback((frame: Record<string, unknown>) => {
    const ws = socketRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(frame));
  }, []);

  useEffect(() => {
    let closed = false;
    let attempts = 0;
    let retry: ReturnType<typeof setTimeout>;
    let heartbeat: ReturnType<typeof setInterval>;

    const connect = () => {
      const base = wsURL();
      if (!base) return;
      setLink("connecting");
      // Resume from the last event we saw so a blip only replays the gap.
      const since = lastEventIdRef.current;
      const url = since ? `${base}${base.includes("?") ? "&" : "?"}since=${since}` : base;
      const ws = new WebSocket(url);
      socketRef.current = ws;

      ws.onopen = () => {
        attempts = 0;
        setLink("online");
        send({ op: "hello", operator: selfRef.current, viewing: caseRef.current });
      };
      ws.onmessage = (msg) => {
        let frame: any;
        try {
          frame = JSON.parse(msg.data);
        } catch {
          return; // ignore malformed frames
        }
        if (frame.type === "pong" || frame.type === "override.rejected") return;
        if (frame.type === "presence.updated") {
          setOperators(frame.payload?.operators ?? []);
          return;
        }
        const event = frame as SwarmEvent;
        if (!event.id || !event.type) return;
        // Dedupe across reconnect replays.
        const seen = seenIdsRef.current;
        if (seen.set.has(event.id)) return;
        seen.set.add(event.id);
        seen.order.push(event.id);
        while (seen.order.length > SEEN_IDS_CAP) seen.set.delete(seen.order.shift()!);
        lastEventIdRef.current = event.id;
        dispatch({ kind: "event", event });
      };
      ws.onclose = () => {
        if (closed) return;
        setLink("offline");
        const delay =
          Math.min(RECONNECT_CAP_MS, RECONNECT_BASE_MS * 2 ** attempts) + Math.random() * 400;
        attempts += 1;
        retry = setTimeout(connect, delay);
      };
      ws.onerror = () => ws.close();
    };

    connect();
    heartbeat = setInterval(() => send({ op: "ping" }), HEARTBEAT_MS);
    return () => {
      closed = true;
      clearTimeout(retry);
      clearInterval(heartbeat);
      socketRef.current?.close();
    };
  }, [send]);

  // Tell the roster which case this console is watching.
  useEffect(() => {
    caseRef.current = state.caseId;
    send({ op: "presence", viewing: state.caseId });
  }, [state.caseId, send]);

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

  const sendOverride = useCallback(
    (action: OverrideAction) => {
      if (!caseRef.current) return;
      send({ op: "override", case_id: caseRef.current, action });
    },
    [send],
  );

  return {
    state,
    link: linkRef.current,
    launch,
    reset,
    sendOverride,
    operators,
    self: selfRef.current,
  };
}
