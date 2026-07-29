// Control-centre API client (the bank's view over the protection layer).

import { authHeaders, redirectToLogin } from "@/lib/auth";
import type { ScamClassification } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "";
const ADMIN_KEY_STORAGE = "hg_admin_key";

// The backend guards /api/admin/* and /ws/events with ADMIN_API_KEY. The console
// takes the key from NEXT_PUBLIC_ADMIN_KEY at build time, or from
// localStorage["hg_admin_key"] so an operator can paste it in the browser.
export function getAdminKey(): string {
  if (typeof window !== "undefined") {
    const stored = window.localStorage.getItem(ADMIN_KEY_STORAGE);
    if (stored) return stored;
  }
  return process.env.NEXT_PUBLIC_ADMIN_KEY ?? "";
}

export function setAdminKey(key: string): void {
  if (typeof window === "undefined") return;
  if (key) window.localStorage.setItem(ADMIN_KEY_STORAGE, key);
  else window.localStorage.removeItem(ADMIN_KEY_STORAGE);
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store", headers: authHeaders() });
  if (res.status === 401) {
    redirectToLogin();
    throw new Error("operator login required");
  }
  if (!res.ok) throw new Error(`GET ${path} → ${res.status}`);
  return res.json();
}

export interface CaseSummary {
  case_id: string;
  user_id: string;
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
}

export interface Overview {
  customers: number;
  transactions: number;
  approved: number;
  blocked: number;
  amount_protected: number;
  escalations: number;
  recent_cases: CaseSummary[];
}

export interface UserRow {
  id: string;
  name: string;
  phone: string;
  age: number | null;
  account_number: string;
  balance: number;
  currency: string;
  vulnerability_flags: string[];
  guardians: number;
  transactions: number;
  blocked: number;
  protected: number;
  last_activity: string | null;
  risk: "clear" | "elevated" | "watch";
  is_app_user: boolean;
}

export interface LedgerEntry {
  id: string;
  ts: string;
  direction: "in" | "out";
  counterparty: string;
  amount: number;
  status: string;
  decision: string | null;
  risk_score: number | null;
  scam_type: string | null;
  memo: string | null;
  case_id: string | null;
}

export interface Guardian {
  id: string;
  name: string;
  phone: string;
  relationship: string;
  priority: number;
}

export interface Escalation {
  contact: Guardian;
  channel: string;
  status: string;
  acknowledged: boolean;
  message: string;
  case_id: string;
  payee: string;
  at: string;
}

export interface UserDetail {
  profile: {
    id: string;
    name: string;
    phone: string;
    age: number | null;
    vulnerability_flags: string[];
    known_payees: string[];
  };
  account: { holder: string; account_number: string; currency: string; balance: number };
  metrics: { transactions: number; succeeded: number; blocked: number; protected: number };
  guardians: Guardian[];
  transactions: LedgerEntry[];
  cases: CaseSummary[];
  escalations: Escalation[];
}

export interface CaseDetail extends CaseSummary {
  transaction: Record<string, any>;
  risk_signals: { code: string; label: string; contribution: number; severity: string; detail: string }[];
  rationale: string;
  classification: ScamClassification | null;
  guardian_alerts: { contact: Guardian; channel: string; status: string; acknowledged: boolean; message: string }[];
  transcript: { index: number; speaker: string; text: string; ts: string; tags: string[] }[];
  evidence: any | null;
  narrative: string;
}

export const admin = {
  overview: () => get<Overview>("/api/admin/overview"),
  users: () => get<UserRow[]>("/api/admin/users"),
  user: (id: string) => get<UserDetail>(`/api/admin/users/${id}`),
  cases: (status?: string) => get<CaseSummary[]>(`/api/admin/cases${status ? `?status=${status}` : ""}`),
  case: (id: string) => get<CaseDetail>(`/api/admin/cases/${id}`),
};
