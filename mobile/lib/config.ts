import Constants from "expo-constants";

/**
 * Backend base URL.
 *
 * On a physical phone running Expo Go, `localhost` points at the phone, not your
 * computer, so we derive your machine's LAN IP from the Expo dev-server host
 * (`hostUri`) and target port 8000. That makes the app reach the backend with
 * zero manual config in the common case.
 *
 * Override explicitly by setting `extra.apiBase` in app.json, or edit the
 * fallback below.
 */
function resolveApiBase(): string {
  const override = (Constants.expoConfig?.extra as { apiBase?: string } | undefined)?.apiBase;
  if (override) return override;

  const hostUri = Constants.expoConfig?.hostUri ?? (Constants as any).expoGoConfig?.hostUri;
  const host = hostUri?.split(":")[0];
  if (host) return `http://${host}:8000`;

  return "http://localhost:8000";
}

export const API_BASE = resolveApiBase();
export const POLL_INTERVAL_MS = 650;
