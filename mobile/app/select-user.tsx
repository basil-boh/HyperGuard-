import React, { useEffect, useState } from "react";
import {
  ActivityIndicator,
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
import { Avatar, Button, Kicker, Pill, ShieldLogo } from "@/components/ui";
import { api } from "@/lib/api";
import { loadUser, setUser } from "@/lib/session";
import { money } from "@/lib/format";
import { color, font, radius } from "@/lib/theme";
import type { UserProfile } from "@/lib/types";

export default function SelectUser() {
  const [users, setUsers] = useState<UserProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [canClose, setCanClose] = useState(false);
  const [creating, setCreating] = useState(false);
  const [busy, setBusy] = useState(false);

  // new-profile form
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("+65");
  const [age, setAge] = useState("");

  const refresh = () =>
    api
      .listUsers()
      .then(setUsers)
      .catch(() => {})
      .finally(() => setLoading(false));

  useEffect(() => {
    loadUser().then((u) => setCanClose(!!u));
    refresh();
  }, []);

  const choose = async (u: UserProfile) => {
    await setUser({ id: u.id, name: u.name });
    router.replace("/(tabs)");
  };

  const create = async () => {
    if (!name.trim() || phone.trim().length < 4) return;
    setBusy(true);
    try {
      const u = await api.createUser({
        name: name.trim(),
        phone: phone.trim(),
        age: age ? parseInt(age, 10) : undefined,
      });
      await setUser({ id: u.id, name: u.name });
      router.replace("/(tabs)");
    } catch (e: any) {
      Alert.alert("Couldn't create profile", e?.message ?? "Try again.");
      setBusy(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe} edges={["top", "bottom"]}>
      <View style={styles.header}>
        <ShieldLogo />
        {canClose ? (
          <Pressable onPress={() => router.back()} hitSlop={12}>
            <Ionicons name="close" size={26} color={color.muted} />
          </Pressable>
        ) : (
          <View style={{ width: 26 }} />
        )}
      </View>

      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <ScrollView contentContainerStyle={{ padding: 20 }} keyboardShouldPersistTaps="handled">
          <Text style={styles.title}>{creating ? "Create your profile" : "Choose your account"}</Text>
          <Text style={styles.sub}>
            {creating
              ? "We'll learn your spending over time to protect you from scams."
              : "Each profile is a separate customer the HyperGuard layer protects."}
          </Text>

          {creating ? (
            <View style={{ marginTop: 20 }}>
              <Kicker>Full name</Kicker>
              <TextInput value={name} onChangeText={setName} placeholder="e.g. Mary Lim" placeholderTextColor={color.faint} style={styles.input} autoFocus />
              <Kicker>Phone number</Kicker>
              <TextInput value={phone} onChangeText={setPhone} placeholder="+65 9123 4567" placeholderTextColor={color.faint} style={styles.input} keyboardType="phone-pad" />
              <Kicker>Age (optional)</Kicker>
              <TextInput value={age} onChangeText={(t) => setAge(t.replace(/[^0-9]/g, ""))} placeholder="e.g. 68" placeholderTextColor={color.faint} style={styles.input} keyboardType="number-pad" />
            </View>
          ) : (
            <View style={{ gap: 10, marginTop: 20 }}>
              {loading ? (
                <ActivityIndicator color={color.signal} style={{ marginTop: 30 }} />
              ) : (
                users.map((u) => (
                  <Pressable key={u.id} style={styles.row} onPress={() => choose(u)}>
                    <Avatar name={u.name} tint={color.ice} />
                    <View style={{ flex: 1 }}>
                      <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
                        <Text style={styles.rName}>{u.name}</Text>
                        {u.is_app_user ? <Pill label="Demo" tint={color.signal} /> : null}
                      </View>
                      <Text style={styles.rMeta}>
                        {u.account_number} · {money(u.balance, u.currency)}
                      </Text>
                    </View>
                    <Ionicons name="chevron-forward" size={18} color={color.faint} />
                  </Pressable>
                ))
              )}
            </View>
          )}
        </ScrollView>

        <View style={styles.footer}>
          {creating ? (
            <>
              <Button label="Create & continue" icon="person-add" onPress={create} loading={busy} disabled={!name.trim() || phone.trim().length < 4} />
              <Pressable onPress={() => setCreating(false)} style={{ marginTop: 12, alignItems: "center" }}>
                <Text style={styles.link}>Back to accounts</Text>
              </Pressable>
            </>
          ) : (
            <Button label="Create new profile" icon="add" variant="ghost" onPress={() => setCreating(true)} />
          )}
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: color.void },
  header: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingHorizontal: 20, paddingVertical: 14 },
  title: { color: color.ink, fontSize: 24, fontWeight: font.black, letterSpacing: -0.5, marginTop: 6 },
  sub: { color: color.muted, fontSize: 13.5, lineHeight: 19, marginTop: 8 },
  row: { flexDirection: "row", alignItems: "center", gap: 13, borderRadius: radius.md, borderWidth: 1, borderColor: color.hairline, backgroundColor: color.surface, padding: 13 },
  rName: { color: color.ink, fontSize: 15.5, fontWeight: font.semi },
  rMeta: { color: color.faint, fontSize: 12.5, marginTop: 2, fontVariant: ["tabular-nums"] },
  input: { marginTop: 8, marginBottom: 18, color: color.ink, fontSize: 16, backgroundColor: color.surface, borderRadius: radius.md, borderWidth: 1, borderColor: color.hairline, padding: 15 },
  footer: { padding: 20, borderTopWidth: 1, borderTopColor: color.hairline },
  link: { color: color.signal, fontSize: 14, fontWeight: font.semi },
});
