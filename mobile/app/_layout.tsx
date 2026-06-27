import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { color } from "@/lib/theme";

export default function RootLayout() {
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
