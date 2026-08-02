import React, { useState } from "react";
import { Alert, Keyboard, Pressable, StyleSheet, Text, TextInput, View } from "react-native";
import { router } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { Button, Kicker } from "@/components/ui";
import { FormScaffold } from "@/components/FormScaffold";
import { api } from "@/lib/api";
import { color, font, radius } from "@/lib/theme";

export default function AddRecipient() {
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [account, setAccount] = useState("");
  const [bank, setBank] = useState("");
  const [busy, setBusy] = useState(false);

  // A payee needs either a PayNow phone or a bank account.
  const valid = !!name.trim() && (!!account.trim() || phone.trim().length >= 4);

  const save = async () => {
    if (!valid) return;
    setBusy(true);
    try {
      await api.addRecipient({
        name: name.trim(),
        phone: phone.trim() || undefined,
        account: account.trim() || "—",
        bank: bank.trim() || "—",
      });
      router.back();
    } catch (e: any) {
      Alert.alert("Couldn't add payee", e?.message ?? "Try again.");
      setBusy(false);
    }
  };

  return (
    <FormScaffold
      header={
        <View style={styles.header}>
          <Pressable onPress={() => router.back()} hitSlop={12}>
            <Ionicons name="close" size={26} color={color.muted} />
          </Pressable>
          <Text style={styles.title}>New payee</Text>
          <View style={{ width: 26 }} />
        </View>
      }
      footer={
        <Button label="Add payee" icon="person-add" onPress={save} loading={busy} disabled={!valid} />
      }
    >
      <Kicker>Payee name</Kicker>
      <TextInput value={name} onChangeText={setName} placeholder="e.g. John Contractor" placeholderTextColor={color.faint} style={styles.input} autoFocus returnKeyType="next" />
      <Kicker>PayNow phone (optional)</Kicker>
      <TextInput value={phone} onChangeText={setPhone} placeholder="+65 9123 4567" placeholderTextColor={color.faint} style={styles.input} keyboardType="phone-pad" returnKeyType="next" />
      <Kicker>Account number (optional)</Kicker>
      <TextInput value={account} onChangeText={setAccount} placeholder="000-000000-0" placeholderTextColor={color.faint} style={styles.input} keyboardType="numbers-and-punctuation" returnKeyType="next" />
      <Kicker>Bank (optional)</Kicker>
      <TextInput
        value={bank}
        onChangeText={setBank}
        placeholder="e.g. DBS"
        placeholderTextColor={color.faint}
        style={styles.input}
        returnKeyType="done"
        onSubmitEditing={() => {
          Keyboard.dismiss();
          if (valid) save();
        }}
      />

      <View style={styles.note}>
        <Ionicons name="information-circle" size={16} color={color.faint} />
        <Text style={styles.noteText}>
          New payees you've never paid before — especially overseas or unknown numbers — are scored as higher risk. HyperGuard may verify the first transfer with a call.
        </Text>
      </View>
    </FormScaffold>
  );
}

const styles = StyleSheet.create({
  header: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingHorizontal: 20, paddingVertical: 14 },
  title: { color: color.ink, fontSize: 16, fontWeight: font.bold },
  input: { marginTop: 8, marginBottom: 20, color: color.ink, fontSize: 16, backgroundColor: color.surface, borderRadius: radius.md, borderWidth: 1, borderColor: color.hairline, padding: 15 },
  note: { flexDirection: "row", gap: 9, marginTop: 6 },
  noteText: { color: color.faint, fontSize: 12.5, lineHeight: 18, flex: 1 },
});
