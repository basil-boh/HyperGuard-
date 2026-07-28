import AsyncStorage from "@react-native-async-storage/async-storage";

/**
 * The selected user. There is no password — on first launch the user picks or
 * creates a profile, and the choice is persisted on the device. When the backend
 * has SESSION_SECRET configured, selection also mints a signed session token that
 * is sent as `Authorization: Bearer …`; the legacy `X-User-Id` header is kept for
 * older backends (see lib/api.ts).
 */
export type SessionUser = { id: string; name: string; token?: string | null };

const KEY = "hg.user";
let cache: SessionUser | null = null;
let loaded = false;

export async function loadUser(): Promise<SessionUser | null> {
  if (loaded) return cache;
  try {
    const raw = await AsyncStorage.getItem(KEY);
    cache = raw ? (JSON.parse(raw) as SessionUser) : null;
  } catch {
    cache = null;
  }
  loaded = true;
  return cache;
}

export async function setUser(user: SessionUser): Promise<void> {
  cache = user;
  loaded = true;
  await AsyncStorage.setItem(KEY, JSON.stringify(user));
}

export async function clearUser(): Promise<void> {
  cache = null;
  loaded = true;
  await AsyncStorage.removeItem(KEY);
}

export async function getUserId(): Promise<string | null> {
  const user = await loadUser();
  return user?.id ?? null;
}

export async function getToken(): Promise<string | null> {
  const user = await loadUser();
  return user?.token ?? null;
}
