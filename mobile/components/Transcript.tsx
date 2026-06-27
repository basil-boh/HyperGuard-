import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { color, font } from "@/lib/theme";
import type { TranscriptTurn } from "@/lib/useIntervention";

export function Transcript({ turns, live }: { turns: TranscriptTurn[]; live: boolean }) {
  if (!turns.length) {
    return (
      <View style={styles.empty}>
        <Ionicons name="call-outline" size={18} color={color.faint} />
        <Text style={styles.emptyText}>Connecting the call…</Text>
      </View>
    );
  }

  return (
    <View style={{ gap: 10 }}>
      {turns.map((t) => {
        const me = t.speaker === "customer";
        const guidance = t.tags?.includes("guidance");
        const tint = me ? color.amber : color.signal;
        return (
          <View key={t.index} style={[styles.row, me ? styles.rowMe : styles.rowAgent]}>
            <Text style={[styles.who, { color: tint }]}>{me ? "You" : "HyperGuard"}</Text>
            <View
              style={[
                styles.bubble,
                me
                  ? { backgroundColor: color.raised, borderColor: color.amber }
                  : { backgroundColor: color.signalSoft, borderColor: guidance ? color.signal : color.signal },
                { borderLeftWidth: me ? 0 : 2, borderRightWidth: me ? 2 : 0 },
              ]}
            >
              {guidance && <Text style={styles.guidanceTag}>LIVE GUIDANCE</Text>}
              <Text style={styles.text}>{t.text}</Text>
            </View>
          </View>
        );
      })}
      {live && (
        <View style={styles.listening}>
          <View style={styles.dot} />
          <Text style={styles.listeningText}>listening…</Text>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  empty: { flexDirection: "row", alignItems: "center", gap: 8, paddingVertical: 18, justifyContent: "center" },
  emptyText: { color: color.faint, fontSize: 13 },
  row: { maxWidth: "92%" },
  rowAgent: { alignSelf: "flex-start", alignItems: "flex-start" },
  rowMe: { alignSelf: "flex-end", alignItems: "flex-end" },
  who: { fontSize: 10.5, fontWeight: font.bold, textTransform: "uppercase", letterSpacing: 0.8, marginBottom: 3 },
  bubble: { borderRadius: 14, paddingHorizontal: 13, paddingVertical: 10, borderWidth: 0 },
  guidanceTag: { color: color.signal, fontSize: 9.5, fontWeight: font.bold, letterSpacing: 1, marginBottom: 4 },
  text: { color: color.ink, fontSize: 14.5, lineHeight: 20 },
  listening: { flexDirection: "row", alignItems: "center", gap: 6, marginTop: 2 },
  dot: { width: 6, height: 6, borderRadius: 3, backgroundColor: color.signal },
  listeningText: { color: color.faint, fontSize: 11, textTransform: "uppercase", letterSpacing: 1 },
});
