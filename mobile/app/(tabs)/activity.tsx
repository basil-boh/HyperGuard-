import React from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Card, Kicker } from "@/components/ui";
import { TxnRow } from "@/components/TxnRow";
import { api } from "@/lib/api";
import { useFocusFetch } from "@/lib/useFocusFetch";
import { color, font } from "@/lib/theme";
import type { LedgerEntry } from "@/lib/types";

export default function Activity() {
  const { data } = useFocusFetch<LedgerEntry[]>(api.transactions);
  const txns = data ?? [];
  const blocked = txns.filter((t) => t.status === "blocked").length;

  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <ScrollView contentContainerStyle={{ padding: 20, paddingBottom: 40 }} showsVerticalScrollIndicator={false}>
        <Text style={styles.title}>Activity</Text>
        <View style={styles.stats}>
          <View style={styles.stat}>
            <Text style={styles.statNum}>{txns.length}</Text>
            <Text style={styles.statLabel}>transactions</Text>
          </View>
          <View style={styles.statDivider} />
          <View style={styles.stat}>
            <Text style={[styles.statNum, { color: color.crimson }]}>{blocked}</Text>
            <Text style={styles.statLabel}>scams blocked</Text>
          </View>
        </View>

        <Kicker>All transactions</Kicker>
        <Card padded={false} style={{ paddingHorizontal: 16, marginTop: 10 }}>
          {txns.length === 0 ? (
            <Text style={styles.empty}>No transactions yet.</Text>
          ) : (
            txns.map((t, i) => (
              <View key={t.id} style={i > 0 ? styles.rowBorder : undefined}>
                <TxnRow tx={t} />
              </View>
            ))
          )}
        </Card>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: color.void },
  title: { color: color.ink, fontSize: 26, fontWeight: font.black, letterSpacing: -0.5, marginBottom: 18 },
  stats: { flexDirection: "row", alignItems: "center", backgroundColor: color.surface, borderRadius: 16, borderWidth: 1, borderColor: color.hairline, paddingVertical: 18, marginBottom: 24 },
  stat: { flex: 1, alignItems: "center" },
  statDivider: { width: 1, height: 34, backgroundColor: color.hairline },
  statNum: { color: color.ink, fontSize: 26, fontWeight: font.black, fontVariant: ["tabular-nums"] },
  statLabel: { color: color.faint, fontSize: 12, marginTop: 3 },
  rowBorder: { borderTopWidth: 1, borderTopColor: color.hairline },
  empty: { color: color.faint, fontSize: 13, paddingVertical: 18, textAlign: "center" },
});
