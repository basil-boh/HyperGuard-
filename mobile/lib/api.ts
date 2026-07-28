import { API_BASE } from "./config";
import { getToken, getUserId } from "./session";
import type {
  Contact,
  InterventionPoll,
  LedgerEntry,
  Recipient,
  UserProfile,
  WalletSummary,
} from "./types";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  // Identify the active user: signed session token when the backend enforces
  // auth, plus the legacy X-User-Id header for backends that don't.
  const uid = await getUserId();
  const token = await getToken();
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "content-type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(uid ? { "X-User-Id": uid } : {}),
      ...(init?.headers ?? {}),
    },
  });
  if (!res.ok) {
    let detail = `${res.status}`;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {}
    throw new Error(detail);
  }
  return res.json();
}

export const api = {
  // identity
  listUsers: () => req<UserProfile[]>("/api/users"),
  createSession: (userId: string) =>
    req<{ user_id: string; token: string | null; expires_at: number | null }>(
      "/api/users/session",
      { method: "POST", body: JSON.stringify({ user_id: userId }) },
    ),
  createUser: (body: {
    name: string;
    phone: string;
    age?: number;
    vulnerability_flags?: string[];
    home_country?: string;
    initial_balance?: number;
  }) => req<UserProfile>("/api/users", { method: "POST", body: JSON.stringify(body) }),

  // wallet
  wallet: () => req<WalletSummary>("/api/wallet"),
  transactions: () => req<LedgerEntry[]>("/api/wallet/transactions"),
  recipients: () => req<Recipient[]>("/api/wallet/recipients"),
  contacts: () => req<Contact[]>("/api/wallet/contacts"),

  addRecipient: (body: {
    name: string;
    account?: string;
    bank?: string;
    phone?: string;
    country?: string;
  }) => req<Recipient>("/api/wallet/recipients", { method: "POST", body: JSON.stringify(body) }),

  addContact: (body: { name: string; phone: string; relationship: string }) =>
    req<Contact>("/api/wallet/contacts", { method: "POST", body: JSON.stringify(body) }),

  removeContact: (id: string) =>
    req<{ removed: string }>(`/api/wallet/contacts/${id}`, { method: "DELETE" }),

  transfer: (body: {
    recipient_id?: string;
    payee_name?: string;
    payee_account?: string;
    payee_phone?: string;
    amount: number;
    memo?: string;
  }) =>
    req<{ case_id: string; transaction_id: string; status: string }>(
      "/api/wallet/transfer",
      { method: "POST", body: JSON.stringify(body) },
    ),

  intervention: (caseId: string) =>
    req<InterventionPoll>(`/api/wallet/intervention/${caseId}`),
};
