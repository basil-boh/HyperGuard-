import React, { useState } from "react";
import { Alert, KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";
import { router } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Button, Kicker } from "@/components/ui";
import { api } from "@/lib/api";
import { color, font, radius } from "@/lib/theme";

const RELATIONSHIPS = ["son", "daughter", "spouse", "sibling", "caregiver", "friend"];

export default function AddContact() {
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [relationship, setRelationship] = useState("son");
  const [busy, setBusy] = useState(false);

  const valid = name.trim() && phone.trim().length >= 5;

  const save = async () => {
    if (!valid) return;
    setBusy(true);
    try {
      await api.addContact({ name: name.trim(), phone: phone.trim(), relationship });
      router.back();
    } catch (e: any) {
      Alert.alert("Couldn't add guardian", e?.message ?? "Try again.");
      setBusy(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe} edges={["top", "bottom"]}>
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="close" size={26} color={color.muted} />
        </Pressable>
        <Text style={styles.title}>Add guardian</Text>
        <View style={{ width: 26 }} />
      </View>

      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <ScrollView contentContainerStyle={{ padding: 20 }} keyboardShouldPersistTaps="handled">
          <Text style={styles.intro}>
            A trusted person HyperGuard can alert if it detects you're being scammed.
          </Text>

          <Kicker>Full name</Kicker>
          <TextInput value={name} onChangeText={setName} placeholder="e.g. Marcus Tan" placeholderTextColor={color.faint} style={styles.input} autoFocus />
          <Kicker>Phone number</Kicker>
          <TextInput value={phone} onChangeText={setPhone} placeholder="+65 8000 0000" placeholderTextColor={color.faint} style={styles.input} keyboardType="phone-pad" />

          <Kicker>Relationship</Kicker>
          <View style={styles.chips}>
            {RELATIONSHIPS.map((r) => {
              const active = r === relationship;
              return (
                <Pressable key={r} onPress={() => setRelationship(r)} style={[styles.chip, active && { borderColor: color.signal, backgroundColor: color.signalSoft }]}>
                  <Text style={[styles.chipText, active && { color: color.signal }]}>{r}</Text>
                </Pressable>
              );
            })}
          </View>
        </ScrollView>
        <View style={styles.footer}>
          <Button label="Add guardian" icon="shield-checkmark" onPress={save} loading={busy} disabled={!valid} />
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: color.void },
  header: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingHorizontal: 20, paddingVertical: 14 },
  title: { color: color.ink, fontSize: 16, fontWeight: font.bold },
  intro: { color: color.muted, fontSize: 14, lineHeight: 20, marginBottom: 22 },
  input: { marginTop: 8, marginBottom: 20, color: color.ink, fontSize: 16, backgroundColor: color.surface, borderRadius: radius.md, borderWidth: 1, borderColor: color.hairline, padding: 15 },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 10 },
  chip: { borderRadius: radius.pill, borderWidth: 1, borderColor: color.hairline, paddingHorizontal: 14, paddingVertical: 8 },
  chipText: { color: color.muted, fontSize: 13.5, fontWeight: font.medium, textTransform: "capitalize" },
  footer: { padding: 20, borderTopWidth: 1, borderTopColor: color.hairline },
});
