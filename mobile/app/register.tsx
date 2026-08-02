import React, { useRef, useState } from "react";
import { Pressable, StyleSheet, Text, TextInput, View } from "react-native";
import { router } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { Button, Kicker, ShieldLogo } from "@/components/ui";
import { FormScaffold } from "@/components/FormScaffold";
import { api } from "@/lib/api";
import { setSession } from "@/lib/session";
import { color, font, radius } from "@/lib/theme";

const PIN_LENGTH = 6;

export default function Register() {
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("+65");
  const [age, setAge] = useState("");
  const [pin, setPin] = useState("");
  const [confirmPin, setConfirmPin] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const confirmInput = useRef<TextInput>(null);

  const pinsMatch = pin.length === PIN_LENGTH && pin === confirmPin;
  const ready = name.trim().length > 1 && phone.replace(/\D/g, "").length >= 8 && pinsMatch;

  const create = async () => {
    if (!ready || busy) return;
    setBusy(true);
    setError(null);
    try {
      const result = await api.register({
        name: name.trim(),
        phone: phone.trim(),
        pin,
        age: age ? parseInt(age, 10) : undefined,
      });
      await setSession({
        id: result.user.id,
        name: result.user.name,
        token: result.token,
        expiresAt: result.expires_at,
      });
      router.replace("/(tabs)");
    } catch (e: any) {
      setError(e?.message ?? "Couldn't create your account. Try again.");
      setBusy(false);
    }
  };

  return (
    <FormScaffold
      contentStyle={{ padding: 24, paddingTop: 8 }}
      header={
        <View style={styles.header}>
          <ShieldLogo />
          <Pressable onPress={() => router.back()} hitSlop={12}>
            <Ionicons name="close" size={26} color={color.muted} />
          </Pressable>
        </View>
      }
    >
          <Text style={styles.title}>Create your account</Text>
          <Text style={styles.sub}>
            HyperGuard learns how you normally spend, so it can tell a real transfer from
            one someone talked you into.
          </Text>

          <View style={{ marginTop: 26 }}>
            <Kicker>Full name</Kicker>
            <TextInput
              value={name}
              onChangeText={setName}
              placeholder="e.g. Mary Lim"
              placeholderTextColor={color.faint}
              style={styles.input}
              editable={!busy}
              autoFocus
            />

            <Kicker>Phone number</Kicker>
            <TextInput
              value={phone}
              onChangeText={setPhone}
              placeholder="+65 9123 4567"
              placeholderTextColor={color.faint}
              style={styles.input}
              keyboardType="phone-pad"
              editable={!busy}
            />

            <Kicker>Age (optional)</Kicker>
            <TextInput
              value={age}
              onChangeText={(t) => setAge(t.replace(/[^0-9]/g, ""))}
              placeholder="e.g. 68"
              placeholderTextColor={color.faint}
              style={styles.input}
              keyboardType="number-pad"
              maxLength={3}
              editable={!busy}
            />

            <Kicker>Choose a 6-digit PIN</Kicker>
            <TextInput
              value={pin}
              onChangeText={(t) => {
                const digits = t.replace(/\D/g, "").slice(0, PIN_LENGTH);
                setPin(digits);
                setError(null);
                if (digits.length === PIN_LENGTH) confirmInput.current?.focus();
              }}
              placeholder="••••••"
              placeholderTextColor={color.faint}
              style={[styles.input, styles.pinInput]}
              keyboardType="number-pad"
              secureTextEntry
              maxLength={PIN_LENGTH}
              editable={!busy}
            />

            <Kicker>Confirm PIN</Kicker>
            <TextInput
              ref={confirmInput}
              value={confirmPin}
              onChangeText={(t) => {
                setConfirmPin(t.replace(/\D/g, "").slice(0, PIN_LENGTH));
                setError(null);
              }}
              placeholder="••••••"
              placeholderTextColor={color.faint}
              style={[
                styles.input,
                styles.pinInput,
                confirmPin.length === PIN_LENGTH && !pinsMatch ? styles.inputError : null,
              ]}
              keyboardType="number-pad"
              secureTextEntry
              maxLength={PIN_LENGTH}
              editable={!busy}
            />
            {confirmPin.length === PIN_LENGTH && !pinsMatch ? (
              <Text style={styles.mismatch}>Those PINs don't match.</Text>
            ) : null}
          </View>

          {error ? (
            <View style={styles.error}>
              <Ionicons name="alert-circle" size={16} color={color.crimson} />
              <Text style={styles.errorText}>{error}</Text>
            </View>
          ) : null}

          <View style={{ marginTop: 22 }}>
            <Button
              label="Create account"
              icon="person-add"
              onPress={create}
              loading={busy}
              disabled={!ready}
            />
          </View>

          <Pressable
            onPress={() => router.back()}
            style={{ marginTop: 16, alignItems: "center" }}
            disabled={busy}
          >
            <Text style={styles.link}>I already have an account</Text>
          </Pressable>
    </FormScaffold>
  );
}

const styles = StyleSheet.create({
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 24,
    paddingVertical: 14,
  },
  title: { color: color.ink, fontSize: 26, fontWeight: font.black, letterSpacing: -0.6 },
  sub: { color: color.muted, fontSize: 13.5, lineHeight: 19, marginTop: 9 },
  input: {
    marginTop: 8,
    marginBottom: 18,
    color: color.ink,
    fontSize: 16,
    backgroundColor: color.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: color.hairline,
    padding: 15,
  },
  pinInput: { letterSpacing: 6, fontVariant: ["tabular-nums"] },
  inputError: { borderColor: color.crimson + "66" },
  mismatch: { color: color.crimson, fontSize: 12.5, marginTop: -10, marginBottom: 12 },
  error: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginTop: 4,
    paddingHorizontal: 13,
    paddingVertical: 11,
    borderRadius: radius.sm,
    borderWidth: 1,
    borderColor: color.crimson + "44",
    backgroundColor: color.crimson + "14",
  },
  errorText: { color: color.crimson, fontSize: 13, flex: 1, lineHeight: 18 },
  link: { color: color.signal, fontSize: 14, fontWeight: font.semi },
});
