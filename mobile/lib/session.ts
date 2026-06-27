import AsyncStorage from "@react-native-async-storage/async-storage";

/**
 * The selected user. There is no password — on first launch the user picks or
 * creates a profile, and the choice is persisted on the device. Its id is sent as
 * the `X-User-Id` header on every API call (see lib/api.ts).
 */
export type SessionUser = { id: string; name: string };

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
