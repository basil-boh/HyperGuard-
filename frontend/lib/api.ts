import type { InterventionOutcome, Scenario } from "./types";

// Requests go through the Next rewrite proxy (`/api/*` → backend) by default, so
// the browser stays same-origin. Override with NEXT_PUBLIC_API_BASE if you prefer
// to hit the backend directly.
const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "";

export interface Capabilities {
  llm: boolean;
  telephony: boolean;
  speech: boolean;
  persistence: boolean;
  distributed_bus: boolean;
  demo_mode: boolean;
  [key: string]: boolean;
}

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`GET ${path} → ${res.status}`);
  return res.json();
}

export async function fetchHealth(): Promise<{ capabilities: Capabilities }> {
  return getJSON("/api/health");
}

export async function fetchScenarios(): Promise<Scenario[]> {
  return getJSON("/api/scenarios");
}

export async function runIntervention(scenarioId: string): Promise<InterventionOutcome> {
  const res = await fetch(`${API_BASE}/api/interventions/run`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ scenario_id: scenarioId }),
  });
  if (!res.ok) throw new Error(`run failed → ${res.status}`);
  return res.json();
}

export function wsURL(): string {
  if (process.env.NEXT_PUBLIC_WS_URL) return process.env.NEXT_PUBLIC_WS_URL;
  if (typeof window === "undefined") return "";
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  // Default to the backend's dev port; the WS isn't covered by the http rewrite.
  return `${proto}://${window.location.hostname}:8000/ws/events`;
}
