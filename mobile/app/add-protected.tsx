import React, { useState } from "react";
import { Keyboard, Pressable, StyleSheet, Text, TextInput, View } from "react-native";
import { router } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Button, Card, Kicker } from "@/components/ui";
import { FormScaffold } from "@/components/FormScaffold";
import { api } from "@/lib/api";
import { color, font, radius } from "@/lib/theme";

/** How the *guardian* relates to the person they're protecting. */
const RELATIONSHIPS = ["son", "daughter", "spouse", "sibling", "nephew", "niece", "caregiver", "friend"];

export default function AddProtected() {
  const [phone, setPhone] = useState("+65");
  const [relationship, setRelationship] = useState("son");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sentTo, setSentTo] = useState<string | null>(null);

  const valid = phone.replace(/\D/g, "").length >= 8;

  const invite = async () => {
    if (!valid || busy) return;
    setBusy(true);
    setError(null);
    try {
      const link = await api.protect({ phone: phone.trim(), relationship });
      setSentTo(link.protected.name);
    } catch (e: any) {
      setError(e?.message ?? "Couldn't send the invitation.");
    } finally {
      setBusy(false);
    }
  };

  if (sentTo) {
    return (
      <SafeAreaView style={styles.safe} edges={["top", "bottom"]}>
        <View style={styles.header}>
          <View style={{ width: 26 }} />
          <Text style={styles.headerTitle}>Invitation sent</Text>
          <Pressable onPress={() => router.back()} hitSlop={12}>
            <Ionicons name="close" size={26} color={color.muted} />
          </Pressable>
        </View>
        <View style={styles.done}>
          <View style={styles.doneIcon}>
            <Ionicons name="paper-plane" size={30} color={color.signal} />
          </View>
          <Text style={styles.doneTitle}>Waiting for {sentTo}</Text>
          <Text style={styles.doneBody}>
            {sentTo} will see your invitation the next time they open HyperGuard. Nothing
            about their account is shared with you until they accept.
          </Text>
          <View style={{ width: "100%", marginTop: 26 }}>
            <Button label="Done" onPress={() => router.back()} />
          </View>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <FormScaffold
      header={
        <View style={styles.header}>
          <Pressable onPress={() => router.back()} hitSlop={12}>
            <Ionicons name="close" size={26} color={color.muted} />
          </Pressable>
          <Text style={styles.headerTitle}>Add someone to protect</Text>
          <View style={{ width: 26 }} />
        </View>
      }
      footer={
        <Button
          label="Send invitation"
          icon="paper-plane"
          onPress={invite}
          loading={busy}
          disabled={!valid}
        />
      }
    >
      <Text style={styles.intro}>
        A parent or relative you worry about. Once they accept, you'll be alerted the
        moment HyperGuard steps in for them — and you'll be able to read exactly what
        happened.
      </Text>

      <Kicker>Their phone number</Kicker>
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
        autoFocus
        editable={!busy}
        returnKeyType="done"
        onSubmitEditing={() => {
          Keyboard.dismiss();
          if (valid) invite();
        }}
      />

      <Kicker>You are their…</Kicker>
      <View style={styles.chips}>
        {RELATIONSHIPS.map((r) => {
          const active = r === relationship;
          return (
            <Pressable
              key={r}
              onPress={() => setRelationship(r)}
              style={[
                styles.chip,
                active && { borderColor: color.signal, backgroundColor: color.signalSoft },
              ]}
              disabled={busy}
            >
              <Text style={[styles.chipText, active && { color: color.signal }]}>{r}</Text>
            </Pressable>
          );
        })}
      </View>

      {error ? (
        <View style={styles.error}>
          <Ionicons name="alert-circle" size={16} color={color.crimson} />
          <Text style={styles.errorText}>{error}</Text>
        </View>
      ) : null}

      <Card style={styles.consent}>
        <Ionicons name="lock-closed" size={17} color={color.ice} />
        <Text style={styles.consentText}>
          They decide. We'll send an invitation they have to accept — you won't see
          their balance, their transfers, or anything else until they do.
        </Text>
      </Card>
    </FormScaffold>
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
  headerTitle: { color: color.ink, fontSize: 16, fontWeight: font.bold },
  intro: { color: color.muted, fontSize: 14, lineHeight: 20, marginBottom: 24 },
  input: {
    marginTop: 8,
    marginBottom: 22,
    color: color.ink,
    fontSize: 17,
    backgroundColor: color.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: color.hairline,
    padding: 15,
    fontVariant: ["tabular-nums"],
  },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 10 },
  chip: {
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: color.hairline,
    paddingHorizontal: 14,
    paddingVertical: 8,
  },
  chipText: { color: color.muted, fontSize: 13.5, fontWeight: font.medium, textTransform: "capitalize" },
  error: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginTop: 20,
    paddingHorizontal: 13,
    paddingVertical: 11,
    borderRadius: radius.sm,
    borderWidth: 1,
    borderColor: color.crimson + "44",
    backgroundColor: color.crimson + "14",
  },
  errorText: { color: color.crimson, fontSize: 13, flex: 1, lineHeight: 18 },
  consent: { flexDirection: "row", alignItems: "flex-start", gap: 11, marginTop: 24 },
  consentText: { color: color.muted, fontSize: 12.5, lineHeight: 18, flex: 1 },
  done: { flex: 1, alignItems: "center", justifyContent: "center", padding: 30 },
  doneIcon: {
    width: 66,
    height: 66,
    borderRadius: 22,
    backgroundColor: color.signalSoft,
    alignItems: "center",
    justifyContent: "center",
  },
  doneTitle: {
    color: color.ink,
    fontSize: 21,
    fontWeight: font.black,
    letterSpacing: -0.4,
    marginTop: 20,
  },
  doneBody: {
    color: color.muted,
    fontSize: 14,
    lineHeight: 21,
    textAlign: "center",
    marginTop: 12,
  },
});
