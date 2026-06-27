export interface WalletSummary {
  holder: string;
  account_number: string;
  currency: string;
  balance: number;
  recipients: number;
  next_of_kin: number;
}

export interface LedgerEntry {
  id: string;
  ts: string;
  direction: "in" | "out";
  counterparty: string;
  amount: number;
  status: "approved" | "blocked" | "completed";
  decision: string | null;
  risk_score: number | null;
  scam_type: string | null;
  memo: string | null;
  case_id: string | null;
}

export interface Recipient {
  id: string;
  name: string;
  account: string;
  bank: string;
  phone: string | null;
  country: string | null;
  saved: boolean;
}

export interface UserProfile {
  id: string;
  name: string;
  phone: string;
  account_number: string;
  balance: number;
  currency: string;
  is_app_user: boolean;
}

export interface Contact {
  id: string;
  name: string;
  phone: string;
  relationship: string;
  priority: number;
}

export type AgentKey =
  | "digital_twin"
  | "voice_negotiator"
  | "educator"
  | "guardian"
  | "recovery_coordinator";

export type Decision = "approve" | "block" | "hold";

export interface SwarmEvent {
  id: string;
  type: string;
  case_id: string;
  agent: AgentKey | "arbiter" | null;
  at: string;
  payload: Record<string, any>;
}

export interface ContextQA {
  question: string;
  answer: string;
}

export interface Assessment {
  scam_likelihood: number;
  is_scam: boolean;
  reasoning: string;
  recommended_action: "clear" | "monitor" | "escalate" | string;
  escalation_reasons: string[];
}

export interface Escalation {
  escalated: boolean;
  guardians_notified: number;
  guardian_alerts: any[];
  filed_with_authorities: boolean;
  reasons: string[];
}

export interface InterventionPoll {
  case_id: string;
  events: SwarmEvent[];
  outcome: any | null;
  done: boolean;
  followup_pending: boolean;
  balance: number;
  context: ContextQA[];
  assessment: Assessment | null;
  escalation: Escalation | null;
  report: string | null;
}
