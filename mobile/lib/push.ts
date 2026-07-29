import { useEffect, useRef } from "react";
import { Platform } from "react-native";
import * as Device from "expo-device";
import * as Notifications from "expo-notifications";
import Constants from "expo-constants";
import { router } from "expo-router";
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

// Show alerts even when the app is foregrounded — an intervention notice must
// never be silently swallowed.
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

let registered: string | null = null; // "<uid>:<token>" already synced this session

export async function syncPushRegistration(): Promise<void> {
  try {
    if (!Device.isDevice) return; // simulators cannot receive push
    if (Platform.OS === "android") {
      await Notifications.setNotificationChannelAsync("interventions", {
        name: "Fraud interventions",
        importance: Notifications.AndroidImportance.MAX,
        vibrationPattern: [0, 250, 250, 250],
        lightColor: color.signal,
      });
    }
    let { status } = await Notifications.getPermissionsAsync();
    if (status !== "granted") {
      status = (await Notifications.requestPermissionsAsync()).status;
    }
    if (status !== "granted") return;

    const projectId =
      (Constants.expoConfig?.extra as any)?.eas?.projectId ?? Constants.easConfig?.projectId;
    const token = (
      await Notifications.getExpoPushTokenAsync(projectId ? { projectId } : undefined)
    ).data;
    const uid = await getUserId();
    const key = `${uid}:${token}`;
    if (!token || key === registered) return;
    await api.registerPushToken(token);
    registered = key;
  } catch (e) {
    // Missing project id / Expo Go limitations / denied permission — not fatal.
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
  const lastResponse = Notifications.useLastNotificationResponse();
  const handled = useRef<string | null>(null);

  useEffect(() => {
    if (enabled) syncPushRegistration();
  }, [enabled]);

  useEffect(() => {
    if (!enabled || !lastResponse) return;
    const id = lastResponse.notification.request.identifier;
    if (handled.current === id) return;
    handled.current = id;
    const route = routeForNotification(lastResponse.notification.request.content.data);
    if (route) router.push(route as never);
  }, [enabled, lastResponse]);
}
