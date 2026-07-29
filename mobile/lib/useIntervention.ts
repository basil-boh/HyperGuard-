import { useEffect, useState } from "react";
import { api } from "./api";
import { POLL_INTERVAL_MS, WS_URL } from "./config";
import { reportNetworkSuccess } from "./connectivity";
import type {
  AgentKey,
  Assessment,
  ContextQA,
  Decision,
  Escalation,
  InterventionPoll,
  SwarmEvent,
} from "./types";

export type AgentState = "idle" | "engaged" | "done";

/** How the view is being fed: live websocket, HTTP polling fallback, or still connecting. */
export type LinkState = "connecting" | "live" | "polling";

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
  // Voice follow-up
  followupPending: boolean;
  context: ContextQA[];
  assessment: Assessment | null;
  escalation: Escalation | null;
  report: string | null;
  // A guardian acted on this case from their own device.
  guardianAction: { action: string; by: string } | null;
  link: LinkState;
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
    followupPending: false,
    context: [],
    assessment: null,
    escalation: null,
    report: null,
    guardianAction: null,
    link: "connecting",
  };
}

function reduce(poll: InterventionPoll): InterventionView {
  const v = blank();
  v.done = poll.done;
  v.balance = poll.balance;
  v.followupPending = !!poll.followup_pending;
  v.context = poll.context ?? [];
  v.assessment = poll.assessment ?? null;
  v.escalation = poll.escalation ?? null;
  v.report = poll.report ?? null;

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
      // Voice follow-up results stream over the same bus, so the websocket path
      // shows them the moment they exist (the poll reconcile is the backstop).
      case "assessment.ready":
        v.assessment = ev.payload.assessment ?? v.assessment;
        break;
      case "report.filed":
        v.escalation = ev.payload.escalation ?? v.escalation;
        v.report = ev.payload.report ?? v.report;
        break;
      case "guardian.action":
        v.guardianAction = { action: ev.payload.action, by: ev.payload.by };
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

// Events that mean the server has authoritative state (outcome, balance, follow-up
// results) worth reconciling with a one-shot poll.
const RECONCILE_EVENTS = new Set([
  "decision.made",
  "case.closed",
  "assessment.ready",
  "report.filed",
  "guardian.action",
]);

// Bound follow-up polling so an unanswered call can't poll forever (~4 min at the
// fallback interval).
const MAX_FOLLOWUP_POLLS = 360;
// While the socket is live, the only thing not on the bus is the interview Q&A —
// reconcile lazily during the follow-up phase.
const FOLLOWUP_RECONCILE_MS = 4000;

/**
 * Live intervention view. Primary feed is the `/ws/events` stream filtered to this
 * case (instant, ~0 requests); an HTTP poll of the intervention endpoint runs once
 * on connect and after terminal events to pick up authoritative outcome/balance.
 * If the socket can't be held (Expo Go on a flaky LAN), it degrades to the old
 * polling behaviour and keeps retrying the socket with backoff.
 */
export function useIntervention(caseId: string): InterventionView {
  const [view, setView] = useState<InterventionView>(blank);

  useEffect(() => {
    let active = true;
    let ws: WebSocket | null = null;
    let link: LinkState = "connecting";
    let wsFailures = 0;
    let pollTimer: ReturnType<typeof setTimeout> | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let reconcileTimer: ReturnType<typeof setTimeout> | null = null;
    let followupPolls = 0;
    let fetching = false;

    const seen = new Set<string>();
    const events: SwarmEvent[] = [];
    let snap: InterventionPoll | null = null;

    const addEvent = (ev: SwarmEvent): boolean => {
      if (!ev?.id || seen.has(ev.id)) return false;
      seen.add(ev.id);
      events.push(ev);
      return true;
    };

    const merged = (): InterventionPoll => ({
      case_id: caseId,
      events,
      outcome: snap?.outcome ?? null,
      done: (snap?.done ?? false) || events.some((e) => e.type === "case.closed"),
      followup_pending: snap?.followup_pending ?? false,
      balance: snap?.balance ?? null,
      context: snap?.context ?? [],
      assessment: snap?.assessment ?? null,
      escalation: snap?.escalation ?? null,
      report: snap?.report ?? null,
    });

    const finished = () => {
      const m = merged();
      return m.done && !m.followup_pending;
    };

    const recompute = () => {
      if (!active) return;
      const v = reduce(merged());
      v.link = link;
      setView(v);
    };

    const fetchSnapshot = async () => {
      if (fetching) return;
      fetching = true;
      try {
        const poll = await api.intervention(caseId);
        if (!active) return;
        snap = poll;
        for (const ev of poll.events as SwarmEvent[]) addEvent(ev);
        recompute();
      } catch {
        // Unreachable backend is surfaced globally by the offline banner; keep
        // rendering the last known view.
      } finally {
        fetching = false;
      }
    };

    // ── Polling fallback (websocket down) ──────────────────────────────────────
    const stopPolling = () => {
      if (pollTimer) {
        clearTimeout(pollTimer);
        pollTimer = null;
      }
    };

    const pollLoop = async () => {
      pollTimer = null;
      await fetchSnapshot();
      if (!active || link === "live") return;
      const m = merged();
      const awaitingFollowup = m.followup_pending && followupPolls < MAX_FOLLOWUP_POLLS;
      if (m.followup_pending) followupPolls += 1;
      if (!m.done || awaitingFollowup) pollTimer = setTimeout(pollLoop, POLL_INTERVAL_MS);
    };

    const startPolling = () => {
      if (!pollTimer) pollTimer = setTimeout(pollLoop, POLL_INTERVAL_MS);
    };

    // ── Websocket feed ─────────────────────────────────────────────────────────
    const connect = () => {
      if (!active) return;
      let socket: WebSocket;
      try {
        socket = new WebSocket(WS_URL);
      } catch {
        down();
        return;
      }
      ws = socket;
      socket.onopen = () => {
        if (!active || socket !== ws) return;
        wsFailures = 0;
        link = "live";
        reportNetworkSuccess();
        stopPolling();
        // Replay covers recent events; the poll covers outcome/balance and
        // anything older than the replay window.
        fetchSnapshot();
        recompute();
      };
      socket.onmessage = (msg) => {
        if (!active) return;
        try {
          const ev = JSON.parse(String(msg.data)) as SwarmEvent;
          if (ev.case_id !== caseId || !addEvent(ev)) return;
          if (RECONCILE_EVENTS.has(ev.type)) fetchSnapshot();
          recompute();
        } catch {
          // ignore malformed frames
        }
      };
      socket.onerror = () => {
        // onclose fires right after; handle teardown there
      };
      socket.onclose = () => {
        if (!active || socket !== ws) return;
        down();
      };
    };

    const down = () => {
      ws = null;
      wsFailures += 1;
      if (finished()) return;
      link = "polling";
      startPolling();
      recompute();
      reconnectTimer = setTimeout(connect, Math.min(8000, 500 * 2 ** Math.min(wsFailures, 4)));
    };

    // While live, lazily reconcile during the follow-up phase (interview Q&A is
    // only exposed on the poll endpoint).
    const reconcileLoop = () => {
      reconcileTimer = setTimeout(async () => {
        if (!active) return;
        const m = merged();
        if (link === "live" && m.followup_pending && followupPolls < MAX_FOLLOWUP_POLLS) {
          followupPolls += 1;
          await fetchSnapshot();
        }
        if (active && !finished()) reconcileLoop();
      }, FOLLOWUP_RECONCILE_MS);
    };

    fetchSnapshot();
    connect();
    reconcileLoop();

    return () => {
      active = false;
      stopPolling();
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (reconcileTimer) clearTimeout(reconcileTimer);
      if (ws) {
        try {
          ws.close();
        } catch {}
        ws = null;
      }
    };
  }, [caseId]);

  return view;
}
