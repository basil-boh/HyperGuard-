import React, { useState } from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { api } from "@/lib/api";
import { useConnectivity } from "@/lib/connectivity";
import { color, font } from "@/lib/theme";

/**
 * Global "can't reach HyperGuard" banner. Mounted once in the root layout; shows
 * whenever any API call fails at the network level and clears the moment one
 * succeeds. Retry probes /api/health (which itself reports back to connectivity).
 */
export function OfflineBanner() {
  const offline = useConnectivity();
  const insets = useSafeAreaInsets();
  const [checking, setChecking] = useState(false);

  if (!offline) return null;

  const retry = async () => {
    setChecking(true);
    try {
      await api.health();
    } catch {
      // still down — the banner stays
    } finally {
      setChecking(false);
    }
  };

  return (
    <View style={[styles.wrap, { paddingTop: insets.top + 8 }]}>
      <Ionicons name="cloud-offline" size={16} color={color.void} />
      <View style={{ flex: 1 }}>
        <Text style={styles.title}>Can't reach HyperGuard</Text>
        <Text style={styles.sub}>Protection updates are paused. Check your connection.</Text>
      </View>
      <Pressable onPress={checking ? undefined : retry} style={styles.retry} hitSlop={8}>
        {checking ? (
          <ActivityIndicator size="small" color={color.void} />
        ) : (
          <Text style={styles.retryText}>Retry</Text>
        )}
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    backgroundColor: color.amber,
    paddingHorizontal: 16,
    paddingBottom: 10,
  },
  title: { color: color.void, fontSize: 13, fontWeight: font.bold },
  sub: { color: color.void, fontSize: 11.5, opacity: 0.75, marginTop: 1 },
  retry: {
    borderRadius: 8,
    backgroundColor: "rgba(0,0,0,0.18)",
    paddingHorizontal: 12,
    paddingVertical: 7,
    minWidth: 58,
    alignItems: "center",
  },
  retryText: { color: color.void, fontSize: 12.5, fontWeight: font.bold },
});
