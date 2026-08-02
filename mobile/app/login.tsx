import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
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
import { Button, Kicker, ShieldLogo } from "@/components/ui";
import { api } from "@/lib/api";
import { setSession } from "@/lib/session";
import { color, font, radius } from "@/lib/theme";
import type { DemoAccount } from "@/lib/types";

const PIN_LENGTH = 6;

export default function Login() {
  const [phone, setPhone] = useState("+65");
  const [pin, setPin] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [demos, setDemos] = useState<DemoAccount[]>([]);
  const [showDemos, setShowDemos] = useState(false);

  const pinInput = useRef<TextInput>(null);
  // Guards the auto-submit that fires on the sixth digit, so a re-render can't
  // double-post the same PIN.
  const submitting = useRef(false);

  useEffect(() => {
    api.demoAccounts().then(setDemos).catch(() => {});
  }, []);

  const ready = phone.replace(/\D/g, "").length >= 8 && pin.length === PIN_LENGTH;

  const signIn = useCallback(
    async (withPhone = phone, withPin = pin) => {
      if (submitting.current) return;
      submitting.current = true;
      setBusy(true);
      setError(null);
      try {
        const session = await api.login({ phone: withPhone, pin: withPin });
        await setSession({
          id: session.user.id,
          name: session.user.name,
          token: session.token,
          expiresAt: session.expires_at,
        });
        router.replace("/(tabs)");
      } catch (e: any) {
        setError(e?.message ?? "Couldn't sign in. Check your connection.");
        setPin("");
        setBusy(false);
        submitting.current = false;
      }
    },
    [phone, pin],
  );

  const onPinChange = (next: string) => {
    const digits = next.replace(/\D/g, "").slice(0, PIN_LENGTH);
    setPin(digits);
    setError(null);
    if (digits.length === PIN_LENGTH && phone.replace(/\D/g, "").length >= 8) {
      signIn(phone, digits);
    }
  };

  const useDemo = (account: DemoAccount) => {
    setPhone(account.phone);
    setPin(account.pin);
    setShowDemos(false);
    signIn(account.phone, account.pin);
  };

  return (
    <SafeAreaView style={styles.safe} edges={["top", "bottom"]}>
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        <ScrollView
          contentContainerStyle={{ padding: 24, paddingTop: 40, flexGrow: 1 }}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
        >
          <ShieldLogo size={30} />
          <Text style={styles.title}>Welcome back</Text>
          <Text style={styles.sub}>
            Sign in with your phone number and 6-digit PIN. Every transfer you make is
            watched by the HyperGuard swarm.
          </Text>

          {/* Phone */}
          <View style={{ marginTop: 30 }}>
            <Kicker>Phone number</Kicker>
            <TextInput
              value={phone}
              onChangeText={(t) => {
                setPhone(t);
                setError(null);
              }}
              placeholder="+65 8000 0001"
              placeholderTextColor={color.faint}
              style={styles.input}
              keyboardType="phone-pad"
              autoCorrect={false}
              editable={!busy}
            />
          </View>

          {/* PIN */}
          <View style={{ marginTop: 22 }}>
            <Kicker>PIN</Kicker>
            <Pressable
              style={styles.pinRow}
              onPress={() => pinInput.current?.focus()}
              disabled={busy}
            >
              {Array.from({ length: PIN_LENGTH }).map((_, i) => (
                <View
                  key={i}
                  style={[
                    styles.pinCell,
                    i < pin.length && styles.pinCellFilled,
                    error ? styles.pinCellError : null,
                  ]}
                >
                  {i < pin.length ? <View style={styles.pinDot} /> : null}
                </View>
              ))}
            </Pressable>
            {/* The real field: invisible, but it owns the keyboard and the value. */}
            <TextInput
              ref={pinInput}
              value={pin}
              onChangeText={onPinChange}
              keyboardType="number-pad"
              maxLength={PIN_LENGTH}
              style={styles.hiddenInput}
              editable={!busy}
              autoFocus
            />
          </View>

          {error ? (
            <View style={styles.error}>
              <Ionicons name="alert-circle" size={16} color={color.crimson} />
              <Text style={styles.errorText}>{error}</Text>
            </View>
          ) : null}

          <View style={{ marginTop: 26 }}>
            <Button
              label="Sign in"
              icon="lock-open"
              onPress={() => signIn()}
              loading={busy}
              disabled={!ready}
            />
          </View>

          <Pressable
            onPress={() => router.push("/register")}
            style={{ marginTop: 16, alignItems: "center" }}
            disabled={busy}
          >
            <Text style={styles.link}>Create a new account</Text>
          </Pressable>

          <View style={{ flex: 1 }} />

          {/* Test accounts — served by the API, hidden when EXPOSE_DEMO_CREDENTIALS is off. */}
          {demos.length > 0 ? (
            <View style={styles.demoBlock}>
              <Pressable
                style={styles.demoHeader}
                onPress={() => setShowDemos((s) => !s)}
                disabled={busy}
              >
                <Ionicons name="flask" size={15} color={color.muted} />
                <Text style={styles.demoTitle}>Demo accounts</Text>
                <Text style={styles.demoCount}>{demos.length}</Text>
                <View style={{ flex: 1 }} />
                <Ionicons
                  name={showDemos ? "chevron-up" : "chevron-down"}
                  size={16}
                  color={color.faint}
                />
              </Pressable>

              {showDemos ? (
                <View style={{ marginTop: 4 }}>
                  {demos.map((account) => (
                    <Pressable
                      key={account.id}
                      style={styles.demoRow}
                      onPress={() => useDemo(account)}
                      disabled={busy}
                    >
                      <View style={{ flex: 1 }}>
                        <Text style={styles.demoName}>{account.name}</Text>
                        <Text style={styles.demoBlurb}>{account.blurb}</Text>
                        <Text style={styles.demoCreds}>
                          {account.phone} · PIN {account.pin}
                        </Text>
                      </View>
                      {busy ? (
                        <ActivityIndicator color={color.faint} />
                      ) : (
                        <Ionicons name="log-in-outline" size={17} color={color.signal} />
                      )}
                    </Pressable>
                  ))}
                </View>
              ) : (
                <Text style={styles.demoHint}>
                  Tap to sign in as any seeded customer — each has its own balance,
                  payees and transaction history.
                </Text>
              )}
            </View>
          ) : null}
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: color.void },
  title: {
    color: color.ink,
    fontSize: 30,
    fontWeight: font.black,
    letterSpacing: -0.8,
    marginTop: 26,
  },
  sub: { color: color.muted, fontSize: 14, lineHeight: 20, marginTop: 10 },
  input: {
    marginTop: 9,
    color: color.ink,
    fontSize: 17,
    backgroundColor: color.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: color.hairline,
    padding: 15,
    fontVariant: ["tabular-nums"],
  },
  pinRow: { flexDirection: "row", gap: 10, marginTop: 10 },
  pinCell: {
    flex: 1,
    height: 56,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: color.hairline,
    backgroundColor: color.surface,
    alignItems: "center",
    justifyContent: "center",
  },
  pinCellFilled: { borderColor: color.signal + "77", backgroundColor: color.signalSoft },
  pinCellError: { borderColor: color.crimson + "66" },
  pinDot: { width: 10, height: 10, borderRadius: 5, backgroundColor: color.signal },
  hiddenInput: { position: "absolute", opacity: 0, height: 1, width: 1 },
  error: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginTop: 18,
    paddingHorizontal: 13,
    paddingVertical: 11,
    borderRadius: radius.sm,
    borderWidth: 1,
    borderColor: color.crimson + "44",
    backgroundColor: color.crimson + "14",
  },
  errorText: { color: color.crimson, fontSize: 13, flex: 1, lineHeight: 18 },
  link: { color: color.signal, fontSize: 14, fontWeight: font.semi },
  demoBlock: {
    marginTop: 34,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: color.hairline,
    backgroundColor: color.abyss,
    padding: 14,
  },
  demoHeader: { flexDirection: "row", alignItems: "center", gap: 8 },
  demoTitle: { color: color.muted, fontSize: 13, fontWeight: font.semi },
  demoCount: {
    color: color.faint,
    fontSize: 11,
    fontWeight: font.bold,
    backgroundColor: color.raised,
    borderRadius: radius.pill,
    paddingHorizontal: 7,
    paddingVertical: 1,
    overflow: "hidden",
  },
  demoHint: { color: color.faint, fontSize: 12, lineHeight: 17, marginTop: 8 },
  demoRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    paddingVertical: 11,
    borderTopWidth: 1,
    borderTopColor: color.hairline,
  },
  demoName: { color: color.ink, fontSize: 14.5, fontWeight: font.semi },
  demoBlurb: { color: color.muted, fontSize: 12, marginTop: 2 },
  demoCreds: {
    color: color.faint,
    fontSize: 11.5,
    marginTop: 3,
    fontVariant: ["tabular-nums"],
  },
});
