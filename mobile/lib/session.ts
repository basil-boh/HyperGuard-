import AsyncStorage from "@react-native-async-storage/async-storage";

/**
 * The signed-in customer.
 *
 * Sign-in is phone number + 6-digit PIN (`POST /api/auth/login`), which returns a
 * bearer token. The token is persisted on the device and sent on every API call
 * (see lib/api.ts); its `id` doubles as the legacy `X-User-Id` the backend still
 * accepts. Signing out is a local discard — the token is stateless server-side.
 */
export type Session = {
  id: string;
  name: string;
  token: string;
  /** Unix seconds. Used to sign out proactively rather than fail a request first. */
  expiresAt?: number | null;
};

const KEY = "hg.session";
/** The pre-login key, read once so an existing install isn't dumped at a login wall. */
const LEGACY_KEY = "hg.user";

let cache: Session | null = null;
let loaded = false;

export async function loadSession(): Promise<Session | null> {
  if (loaded) return cache;
  try {
    const raw = await AsyncStorage.getItem(KEY);
    const stored = raw ? (JSON.parse(raw) as Session) : null;
    cache = stored?.token ? stored : null;
    if (cache && isExpired(cache)) {
      await AsyncStorage.removeItem(KEY);
      cache = null;
    }
  } catch {
    cache = null;
  }
  loaded = true;
  return cache;
}

export async function setSession(session: Session): Promise<void> {
  cache = session;
  loaded = true;
  await AsyncStorage.setItem(KEY, JSON.stringify(session));
  await AsyncStorage.removeItem(LEGACY_KEY);
}

export async function clearSession(): Promise<void> {
  cache = null;
  loaded = true;
  await AsyncStorage.multiRemove([KEY, LEGACY_KEY]);
}

export async function getToken(): Promise<string | null> {
  return (await loadSession())?.token ?? null;
}

export async function getUserId(): Promise<string | null> {
  return (await loadSession())?.id ?? null;
}

function isExpired(session: Session): boolean {
  return !!session.expiresAt && session.expiresAt * 1000 <= Date.now();
}
