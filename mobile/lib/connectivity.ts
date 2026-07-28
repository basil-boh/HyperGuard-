import { useEffect, useState } from "react";

/**
 * Global API reachability. `lib/api.ts` reports every request's fate here; the
 * OfflineBanner subscribes so any screen can show a single, consistent
 * "can't reach HyperGuard" state without threading errors through props.
 * Only network-level failures flip the flag — HTTP 4xx/5xx means the backend
 * was reached and is a per-call error, not connectivity.
 */

type Listener = (offline: boolean) => void;

let offline = false;
const listeners = new Set<Listener>();

function set(value: boolean) {
  if (offline === value) return;
  offline = value;
  listeners.forEach((l) => l(value));
}

export const reportNetworkFailure = () => set(true);
export const reportNetworkSuccess = () => set(false);
export const isOffline = () => offline;

export function subscribeConnectivity(fn: Listener): () => void {
  listeners.add(fn);
  return () => {
    listeners.delete(fn);
  };
}

export function useConnectivity(): boolean {
  const [value, setValue] = useState(offline);
  useEffect(() => subscribeConnectivity(setValue), []);
  return value;
}
