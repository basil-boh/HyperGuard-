import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { color, font } from "@/lib/theme";
import { money, relativeDay } from "@/lib/format";
import type { LedgerEntry } from "@/lib/types";

export function TxnRow({ tx }: { tx: LedgerEntry }) {
  const incoming = tx.direction === "in";
  const blocked = tx.status === "blocked";
  const iconBg = blocked ? color.crimson + "1a" : incoming ? color.signal + "1a" : color.raised;
  const iconColor = blocked ? color.crimson : incoming ? color.signal : color.ice;
  const icon = blocked ? "shield" : incoming ? "arrow-down" : "arrow-up";

  return (
    <View style={styles.row}>
      <View style={[styles.icon, { backgroundColor: iconBg }]}>
        <Ionicons name={icon as any} size={18} color={iconColor} />
      </View>
      <View style={{ flex: 1 }}>
        <Text style={styles.name} numberOfLines={1}>
          {tx.counterparty}
        </Text>
        <Text style={styles.sub} numberOfLines={1}>
          {blocked ? "Blocked by HyperGuard" : tx.memo || relativeDay(tx.ts)}
        </Text>
      </View>
      <View style={{ alignItems: "flex-end" }}>
        <Text
          style={[
            styles.amount,
            {
              color: blocked ? color.faint : incoming ? color.signal : color.ink,
              textDecorationLine: blocked ? "line-through" : "none",
            },
          ]}
        >
          {incoming ? "+" : "−"}
          {money(tx.amount).replace("SGD ", "")}
        </Text>
        <Text style={styles.day}>{relativeDay(tx.ts)}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: "row", alignItems: "center", gap: 13, paddingVertical: 11 },
  icon: { width: 40, height: 40, borderRadius: 12, alignItems: "center", justifyContent: "center" },
  name: { color: color.ink, fontSize: 15, fontWeight: font.semi },
  sub: { color: color.faint, fontSize: 12.5, marginTop: 2 },
  amount: { fontSize: 15, fontWeight: font.bold, fontVariant: ["tabular-nums"] },
  day: { color: color.faint, fontSize: 11, marginTop: 2 },
});
