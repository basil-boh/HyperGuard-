import React, { useCallback, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { router, useFocusEffect, useLocalSearchParams } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Avatar, Button, Card, Kicker, Pill } from "@/components/ui";
import { api } from "@/lib/api";
import { money, pct, relativeDay } from "@/lib/format";
import { bandColor, color, font, radius } from "@/lib/theme";
import type { GuardianLink, IncidentSummary } from "@/lib/types";

/** Everything that has happened to one person I protect. */
export default function ProtectedPerson() {
  const { userId } = useLocalSearchParams<{ userId: string }>();
  const [link, setLink] = useState<GuardianLink | null>(null);
  const [incidents, setIncidents] = useState<IncidentSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useFocusEffect(
    useCallback(() => {
      let alive = true;
      Promise.all([api.network(), api.incidents()])
        .then(([network, all]) => {
          if (!alive) return;
          setLink(network.protecting.find((l) => l.protected_user_id === userId) ?? null);
          setIncidents(all.filter((i) => i.protected_user_id === userId));
        })
        .catch(() => {})
        .finally(() => alive && setLoading(false));
      return () => {
        alive = false;
      };
    }, [userId]),
  );

  const person = link?.protected;

  return (
    <SafeAreaView style={styles.safe} edges={["top", "bottom"]}>
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={color.muted} />
        </Pressable>
        <Text style={styles.headerTitle}>{person?.name ?? "Protecting"}</Text>
        <View style={{ width: 26 }} />
      </View>

      <ScrollView
        contentContainerStyle={{ padding: 20, paddingBottom: 40 }}
        showsVerticalScrollIndicator={false}
      >
        {person ? (
          <Card style={styles.identity}>
            <Avatar name={person.name} size={52} tint={color.signal} />
            <View style={{ flex: 1 }}>
              <Text style={styles.name}>{person.name}</Text>
              <Text style={styles.meta}>
                You are their {link?.relationship}
                {person.age ? ` · ${person.age}` : ""}
              </Text>
              {person.vulnerability_flags.length > 0 ? (
                <View style={styles.flags}>
                  {person.vulnerability_flags.map((flag) => (
                    <Pill key={flag} label={flag.replace(/_/g, " ")} tint={color.amber} />
                  ))}
                </View>
              ) : null}
            </View>
          </Card>
        ) : null}

        {link ? (
          <TransferLimitCard
            link={link}
            onChange={(next) =>
              setLink((current) => (current ? { ...current, transfer_limit: next } : current))
            }
          />
        ) : null}

        <View style={styles.sectionHead}>
          <Kicker>Incidents</Kicker>
          <Text style={styles.count}>{incidents.length}</Text>
        </View>

        {loading ? (
          <ActivityIndicator color={color.signal} style={{ marginTop: 30 }} />
        ) : incidents.length === 0 ? (
          <Card style={styles.empty}>
            <Ionicons name="shield-checkmark" size={22} color={color.signal} />
            <Text style={styles.emptyText}>
              Nothing has happened. HyperGuard is watching every transfer
              {person ? ` ${person.name.split(" ")[0]} makes` : ""}, and you'll be told the
              moment it steps in.
            </Text>
          </Card>
        ) : (
          <View style={{ gap: 10 }}>
            {incidents.map((incident) => (
              <Pressable
                key={incident.id}
                onPress={() => router.push(`/incident/${incident.id}`)}
              >
                <Card style={[styles.incident, incident.unread && styles.incidentUnread]}>
                  <View style={styles.incidentTop}>
                    <View
                      style={[
                        styles.dot,
                        { backgroundColor: incident.unread ? color.ember : color.faint },
                      ]}
                    />
                    <Text style={styles.incidentDate}>{relativeDay(incident.sent_at)}</Text>
                    <View style={{ flex: 1 }} />
                    <Text
                      style={[
                        styles.risk,
                        { color: bandColor[bandOf(incident.risk_score)] ?? color.muted },
                      ]}
                    >
                      {pct(incident.risk_score)}
                    </Text>
                  </View>
                  <Text style={styles.incidentAmount}>
                    {money(incident.amount, incident.currency)}
                  </Text>
                  <Text style={styles.incidentPayee}>to {incident.payee_name}</Text>
                  <View style={styles.incidentFoot}>
                    <Pill
                      label={incident.decision === "block" ? "Blocked" : incident.decision}
                      tint={incident.decision === "block" ? color.crimson : color.signal}
                    />
                    {incident.scam_title ? (
                      <Text style={styles.scamTitle} numberOfLines={1}>
                        {incident.scam_title}
                      </Text>
                    ) : null}
                  </View>
                </Card>
              </Pressable>
            ))}
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

/**
 * The guardian's per-transfer ceiling on this account.
 *
 * Deliberately one-sided: only the guardian can change it, so it holds even if the
 * person is being talked through raising it on a call. They can always see it and
 * who set it, and can remove the guardian entirely if they disagree.
 */
function TransferLimitCard({
  link,
  onChange,
}: {
  link: GuardianLink;
  onChange: (next: number | null) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(link.transfer_limit ? String(link.transfer_limit) : "");
  const [busy, setBusy] = useState(false);

  const name = link.protected.name.split(" ")[0];

  const apply = async (amount: number | null) => {
    setBusy(true);
    try {
      const updated = await api.setTransferLimit(link.id, amount);
      onChange(updated.transfer_limit);
      setEditing(false);
    } catch (e: any) {
      Alert.alert("Couldn't update the limit", e?.message ?? "Try again.");
    } finally {
      setBusy(false);
    }
  };

  const save = () => {
    const amount = parseFloat(draft);
    if (!Number.isFinite(amount) || amount <= 0) {
      Alert.alert("Enter an amount", "The limit must be more than zero.");
      return;
    }
    apply(amount);
  };

  const confirmRemove = () =>
    Alert.alert("Remove the limit?", `${name} will be able to transfer any amount again.`, [
      { text: "Cancel", style: "cancel" },
      { text: "Remove", style: "destructive", onPress: () => apply(null) },
    ]);

  return (
    <>
      <View style={styles.sectionHead}>
        <Kicker>Transfer limit</Kicker>
      </View>
      <Card style={{ gap: 12 }}>
        {editing ? (
          <>
            <Text style={styles.limitBody}>
              The most {name} can send in a single transfer. Anything larger is refused
              before it reaches the swarm.
            </Text>
            <View style={styles.limitInputRow}>
              <Text style={styles.limitCurrency}>SGD</Text>
              <TextInput
                value={draft}
                onChangeText={(t) => setDraft(t.replace(/[^0-9.]/g, ""))}
                placeholder="500"
                placeholderTextColor={color.faint}
                style={styles.limitInput}
                keyboardType="decimal-pad"
                autoFocus
                editable={!busy}
              />
            </View>
            <View style={styles.limitChips}>
              {[200, 500, 1000, 2000].map((v) => (
                <Pressable key={v} style={styles.limitChip} onPress={() => setDraft(String(v))}>
                  <Text style={styles.limitChipText}>{v.toLocaleString()}</Text>
                </Pressable>
              ))}
            </View>
            <Button label="Set limit" icon="lock-closed" onPress={save} loading={busy} />
            <Pressable onPress={() => setEditing(false)} style={{ alignItems: "center" }}>
              <Text style={styles.limitLink}>Cancel</Text>
            </Pressable>
          </>
        ) : link.transfer_limit ? (
          <>
            <View style={styles.limitRow}>
              <Ionicons name="lock-closed" size={18} color={color.signal} />
              <View style={{ flex: 1 }}>
                <Text style={styles.limitAmount}>{money(link.transfer_limit, "SGD")}</Text>
                <Text style={styles.limitMeta}>per transfer · set by you</Text>
              </View>
            </View>
            <View style={{ flexDirection: "row", gap: 10 }}>
              <View style={{ flex: 1 }}>
                <Button
                  label="Change"
                  variant="ghost"
                  onPress={() => {
                    setDraft(String(link.transfer_limit));
                    setEditing(true);
                  }}
                />
              </View>
              <View style={{ flex: 1 }}>
                <Button label="Remove" variant="ghost" onPress={confirmRemove} />
              </View>
            </View>
          </>
        ) : (
          <>
            <View style={styles.limitRow}>
              <Ionicons name="lock-open-outline" size={18} color={color.faint} />
              <Text style={styles.limitBody}>
                No limit. {name} can transfer any amount, subject to the swarm's review.
              </Text>
            </View>
            <Button
              label="Set a transfer limit"
              icon="lock-closed"
              variant="ghost"
              onPress={() => setEditing(true)}
            />
          </>
        )}
      </Card>
    </>
  );
}

function bandOf(score: number): string {
  if (score >= 0.85) return "critical";
  if (score >= 0.6) return "high";
  if (score >= 0.35) return "elevated";
  return "minimal";
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
  identity: { flexDirection: "row", alignItems: "center", gap: 14 },
  name: { color: color.ink, fontSize: 17, fontWeight: font.bold },
  meta: { color: color.faint, fontSize: 12.5, marginTop: 3, textTransform: "capitalize" },
  flags: { flexDirection: "row", flexWrap: "wrap", gap: 6, marginTop: 8 },
  sectionHead: { flexDirection: "row", alignItems: "center", gap: 8, marginTop: 26, marginBottom: 12 },
  count: {
    color: color.faint,
    fontSize: 11,
    fontWeight: font.bold,
    backgroundColor: color.raised,
    borderRadius: radius.pill,
    paddingHorizontal: 7,
    paddingVertical: 1,
    overflow: "hidden",
  },
  empty: { flexDirection: "row", alignItems: "flex-start", gap: 12 },
  emptyText: { color: color.muted, fontSize: 13, lineHeight: 19, flex: 1 },
  incident: { gap: 3 },
  incidentUnread: { borderColor: color.ember + "55", backgroundColor: color.ember + "0d" },
  incidentTop: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 6 },
  dot: { width: 7, height: 7, borderRadius: 4 },
  incidentDate: { color: color.faint, fontSize: 12 },
  risk: { fontSize: 12.5, fontWeight: font.bold, fontVariant: ["tabular-nums"] },
  incidentAmount: {
    color: color.ink,
    fontSize: 20,
    fontWeight: font.black,
    letterSpacing: -0.4,
    fontVariant: ["tabular-nums"],
  },
  incidentPayee: { color: color.muted, fontSize: 13 },
  incidentFoot: { flexDirection: "row", alignItems: "center", gap: 9, marginTop: 10 },
  limitRow: { flexDirection: "row", alignItems: "center", gap: 12 },
  limitAmount: {
    color: color.ink,
    fontSize: 19,
    fontWeight: font.black,
    letterSpacing: -0.4,
    fontVariant: ["tabular-nums"],
  },
  limitMeta: { color: color.faint, fontSize: 12, marginTop: 2 },
  limitBody: { color: color.muted, fontSize: 13, lineHeight: 19, flex: 1 },
  limitInputRow: { flexDirection: "row", alignItems: "center", gap: 10 },
  limitCurrency: { color: color.muted, fontSize: 17, fontWeight: font.semi },
  limitInput: {
    flex: 1,
    color: color.ink,
    fontSize: 30,
    fontWeight: font.black,
    letterSpacing: -0.8,
    padding: 0,
    fontVariant: ["tabular-nums"],
  },
  limitChips: { flexDirection: "row", gap: 8 },
  limitChip: {
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: color.hairline,
    paddingHorizontal: 13,
    paddingVertical: 6,
  },
  limitChipText: { color: color.muted, fontSize: 12.5, fontWeight: font.medium },
  limitLink: { color: color.signal, fontSize: 13.5, fontWeight: font.semi },
  scamTitle: { color: color.amber, fontSize: 12, flex: 1 },
});
