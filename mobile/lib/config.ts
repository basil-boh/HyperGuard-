import Constants from "expo-constants";

/**
 * Backend base URL.
 *
 * Defaults to the deployed Railway backend so the app works as a standalone build
 * (and on any network) with no dependency on a dev machine. For local development
 * against a laptop backend, set `extra.apiBase` in app.json to override.
 */
const DEFAULT_API = "https://hyperguard-production.up.railway.app";

function resolveApiBase(): string {
  const override = (Constants.expoConfig?.extra as { apiBase?: string } | undefined)?.apiBase;
  if (override && override.length > 0) return override;
  return DEFAULT_API;
}

export const API_BASE = resolveApiBase();
export const POLL_INTERVAL_MS = 650;
