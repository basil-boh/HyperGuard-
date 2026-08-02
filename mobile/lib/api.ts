import { API_BASE } from "./config";
import { clearSession, getToken, getUserId } from "./session";
import type {
  AuthSession,
  AuthorityFiling,
  Contact,
  DemoAccount,
  GuardianLink,
  IncidentDetail,
  IncidentSummary,
  InterventionPoll,
  LedgerEntry,
  Me,
  Network,
  Recipient,
  UserProfile,
  WalletSummary,
} from "./types";

/** Raised on a 401 so callers can distinguish "signed out" from a network failure. */
export class UnauthorizedError extends Error {
  constructor(message = "Session expired, please sign in again") {
    super(message);
    this.name = "UnauthorizedError";
  }
}

/** Set by the root layout so a 401 anywhere bounces the app back to sign-in. */
let onUnauthorized: (() => void) | null = null;
export function setUnauthorizedHandler(handler: (() => void) | null): void {
  onUnauthorized = handler;
}

type ReqOptions = RequestInit & { anonymous?: boolean };

async function req<T>(path: string, init?: ReqOptions): Promise<T> {
  const { anonymous, ...rest } = init ?? {};
  // Bearer token identifies the signed-in customer; X-User-Id rides along for
  // back-compat with the pre-login backend contract.
  const token = anonymous ? null : await getToken();
  const uid = anonymous ? null : await getUserId();

  const res = await fetch(`${API_BASE}${path}`, {
    ...rest,
    headers: {
      "content-type": "application/json",
      ...(token ? { authorization: `Bearer ${token}` } : {}),
      ...(uid ? { "X-User-Id": uid } : {}),
      ...(rest.headers ?? {}),
    },
  });

  if (!res.ok) {
    let detail = `${res.status}`;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {}
    if (res.status === 401 && !anonymous) {
      await clearSession();
      onUnauthorized?.();
      throw new UnauthorizedError(detail);
    }
    throw new Error(detail);
  }
  return res.json();
}

export const api = {
  // auth
  login: (body: { phone: string; pin: string }) =>
    req<AuthSession>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify(body),
      anonymous: true,
    }),

  register: (body: {
    name: string;
    phone: string;
    pin: string;
    age?: number;
    initial_balance?: number;
  }) =>
    req<AuthSession & { profile: UserProfile }>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify(body),
      anonymous: true,
    }),

  /** Seeded phone/PIN pairs for the test-account picker; [] when the API hides them. */
  demoAccounts: () =>
    req<DemoAccount[]>("/api/auth/demo-accounts", { anonymous: true }).catch(
      () => [] as DemoAccount[],
    ),

  me: () => req<Me>("/api/auth/me"),

  changePin: (body: { current_pin: string; new_pin: string }) =>
    req<{ updated: boolean }>("/api/auth/pin", { method: "POST", body: JSON.stringify(body) }),

  logout: () => req<{ signed_out: boolean }>("/api/auth/logout", { method: "POST" }),

  // identity
  listUsers: () => req<UserProfile[]>("/api/users"),

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

  // guardian network
  network: () => req<Network>("/api/network"),

  /** Invite a relative to be protected — they must accept before anything is shared. */
  protect: (body: { phone: string; relationship: string }) =>
    req<GuardianLink>("/api/network/protect", { method: "POST", body: JSON.stringify(body) }),

  respondToInvitation: (linkId: string, accept: boolean) =>
    req<GuardianLink>(`/api/network/invitations/${linkId}/respond`, {
      method: "POST",
      body: JSON.stringify({ accept }),
    }),

  revokeLink: (linkId: string) =>
    req<{ revoked: string }>(`/api/network/links/${linkId}`, { method: "DELETE" }),

  // incident reports
  incidents: () => req<IncidentSummary[]>("/api/incidents"),

  incident: (reportId: string) => req<IncidentDetail>(`/api/incidents/${reportId}`),

  /** Raise a SIMULATED authority filing. Nothing is sent to anyone. */
  fileWithAuthorities: (reportId: string) =>
    req<{ filing: AuthorityFiling; already_filed: boolean }>(
      `/api/incidents/${reportId}/file`,
      { method: "POST" },
    ),

  /** Send one of my own case reports to my guardians. */
  sendReport: (body: { case_id: string; note?: string }) =>
    req<{ case_id: string; delivered_to: { guardian_user_id: string; name: string; report_id: string }[] }>(
      "/api/incidents/send",
      { method: "POST", body: JSON.stringify(body) },
    ),

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
