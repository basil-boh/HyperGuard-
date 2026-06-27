// Mirrors backend/app/schemas.py and domain/events.py, the wire contract.

export type RiskBand = "minimal" | "elevated" | "high" | "critical";
export type Decision = "approve" | "block" | "hold";
export type Speaker = "agent" | "customer" | "system";
export type Verification = "unknown" | "verified" | "failed" | "coerced";

export type AgentKey =
  | "digital_twin"
  | "voice_negotiator"
  | "educator"
  | "guardian"
  | "recovery_coordinator";

export interface RiskSignal {
  code: string;
  label: string;
  contribution: number;
  severity: "info" | "warn" | "alarm";
  detail: string;
}

export interface RiskAssessment {
  transaction_id: string;
  score: number;
  band: RiskBand;
  signals: RiskSignal[];
  rationale: string;
  model_version: string;
}

export interface TranscriptTurn {
  index: number;
  speaker: Speaker;
  text: string;
  ts: string;
  tags: string[];
}

export interface ScamClassification {
  archetype: string;
  title: string;
  confidence: number;
  indicators: string[];
  guidance: string;
  // Educator debrief — the customer's own phrases, how the scam works, and how to avoid it.
  mentions?: string[];
  how_it_works?: string;
  prevention?: string[];
}

export interface TrustedContact {
  id: string;
  name: string;
  phone: string;
  relationship: string;
  priority: number;
}

export interface GuardianAlert {
  contact: TrustedContact;
  channel: string;
  status: string;
  message: string;
  acknowledged: boolean;
}

export interface TimelineEntry {
  at: string;
  actor: string;
  event: string;
}

export interface EvidencePackage {
  case_id: string;
  transaction: TransactionRequest;
  risk: RiskAssessment;
  classification: ScamClassification | null;
  transcript: TranscriptTurn[];
  guardian_alerts: GuardianAlert[];
  timeline: TimelineEntry[];
  generated_at: string;
  executive_summary: string;
  recommended_actions: string[];
}

export interface TransactionRequest {
  id: string;
  customer_id: string;
  amount: number;
  currency: string;
  payee_name: string;
  payee_account: string;
  channel: string;
  memo: string | null;
  requested_at: string;
  status: string;
}

export interface Customer {
  id: string;
  name: string;
  phone: string;
  age: number | null;
  vulnerability_flags: string[];
  trusted_contacts: TrustedContact[];
}

export interface Scenario {
  id: string;
  title: string;
  subtitle: string;
  customer_id: string;
  customer_name: string;
  severity: RiskBand;
  expected: string;
}

export interface InterventionOutcome {
  transaction_id: string;
  decision: Decision;
  verification: Verification;
  risk: RiskAssessment;
  classification: ScamClassification | null;
  transcript: TranscriptTurn[];
  guardian_alerts: GuardianAlert[];
  evidence: EvidencePackage | null;
  decided_at: string;
  narrative: string;
}

// ── Events ─────────────────────────────────────────────────────────────────────
export type EventType =
  | "case.opened"
  | "risk.scored"
  | "agent.engaged"
  | "agent.completed"
  | "call.started"
  | "transcript.turn"
  | "scam.classified"
  | "guardian.alerted"
  | "decision.made"
  | "evidence.built"
  | "case.closed";

export interface SwarmEvent {
  id: string;
  type: EventType;
  case_id: string;
  agent: AgentKey | "arbiter" | null;
  at: string;
  payload: Record<string, any>;
}
