import { API_BASE } from "./config";
import type {
  Contact,
  InterventionPoll,
  LedgerEntry,
  Recipient,
  WalletSummary,
} from "./types";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "content-type": "application/json", ...(init?.headers ?? {}) },
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
  wallet: () => req<WalletSummary>("/api/wallet"),
  transactions: () => req<LedgerEntry[]>("/api/wallet/transactions"),
  recipients: () => req<Recipient[]>("/api/wallet/recipients"),
  contacts: () => req<Contact[]>("/api/wallet/contacts"),

  addRecipient: (body: { name: string; account: string; bank: string }) =>
    req<Recipient>("/api/wallet/recipients", { method: "POST", body: JSON.stringify(body) }),

  addContact: (body: { name: string; phone: string; relationship: string }) =>
    req<Contact>("/api/wallet/contacts", { method: "POST", body: JSON.stringify(body) }),

  removeContact: (id: string) =>
    req<{ removed: string }>(`/api/wallet/contacts/${id}`, { method: "DELETE" }),

  transfer: (body: {
    recipient_id?: string;
    payee_name?: string;
    payee_account?: string;
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
