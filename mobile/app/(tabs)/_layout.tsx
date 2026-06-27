import { Tabs } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { color, font } from "@/lib/theme";

export default function TabsLayout() {
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: color.signal,
        tabBarInactiveTintColor: color.faint,
        tabBarStyle: {
          backgroundColor: color.abyss,
          borderTopColor: color.hairline,
          height: 88,
          paddingTop: 10,
          paddingBottom: 28,
        },
        tabBarLabelStyle: { fontSize: 11, fontWeight: font.semi },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{ title: "Wallet", tabBarIcon: ({ color: c, size }) => <Ionicons name="wallet" size={size} color={c} /> }}
      />
      <Tabs.Screen
        name="activity"
        options={{ title: "Activity", tabBarIcon: ({ color: c, size }) => <Ionicons name="receipt" size={size} color={c} /> }}
      />
      <Tabs.Screen
        name="family"
        options={{ title: "Guardians", tabBarIcon: ({ color: c, size }) => <Ionicons name="shield-half" size={size} color={c} /> }}
      />
    </Tabs>
  );
}
