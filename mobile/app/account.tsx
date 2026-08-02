import React, { useEffect, useState } from "react";
import {
  Alert,
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
import { Avatar, Button, Card, Kicker, Pill, ShieldLogo } from "@/components/ui";
import { api } from "@/lib/api";
import { clearSession } from "@/lib/session";
import { money } from "@/lib/format";
import { color, font, radius } from "@/lib/theme";
import type { Me } from "@/lib/types";

const PIN_LENGTH = 6;

export default function AccountScreen() {
  const [me, setMe] = useState<Me | null>(null);
  const [changingPin, setChangingPin] = useState(false);

  useEffect(() => {
    api.me().then(setMe).catch(() => {});
  }, []);

  const signOut = async () => {
    // Tokens are stateless, so this is a local discard; tell the API anyway so the
    // sign-out shows up in the server log alongside the sign-in.
    await api.logout().catch(() => {});
    await clearSession();
    router.replace("/login");
  };

  const confirmSignOut = () =>
    Alert.alert("Sign out?", "You'll need your phone number and PIN to sign back in.", [
      { text: "Cancel", style: "cancel" },
      { text: "Sign out", style: "destructive", onPress: signOut },
    ]);

  return (
    <SafeAreaView style={styles.safe} edges={["top", "bottom"]}>
      <View style={styles.header}>
        <ShieldLogo />
        <Pressable onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="close" size={26} color={color.muted} />
        </Pressable>
      </View>

      <ScrollView
        contentContainerStyle={{ padding: 20, paddingBottom: 40 }}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
      >
        <Text style={styles.title}>Your account</Text>

        <Card style={styles.identity}>
          <Avatar name={me?.name ?? "?"} size={52} />
          <View style={{ flex: 1 }}>
            <Text style={styles.name}>{me?.name ?? "—"}</Text>
            <Text style={styles.meta}>{me?.phone ?? ""}</Text>
            <Text style={styles.meta}>
              {me?.account_number ?? ""}
              {me ? ` · ${money(me.balance, me.currency)}` : ""}
            </Text>
          </View>
        </Card>

        {me && me.vulnerability_flags.length > 0 ? (
          <View style={{ marginTop: 20 }}>
            <Kicker>Protection profile</Kicker>
            <View style={styles.flags}>
              {me.vulnerability_flags.map((flag) => (
                <Pill key={flag} label={flag.replace(/_/g, " ")} tint={color.amber} />
              ))}
            </View>
            <Text style={styles.flagNote}>
              HyperGuard weighs these when scoring a transfer, so an unusual payment on
              this account is challenged sooner.
            </Text>
          </View>
        ) : null}

        <View style={{ marginTop: 26, gap: 12 }}>
          {changingPin ? (
            <ChangePin onDone={() => setChangingPin(false)} />
          ) : (
            <Button
              label="Change PIN"
              icon="keypad"
              variant="ghost"
              onPress={() => setChangingPin(true)}
            />
          )}

          <Button
            label="Switch account"
            icon="swap-horizontal"
            variant="ghost"
            onPress={signOut}
          />
          <Button label="Sign out" icon="log-out" variant="danger" onPress={confirmSignOut} />
        </View>

        <Text style={styles.footnote}>
          Switching accounts signs you out and returns to the sign-in screen, where any
          seeded demo customer can be picked from the test-account list.
        </Text>
      </ScrollView>
    </SafeAreaView>
  );
}

function ChangePin({ onDone }: { onDone: () => void }) {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const ready = current.length === PIN_LENGTH && next.length === PIN_LENGTH;

  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      await api.changePin({ current_pin: current, new_pin: next });
      Alert.alert("PIN updated", "Use your new PIN the next time you sign in.");
      onDone();
    } catch (e: any) {
      setError(e?.message ?? "Couldn't update your PIN.");
      setBusy(false);
    }
  };

  return (
    <Card>
      <Kicker>Current PIN</Kicker>
      <TextInput
        value={current}
        onChangeText={(t) => setCurrent(t.replace(/\D/g, "").slice(0, PIN_LENGTH))}
        style={styles.pinInput}
        keyboardType="number-pad"
        secureTextEntry
        maxLength={PIN_LENGTH}
        editable={!busy}
        autoFocus
      />
      <Kicker>New PIN</Kicker>
      <TextInput
        value={next}
        onChangeText={(t) => setNext(t.replace(/\D/g, "").slice(0, PIN_LENGTH))}
        style={styles.pinInput}
        keyboardType="number-pad"
        secureTextEntry
        maxLength={PIN_LENGTH}
        editable={!busy}
      />
      {error ? <Text style={styles.error}>{error}</Text> : null}
      <View style={{ gap: 10, marginTop: 4 }}>
        <Button label="Update PIN" onPress={submit} loading={busy} disabled={!ready} />
        <Pressable onPress={onDone} style={{ alignItems: "center" }} disabled={busy}>
          <Text style={styles.link}>Cancel</Text>
        </Pressable>
      </View>
    </Card>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: color.void },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 20,
    paddingVertical: 14,
  },
  title: { color: color.ink, fontSize: 26, fontWeight: font.black, letterSpacing: -0.5 },
  identity: { flexDirection: "row", alignItems: "center", gap: 14, marginTop: 18 },
  name: { color: color.ink, fontSize: 17, fontWeight: font.bold },
  meta: {
    color: color.faint,
    fontSize: 12.5,
    marginTop: 3,
    fontVariant: ["tabular-nums"],
  },
  flags: { flexDirection: "row", flexWrap: "wrap", gap: 7, marginTop: 10 },
  flagNote: { color: color.faint, fontSize: 12, lineHeight: 17, marginTop: 10 },
  pinInput: {
    marginTop: 8,
    marginBottom: 14,
    color: color.ink,
    fontSize: 16,
    letterSpacing: 6,
    backgroundColor: color.void,
    borderRadius: radius.sm,
    borderWidth: 1,
    borderColor: color.hairline,
    padding: 13,
  },
  error: { color: color.crimson, fontSize: 12.5, marginBottom: 12 },
  link: { color: color.signal, fontSize: 14, fontWeight: font.semi },
  footnote: { color: color.faint, fontSize: 12, lineHeight: 17, marginTop: 24 },
});
