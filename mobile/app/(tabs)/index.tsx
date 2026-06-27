import React from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import { Button, Card, Kicker, ShieldLogo } from "@/components/ui";
import { TxnRow } from "@/components/TxnRow";
import { api } from "@/lib/api";
import { useFocusFetch } from "@/lib/useFocusFetch";
import { money } from "@/lib/format";
import { color, font, radius } from "@/lib/theme";
import type { LedgerEntry, WalletSummary } from "@/lib/types";

export default function Home() {
  const wallet = useFocusFetch<WalletSummary>(api.wallet);
  const txns = useFocusFetch<LedgerEntry[]>(api.transactions);
  const summary = wallet.data;
  const recent = (txns.data ?? []).slice(0, 4);

  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <ScrollView contentContainerStyle={{ padding: 20, paddingBottom: 40 }} showsVerticalScrollIndicator={false}>
        <View style={styles.header}>
          <ShieldLogo />
          <View style={{ flexDirection: "row", alignItems: "center", gap: 10 }}>
            <Pressable style={styles.switcher} onPress={() => router.push("/select-user")} hitSlop={8}>
              <Ionicons name="people" size={16} color={color.muted} />
            </Pressable>
            <Pressable style={styles.protected} onPress={() => router.push("/family")}>
              <Ionicons name="shield-checkmark" size={13} color={color.signal} />
              <Text style={styles.protectedText}>Protected</Text>
            </Pressable>
          </View>
        </View>

        {/* Balance */}
        <LinearGradient
          colors={["#171b24", "#0e1018"]}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
          style={styles.balanceCard}
        >
          <View style={styles.shieldWatermark}>
            <Ionicons name="shield-checkmark" size={120} color={color.signal} />
          </View>
          <Text style={styles.holder}>{summary?.holder ?? "—"}</Text>
          <Text style={styles.account}>{summary?.account_number ?? ""}</Text>
          <Text style={styles.balanceLabel}>Available balance</Text>
          <Text style={styles.balance}>
            {summary ? money(summary.balance, summary.currency) : "—"}
          </Text>
        </LinearGradient>

        {/* Actions */}
        <View style={styles.actions}>
          <View style={{ flex: 1 }}>
            <Button label="Transfer" icon="send" onPress={() => router.push("/transfer")} />
          </View>
          <View style={{ flex: 1 }}>
            <Button label="New payee" icon="person-add" variant="ghost" onPress={() => router.push("/add-recipient")} />
          </View>
        </View>

        {/* Protection */}
        <Pressable onPress={() => router.push("/family")}>
          <Card style={styles.protCard}>
            <View style={styles.protIcon}>
              <Ionicons name="shield-half" size={20} color={color.signal} />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.protTitle}>HyperGuard is watching your transfers</Text>
              <Text style={styles.protSub}>
                {summary?.next_of_kin ?? 0} guardian{(summary?.next_of_kin ?? 0) === 1 ? "" : "s"} · real-time scam interception
              </Text>
            </View>
            <Ionicons name="chevron-forward" size={18} color={color.faint} />
          </Card>
        </Pressable>

        {/* Recent */}
        <View style={styles.recentHead}>
          <Kicker>Recent activity</Kicker>
          <Pressable onPress={() => router.push("/activity")}>
            <Text style={styles.seeAll}>See all</Text>
          </Pressable>
        </View>
        <Card padded={false} style={{ paddingHorizontal: 16 }}>
          {recent.length === 0 ? (
            <Text style={styles.emptyRow}>No transactions yet.</Text>
          ) : (
            recent.map((t, i) => (
              <View key={t.id} style={i > 0 ? styles.rowBorder : undefined}>
                <TxnRow tx={t} />
              </View>
            ))
          )}
        </Card>

        {wallet.error ? (
          <Text style={styles.err}>
            Can't reach the backend ({wallet.error}). Is uvicorn running, and is the API host set in lib/config.ts?
          </Text>
        ) : null}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: color.void },
  header: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginBottom: 22 },
  protected: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: color.signal + "55",
    backgroundColor: color.signalSoft,
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  protectedText: { color: color.signal, fontSize: 12, fontWeight: font.semi },
  switcher: {
    width: 34,
    height: 34,
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: color.hairline,
    alignItems: "center",
    justifyContent: "center",
  },
  balanceCard: {
    borderRadius: radius.lg,
    padding: 22,
    borderWidth: 1,
    borderColor: color.hairline,
    overflow: "hidden",
  },
  shieldWatermark: { position: "absolute", right: -24, top: -14, opacity: 0.05 },
  holder: { color: color.ink, fontSize: 16, fontWeight: font.semi },
  account: { color: color.faint, fontSize: 13, marginTop: 2, fontVariant: ["tabular-nums"] },
  balanceLabel: { color: color.muted, fontSize: 12.5, marginTop: 22 },
  balance: { color: color.ink, fontSize: 36, fontWeight: font.black, letterSpacing: -1, marginTop: 4, fontVariant: ["tabular-nums"] },
  actions: { flexDirection: "row", gap: 12, marginTop: 18 },
  protCard: { flexDirection: "row", alignItems: "center", gap: 14, marginTop: 18 },
  protIcon: { width: 40, height: 40, borderRadius: 12, backgroundColor: color.signalSoft, alignItems: "center", justifyContent: "center" },
  protTitle: { color: color.ink, fontSize: 14.5, fontWeight: font.semi },
  protSub: { color: color.faint, fontSize: 12.5, marginTop: 3 },
  recentHead: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginTop: 26, marginBottom: 10 },
  seeAll: { color: color.signal, fontSize: 13, fontWeight: font.semi },
  rowBorder: { borderTopWidth: 1, borderTopColor: color.hairline },
  emptyRow: { color: color.faint, fontSize: 13, paddingVertical: 18, textAlign: "center" },
  err: { color: color.ember, fontSize: 12.5, marginTop: 18, lineHeight: 18 },
});
