import { useEffect, useState } from "react";
import { View } from "react-native";
import { Stack, router } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { setUnauthorizedHandler } from "@/lib/api";
import { loadSession } from "@/lib/session";
import { color } from "@/lib/theme";

export default function RootLayout() {
  const [ready, setReady] = useState(false);
  const [signedIn, setSignedIn] = useState(false);

  useEffect(() => {
    loadSession().then((session) => {
      setSignedIn(!!session);
      setReady(true);
    });
  }, []);

  // A 401 from anywhere in the app (expired or revoked token) lands here: the
  // session is already cleared by lib/api, so this just moves the user.
  useEffect(() => {
    setUnauthorizedHandler(() => router.replace("/login"));
    return () => setUnauthorizedHandler(null);
  }, []);

  // Once the stored session is resolved, send signed-out users to the sign-in screen.
  useEffect(() => {
    if (ready && !signedIn) router.replace("/login");
  }, [ready, signedIn]);

  // Hold on a blank canvas until we know whether someone is signed in, so the
  // wallet never flashes before the sign-in screen.
  if (!ready) {
    return <View style={{ flex: 1, backgroundColor: color.void }} />;
  }

  return (
    <SafeAreaProvider>
      <StatusBar style="light" />
      <Stack
        screenOptions={{
          headerShown: false,
          contentStyle: { backgroundColor: color.void },
          animation: "slide_from_right",
        }}
      >
        <Stack.Screen name="(tabs)" />
        <Stack.Screen
          name="login"
          options={{ gestureEnabled: false, animation: "fade" }}
        />
        <Stack.Screen name="register" options={{ presentation: "modal" }} />
        <Stack.Screen name="account" options={{ presentation: "modal" }} />
        <Stack.Screen name="transfer" options={{ presentation: "modal" }} />
        <Stack.Screen name="add-recipient" options={{ presentation: "modal" }} />
        <Stack.Screen name="add-contact" options={{ presentation: "modal" }} />
        <Stack.Screen name="add-protected" options={{ presentation: "modal" }} />
        <Stack.Screen name="protecting/[userId]" />
        <Stack.Screen name="incident/[id]" />
        <Stack.Screen
          name="intervention/[caseId]"
          options={{ gestureEnabled: false, animation: "fade" }}
        />
      </Stack>
    </SafeAreaProvider>
  );
}
