import React, { useEffect, useState } from "react";
import {
  Alert,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { router } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Avatar, Button, Kicker } from "@/components/ui";
import { api } from "@/lib/api";
import { color, font, radius } from "@/lib/theme";
import type { Recipient } from "@/lib/types";

export default function Transfer() {
  const [recipients, setRecipients] = useState<Recipient[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [amount, setAmount] = useState("");
  const [memo, setMemo] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.recipients().then(setRecipients).catch(() => {});
  }, []);

  const amountNum = parseFloat(amount || "0");
  const valid = selected && amountNum > 0;

  const send = async () => {
    if (!valid) return;
    setBusy(true);
    try {
      const res = await api.transfer({ recipient_id: selected!, amount: amountNum, memo: memo || undefined });
      router.replace(`/intervention/${res.case_id}`);
    } catch (e: any) {
      Alert.alert("Transfer failed", e?.message ?? "Please try again.");
      setBusy(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe} edges={["top", "bottom"]}>
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="close" size={26} color={color.muted} />
        </Pressable>
        <Text style={styles.headerTitle}>Send money</Text>
        <View style={{ width: 26 }} />
      </View>

      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <ScrollView contentContainerStyle={{ padding: 20 }} keyboardShouldPersistTaps="handled">
          <Kicker>Amount</Kicker>
          <View style={styles.amountRow}>
            <Text style={styles.currency}>SGD</Text>
            <TextInput
              value={amount}
              onChangeText={(t) => setAmount(t.replace(/[^0-9.]/g, ""))}
              placeholder="0.00"
              placeholderTextColor={color.faint}
              keyboardType="decimal-pad"
              style={styles.amountInput}
              autoFocus
            />
          </View>
          <View style={styles.chips}>
            {[100, 500, 1000, 8000].map((v) => (
              <Pressable key={v} style={styles.chip} onPress={() => setAmount(String(v))}>
                <Text style={styles.chipText}>{v.toLocaleString()}</Text>
              </Pressable>
            ))}
          </View>

          <Kicker>To</Kicker>
          <View style={{ gap: 10, marginTop: 10 }}>
            {recipients.map((r) => {
              const active = r.id === selected;
              return (
                <Pressable
                  key={r.id}
                  onPress={() => setSelected(r.id)}
                  style={[styles.recipient, active && { borderColor: color.signal, backgroundColor: color.signalSoft }]}
                >
                  <Avatar name={r.name} tint={active ? color.signal : color.ice} />
                  <View style={{ flex: 1 }}>
                    <Text style={styles.rName}>{r.name}</Text>
                    <Text style={styles.rMeta}>
                      {r.bank} · {r.account}
                    </Text>
                  </View>
                  <Ionicons
                    name={active ? "radio-button-on" : "radio-button-off"}
                    size={20}
                    color={active ? color.signal : color.faint}
                  />
                </Pressable>
              );
            })}
            <Pressable style={styles.addNew} onPress={() => router.push("/add-recipient")}>
              <Ionicons name="add" size={18} color={color.signal} />
              <Text style={styles.addNewText}>New payee</Text>
            </Pressable>
          </View>

          <Kicker>Note (optional)</Kicker>
          <TextInput
            value={memo}
            onChangeText={setMemo}
            placeholder="What's this for?"
            placeholderTextColor={color.faint}
            style={styles.memo}
          />

          <View style={styles.guard}>
            <Ionicons name="shield-checkmark" size={15} color={color.signal} />
            <Text style={styles.guardText}>HyperGuard reviews this transfer before any money moves.</Text>
          </View>
        </ScrollView>

        <View style={styles.footer}>
          <Button label={busy ? "Reviewing…" : "Send securely"} icon="lock-closed" onPress={send} loading={busy} disabled={!valid} />
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: color.void },
  header: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingHorizontal: 20, paddingVertical: 14 },
  headerTitle: { color: color.ink, fontSize: 16, fontWeight: font.bold },
  amountRow: { flexDirection: "row", alignItems: "center", gap: 10, marginTop: 8, marginBottom: 14 },
  currency: { color: color.muted, fontSize: 20, fontWeight: font.semi },
  amountInput: { flex: 1, color: color.ink, fontSize: 42, fontWeight: font.black, letterSpacing: -1, padding: 0 },
  chips: { flexDirection: "row", gap: 8, marginBottom: 26 },
  chip: { borderRadius: radius.pill, borderWidth: 1, borderColor: color.hairline, paddingHorizontal: 14, paddingVertical: 7 },
  chipText: { color: color.muted, fontSize: 13, fontWeight: font.medium },
  recipient: { flexDirection: "row", alignItems: "center", gap: 13, borderRadius: radius.md, borderWidth: 1, borderColor: color.hairline, padding: 12 },
  rName: { color: color.ink, fontSize: 15, fontWeight: font.semi },
  rMeta: { color: color.faint, fontSize: 12, marginTop: 2, fontVariant: ["tabular-nums"] },
  addNew: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 6, paddingVertical: 12, borderRadius: radius.md, borderWidth: 1, borderStyle: "dashed", borderColor: color.hairline },
  addNewText: { color: color.signal, fontSize: 14, fontWeight: font.semi },
  memo: { marginTop: 10, color: color.ink, fontSize: 15, backgroundColor: color.surface, borderRadius: radius.md, borderWidth: 1, borderColor: color.hairline, padding: 14 },
  guard: { flexDirection: "row", alignItems: "center", gap: 8, marginTop: 22 },
  guardText: { color: color.faint, fontSize: 12.5, flex: 1, lineHeight: 17 },
  footer: { padding: 20, borderTopWidth: 1, borderTopColor: color.hairline },
});
