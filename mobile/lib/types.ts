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

/** What `POST /api/auth/login` and `/register` return. */
export interface AuthSession {
  token: string;
  expires_at: number | null;
  user: { id: string; name: string };
}

/** The signed-in customer, from `GET /api/auth/me`. */
export interface Me {
  id: string;
  name: string;
  phone: string;
  account_number: string;
  balance: number;
  currency: string;
  age: number | null;
  vulnerability_flags: string[];
}

// ── Guardian network ─────────────────────────────────────────────────────────
export interface PersonBrief {
  id: string;
  name: string;
  phone: string | null;
  age: number | null;
  vulnerability_flags: string[];
}

export type LinkStatus = "pending" | "active" | "declined" | "revoked";

export interface GuardianLink {
  id: string;
  guardian_user_id: string;
  guardian_name: string;
  protected_user_id: string;
  protected_name: string;
  /** The guardian's relationship *to* the protected person, e.g. "son". */
  relationship: string;
  status: LinkStatus;
  invited_by: "guardian" | "protected";
  created_at: string;
  responded_at: string | null;
  guardian: PersonBrief;
  protected: PersonBrief;
  /** Present on "I'm protecting" rows only. */
  incidents?: { total: number; unread: number };
}

export interface Network {
  protecting: GuardianLink[];
  guardians: GuardianLink[];
  invitations: GuardianLink[];
  invitations_sent: GuardianLink[];
  unread_incidents: number;
}

export interface IncidentSummary {
  id: string;
  case_id: string;
  protected_user_id: string;
  protected_name: string;
  guardian_user_id: string;
  sent_at: string;
  sent_by_user_id: string | null;
  read_at: string | null;
  unread: boolean;
  note: string | null;
  amount: number;
  currency: string;
  payee_name: string;
  scam_title: string | null;
  decision: string;
  risk_score: number;
}

/** A SIMULATED authority filing — never a real report. See services/filing.py. */
export interface AuthorityFiling {
  case_id: string;
  reference: string;
  authority: string;
  filed_by_user_id: string;
  filed_at: string;
  status: string;
  timeline: { at: string; status: string; note: string }[];
  simulated: boolean;
  disclaimer: string;
  real_channels: string[];
}

export interface IncidentDetail {
  report: IncidentSummary;
  protected: PersonBrief;
  case: {
    case_id: string;
    user_name: string;
    created_at: string;
    amount: number;
    currency: string;
    payee_name: string;
    decision: string;
    status: string;
    risk_score: number;
    band: string;
    scam_type: string | null;
    scam_title: string | null;
    escalated: boolean;
    transaction: Record<string, any>;
    risk_signals: { code: string; label: string; contribution: number; severity: string; detail: string }[];
    rationale: string;
    classification: Record<string, any> | null;
    guardian_alerts: Record<string, any>[];
    transcript: { index: number; speaker: string; text: string; ts: string; tags: string[] }[];
    evidence: Record<string, any> | null;
    narrative: string;
  };
  filing: AuthorityFiling | null;
}

/** A seeded test account, from `GET /api/auth/demo-accounts`. */
export interface DemoAccount {
  id: string;
  name: string;
  phone: string;
  pin: string;
  blurb: string;
  account_number: string;
  balance: number;
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
