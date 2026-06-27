import { useEffect, useState } from "react";
import { View } from "react-native";
import { Stack, router } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { loadUser } from "@/lib/session";
import { color } from "@/lib/theme";

export default function RootLayout() {
  const [ready, setReady] = useState(false);
  const [hasUser, setHasUser] = useState(false);

  useEffect(() => {
    loadUser().then((u) => {
      setHasUser(!!u);
      setReady(true);
    });
  }, []);

  // Once the session is resolved, send first-launch users to the picker.
  useEffect(() => {
    if (ready && !hasUser) router.replace("/select-user");
  }, [ready, hasUser]);

  // Hold on a blank canvas until we know whether a profile is selected, so the
  // wallet never flashes before the picker.
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
        <Stack.Screen name="select-user" options={{ gestureEnabled: false, animation: "fade" }} />
        <Stack.Screen name="transfer" options={{ presentation: "modal" }} />
        <Stack.Screen name="add-recipient" options={{ presentation: "modal" }} />
        <Stack.Screen name="add-contact" options={{ presentation: "modal" }} />
        <Stack.Screen
          name="intervention/[caseId]"
          options={{ gestureEnabled: false, animation: "fade" }}
        />
      </Stack>
    </SafeAreaProvider>
  );
}
