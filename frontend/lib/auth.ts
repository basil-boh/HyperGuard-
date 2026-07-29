// Operator session for the control centre.
//
// Login exchanges the shared operator password for a short-lived JWT which every
// admin/REST call sends as a Bearer header and the event websocket sends as its
// first frame. When the backend runs without ADMIN_PASSWORD the console never
// sees a 401 and this module stays dormant.

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "";
const TOKEN_KEY = "hg:operator_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function clearToken(): void {
  if (typeof window !== "undefined") window.localStorage.removeItem(TOKEN_KEY);
}

export function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { authorization: `Bearer ${token}` } : {};
}

export async function login(password: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/admin/login`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ password }),
  });
  if (res.status === 401) throw new Error("Wrong password.");
  if (res.status === 503) throw new Error("Operator auth isn't configured on the backend — the console is open.");
  if (!res.ok) throw new Error(`Login failed (${res.status}).`);
  const { token } = (await res.json()) as { token: string };
  window.localStorage.setItem(TOKEN_KEY, token);
}

// Bounce to the login page, remembering where the operator was headed.
export function redirectToLogin(): void {
  if (typeof window === "undefined") return;
  clearToken();
  const next = encodeURIComponent(window.location.pathname + window.location.search);
  window.location.href = `/console/login?next=${next}`;
}
