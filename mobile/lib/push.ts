import { useEffect, useRef, useState } from "react";
import { Platform } from "react-native";
import * as Device from "expo-device";
import Constants, { ExecutionEnvironment } from "expo-constants";
import { router } from "expo-router";
import type * as Notifications from "expo-notifications";
import { api } from "./api";
import { getUserId } from "./session";
import { color } from "./theme";

/**
 * Push notifications. The device's Expo push token is bound to the active
 * profile server-side (`POST /api/users/push-token`); the backend then reaches
 * the victim ("transfer paused, expect a call") and their guardians even when
 * the app is backgrounded or closed. Everything here is best-effort: simulators,
 * denied permissions, or a missing EAS project id just mean no remote pushes.
 */

/**
 * Expo Go dropped remote push notifications in SDK 53, and `expo-notifications`
 * registers device tokens as an import-time side effect — so a static import
 * warns before any of our code runs. Load it lazily and only outside Expo Go.
 */
export const pushSupported = Constants.executionEnvironment !== ExecutionEnvironment.StoreClient;

type NotificationsApi = typeof Notifications;
type Subscription = ReturnType<NotificationsApi["addNotificationResponseReceivedListener"]>;

let loading: Promise<NotificationsApi | null> | null = null;

function loadNotifications(): Promise<NotificationsApi | null> {
  if (!pushSupported) return Promise.resolve(null);
  if (!loading) {
    loading = import("expo-notifications")
      .then((mod) => {
        // Show alerts even when the app is foregrounded — an intervention
        // notice must never be silently swallowed.
        mod.setNotificationHandler({
          handleNotification: async () => ({
            shouldShowBanner: true,
            shouldShowList: true,
            shouldPlaySound: true,
            shouldSetBadge: false,
          }),
        });
        return mod;
      })
      .catch((e) => {
        console.log("[push] expo-notifications unavailable:", String(e));
        return null;
      });
  }
  return loading;
}

let registered: string | null = null; // "<uid>:<token>" already synced this session

export async function syncPushRegistration(): Promise<void> {
  try {
    const N = await loadNotifications();
    if (!N) return; // Expo Go — use a development build for push
    if (!Device.isDevice) return; // simulators cannot receive push
    if (Platform.OS === "android") {
      await N.setNotificationChannelAsync("interventions", {
        name: "Fraud interventions",
        importance: N.AndroidImportance.MAX,
        vibrationPattern: [0, 250, 250, 250],
        lightColor: color.signal,
      });
    }
    let { status } = await N.getPermissionsAsync();
    if (status !== "granted") {
      status = (await N.requestPermissionsAsync()).status;
    }
    if (status !== "granted") return;

    const projectId =
      (Constants.expoConfig?.extra as any)?.eas?.projectId ?? Constants.easConfig?.projectId;
    const token = (await N.getExpoPushTokenAsync(projectId ? { projectId } : undefined)).data;
    const uid = await getUserId();
    const key = `${uid}:${token}`;
    if (!token || key === registered) return;
    await api.registerPushToken(token);
    registered = key;
  } catch (e) {
    // Missing project id / denied permission / no network — not fatal.
    console.log("[push] registration skipped:", String(e));
  }
}

export function routeForNotification(data: unknown): string | null {
  const d = data as { caseId?: string; role?: string } | null;
  if (!d?.caseId) return null;
  return d.role === "guardian" ? `/guardian/${d.caseId}` : `/intervention/${d.caseId}`;
}

/**
 * Register the device and deep-link notification taps (warm and cold start) to
 * the matching intervention or guardian screen.
 */
export function usePushNotifications(enabled: boolean) {
  const [response, setResponse] = useState<Notifications.NotificationResponse | null>(null);
  const handled = useRef<string | null>(null);

  useEffect(() => {
    if (enabled) syncPushRegistration();
  }, [enabled]);

  // Mirrors `Notifications.useLastNotificationResponse()`, which we cannot call
  // directly because the module is only loaded outside Expo Go.
  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    let subscription: Subscription | undefined;
    loadNotifications().then((N) => {
      if (!N || cancelled) return;
      // A tap that cold-started the app is already recorded natively.
      const initial = N.getLastNotificationResponse();
      if (initial) setResponse(initial);
      subscription = N.addNotificationResponseReceivedListener(setResponse);
      if (cancelled) subscription.remove(); // unmounted while the import resolved
    });
    return () => {
      cancelled = true;
      subscription?.remove();
    };
  }, [enabled]);

  useEffect(() => {
    if (!enabled || !response) return;
    const id = response.notification.request.identifier;
    if (handled.current === id) return;
    handled.current = id;
    const route = routeForNotification(response.notification.request.content.data);
    if (route) router.push(route as never);
  }, [enabled, response]);
}
