import Constants from "expo-constants";
import { NativeModules } from "react-native";

/**
 * Backend base URL.
 *
 * On a physical phone, `localhost` points at the phone, not your computer, so we
 * derive your machine's LAN IP and target port 8000. We try, in order:
 *   1. an explicit `extra.apiBase` override in app.json,
 *   2. the Expo dev-server host (`hostUri`) — set in Expo Go,
 *   3. the Metro bundle URL (`SourceCode.scriptURL`) — the reliable source in a
 *      bare/prebuilt dev build, where `hostUri` is often empty.
 * That makes the app reach the backend with zero manual config in every case.
 */
function resolveApiBase(): string {
  const override = (Constants.expoConfig?.extra as { apiBase?: string } | undefined)?.apiBase;
  if (override) return override;

  const hostUri =
    Constants.expoConfig?.hostUri ?? (Constants as any).expoGoConfig?.hostUri;
  let host = hostUri?.split(":")[0];

  // Bare dev build: pull the dev-machine host out of the Metro bundle URL,
  // e.g. "http://172.20.10.2:8081/index.bundle?platform=ios&dev=true".
  if (!host || host === "localhost") {
    const scriptURL: string | undefined = NativeModules?.SourceCode?.scriptURL;
    const match = scriptURL?.match(/https?:\/\/([^:/]+)/);
    if (match) host = match[1];
  }

  if (host && host !== "localhost") return `http://${host}:8000`;
  return "http://localhost:8000";
}

export const API_BASE = resolveApiBase();
export const POLL_INTERVAL_MS = 650;
