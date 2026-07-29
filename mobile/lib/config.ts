import Constants from "expo-constants";

/**
 * Backend base URL.
 *
 * Defaults to the deployed Railway backend so the app works as a standalone build
 * (and on any network) with no dependency on a dev machine. To point at a laptop
 * backend, set EXPO_PUBLIC_API_BASE (e.g. in mobile/.env) or `extra.apiBase` in
 * app.json. The env var wins so a dev machine's LAN IP never lands in a tracked file.
 */
const DEFAULT_API = "https://hyperguard-production.up.railway.app";

function resolveApiBase(): string {
  const fromEnv = process.env.EXPO_PUBLIC_API_BASE;
  if (fromEnv && fromEnv.length > 0) return fromEnv;
  const override = (Constants.expoConfig?.extra as { apiBase?: string } | undefined)?.apiBase;
  if (override && override.length > 0) return override;
  return DEFAULT_API;
}

export const API_BASE = resolveApiBase();
// Live event stream (same host as the REST API).
export const WS_URL = API_BASE.replace(/^http/, "ws") + "/ws/events";
// Fallback cadence when the websocket is down.
export const POLL_INTERVAL_MS = 650;
