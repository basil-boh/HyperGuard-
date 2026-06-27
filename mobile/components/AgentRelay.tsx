import React, { useEffect, useRef } from "react";
import { Animated, StyleSheet, Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { color, font } from "@/lib/theme";
import type { AgentKey } from "@/lib/types";
import type { AgentState } from "@/lib/useIntervention";

const ROSTER: { key: AgentKey; name: string; role: string; icon: keyof typeof Ionicons.glyphMap }[] = [
  { key: "digital_twin", name: "Digital Twin", role: "Scoring behaviour", icon: "pulse" },
  { key: "voice_negotiator", name: "Voice Negotiator", role: "Calling you", icon: "call" },
  { key: "educator", name: "Educator", role: "Spotting the scam", icon: "school" },
  { key: "guardian", name: "Guardian", role: "Alerting next of kin", icon: "people" },
  { key: "recovery_coordinator", name: "Recovery", role: "Building evidence", icon: "document-text" },
];

const TINT: Record<AgentState, string> = {
  idle: color.faint,
  engaged: color.signal,
  done: color.ice,
};

function Pulse({ active, tint }: { active: boolean; tint: string }) {
  const a = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    if (!active) return;
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(a, { toValue: 1, duration: 700, useNativeDriver: true }),
        Animated.timing(a, { toValue: 0, duration: 700, useNativeDriver: true }),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [active]);
  const scale = a.interpolate({ inputRange: [0, 1], outputRange: [1, 2.4] });
  const opacity = a.interpolate({ inputRange: [0, 1], outputRange: [0.5, 0] });
  return (
    <View style={{ width: 10, alignItems: "center", justifyContent: "center" }}>
      {active && (
        <Animated.View
          style={{
            position: "absolute",
            width: 10,
            height: 10,
            borderRadius: 5,
            backgroundColor: tint,
            transform: [{ scale }],
            opacity,
          }}
        />
      )}
      <View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: tint }} />
    </View>
  );
}

export function AgentRelay({ agents }: { agents: Record<AgentKey, AgentState> }) {
  return (
    <View>
      {ROSTER.map((a, i) => {
        const st = agents[a.key];
        const tint = TINT[st];
        const last = i === ROSTER.length - 1;
        return (
          <View key={a.key} style={styles.row}>
            <View style={styles.rail}>
              <View style={[styles.node, { borderColor: tint }]}>
                <Ionicons name={a.icon} size={15} color={tint} />
              </View>
              {!last && (
                <View
                  style={[styles.connector, { backgroundColor: st === "done" ? color.ice : color.hairline }]}
                />
              )}
            </View>
            <View style={styles.body}>
              <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between" }}>
                <Text style={[styles.name, { color: st === "idle" ? color.muted : color.ink }]}>{a.name}</Text>
                <Pulse active={st === "engaged"} tint={tint} />
              </View>
              <Text style={styles.role}>
                {st === "done" ? "Done" : st === "engaged" ? a.role + "…" : a.role}
              </Text>
            </View>
          </View>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: "row", gap: 14 },
  rail: { alignItems: "center", width: 32 },
  node: {
    width: 32,
    height: 32,
    borderRadius: 10,
    borderWidth: 1.5,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: color.abyss,
  },
  connector: { width: 1.5, flex: 1, minHeight: 16, marginVertical: 2 },
  body: { flex: 1, paddingBottom: 16 },
  name: { fontSize: 14.5, fontWeight: font.semi },
  role: { color: color.faint, fontSize: 12.5, marginTop: 2 },
});
