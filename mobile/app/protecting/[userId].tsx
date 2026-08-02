import React, { useCallback, useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { router, useFocusEffect, useLocalSearchParams } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Avatar, Card, Kicker, Pill } from "@/components/ui";
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
  scamTitle: { color: color.amber, fontSize: 12, flex: 1 },
});
