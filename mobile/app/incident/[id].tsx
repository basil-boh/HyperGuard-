import React, { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Button, Card, Kicker, Pill } from "@/components/ui";
import { api } from "@/lib/api";
import { money, pct, relativeDay } from "@/lib/format";
import { bandColor, color, font, radius } from "@/lib/theme";
import type { AuthorityFiling, IncidentDetail } from "@/lib/types";

/**
 * What happened, told to the guardian.
 *
 * The "Alert authorities" action produces a SIMULATED filing — HyperGuard has no
 * connection to the police or the National Anti-Scam Centre. That is stated on the
 * button, on the result, and in the disclaimer beneath both; do not soften it.
 */
export default function IncidentScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const [data, setData] = useState<IncidentDetail | null>(null);
  const [filing, setFiling] = useState<AuthorityFiling | null>(null);
  const [loading, setLoading] = useState(true);
  const [filingBusy, setFilingBusy] = useState(false);

  useEffect(() => {
    api
      .incident(id)
      .then((detail) => {
        setData(detail);
        setFiling(detail.filing);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [id]);

  const fileReport = async () => {
    setFilingBusy(true);
    try {
      const result = await api.fileWithAuthorities(id);
      setFiling(result.filing);
    } catch (e: any) {
      Alert.alert("Couldn't file", e?.message ?? "Try again.");
    } finally {
      setFilingBusy(false);
    }
  };

  const confirmFile = () =>
    Alert.alert(
      "Alert the authorities?",
      "This is a simulation. HyperGuard is a prototype and will not contact the police " +
        "or the National Anti-Scam Centre — no report leaves this device. To report a " +
        "real scam, call 1799.",
      [
        { text: "Cancel", style: "cancel" },
        { text: "Run simulation", onPress: fileReport },
      ],
    );

  if (loading) {
    return (
      <SafeAreaView style={styles.safe} edges={["top"]}>
        <ActivityIndicator color={color.signal} style={{ marginTop: 60 }} />
      </SafeAreaView>
    );
  }

  if (!data) {
    return (
      <SafeAreaView style={styles.safe} edges={["top"]}>
        <View style={styles.header}>
          <Pressable onPress={() => router.back()} hitSlop={12}>
            <Ionicons name="chevron-back" size={26} color={color.muted} />
          </Pressable>
          <Text style={styles.headerTitle}>Incident</Text>
          <View style={{ width: 26 }} />
        </View>
        <Text style={styles.missing}>This report isn't available.</Text>
      </SafeAreaView>
    );
  }

  const { report, protected: person, case: incident } = data;
  const band = incident.band ?? "high";

  return (
    <SafeAreaView style={styles.safe} edges={["top", "bottom"]}>
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={color.muted} />
        </Pressable>
        <Text style={styles.headerTitle}>Incident report</Text>
        <View style={{ width: 26 }} />
      </View>

      <ScrollView
        contentContainerStyle={{ padding: 20, paddingBottom: 44 }}
        showsVerticalScrollIndicator={false}
      >
        {/* Headline */}
        <Text style={styles.who}>
          {person.name || report.protected_name}
          <Text style={styles.when}>  ·  {relativeDay(report.sent_at)}</Text>
        </Text>
        <Text style={styles.amount}>{money(incident.amount, incident.currency)}</Text>
        <Text style={styles.payee}>to {incident.payee_name}</Text>

        <View style={styles.badges}>
          <Pill
            label={incident.decision === "block" ? "Blocked" : incident.decision}
            tint={incident.decision === "block" ? color.crimson : color.signal}
          />
          <Pill label={`risk ${pct(incident.risk_score)}`} tint={bandColor[band] ?? color.amber} />
          {incident.escalated ? <Pill label="Guardians alerted" tint={color.ice} /> : null}
        </View>

        {/* The one-paragraph version */}
        <Card style={styles.narrativeCard}>
          <Text style={styles.narrative}>{incident.narrative}</Text>
        </Card>

        {/* What the scam was */}
        {incident.classification ? (
          <>
            <Kicker>The scam</Kicker>
            <Card style={{ marginTop: 10, gap: 9 }}>
              <Text style={styles.scamTitle}>{incident.classification.title}</Text>
              {incident.classification.how_it_works ? (
                <Text style={styles.body}>{incident.classification.how_it_works}</Text>
              ) : null}
              {Array.isArray(incident.classification.indicators) &&
              incident.classification.indicators.length > 0 ? (
                <View style={styles.chips}>
                  {incident.classification.indicators.map((ind: string) => (
                    <View key={ind} style={styles.chip}>
                      <Text style={styles.chipText}>{ind}</Text>
                    </View>
                  ))}
                </View>
              ) : null}
            </Card>
          </>
        ) : null}

        {/* Why it was stopped */}
        {incident.risk_signals.length > 0 ? (
          <>
            <Kicker>Why it was stopped</Kicker>
            <Card style={{ marginTop: 10, gap: 12 }}>
              {incident.risk_signals.map((signal) => (
                <View key={signal.code} style={styles.signal}>
                  <Ionicons
                    name={signal.severity === "alarm" ? "alert-circle" : "information-circle"}
                    size={16}
                    color={signal.severity === "alarm" ? color.ember : color.muted}
                  />
                  <View style={{ flex: 1 }}>
                    <Text style={styles.signalLabel}>{signal.label}</Text>
                    <Text style={styles.signalDetail}>{signal.detail}</Text>
                  </View>
                </View>
              ))}
            </Card>
          </>
        ) : null}

        {/* The call */}
        {incident.transcript.length > 0 ? (
          <>
            <Kicker>What was said on the call</Kicker>
            <Card style={{ marginTop: 10, gap: 12 }}>
              {incident.transcript.map((turn) => (
                <View key={turn.index} style={styles.turn}>
                  <Text
                    style={[
                      styles.speaker,
                      { color: turn.speaker === "agent" ? color.signal : color.ice },
                    ]}
                  >
                    {turn.speaker === "agent" ? "HyperGuard" : person.name.split(" ")[0]}
                  </Text>
                  <Text style={styles.turnText}>{turn.text}</Text>
                </View>
              ))}
            </Card>
          </>
        ) : null}

        {/* Simulated authority filing */}
        <Kicker>Report to authorities</Kicker>
        {filing ? (
          <Card style={styles.filedCard}>
            <View style={styles.simBanner}>
              <Ionicons name="flask" size={14} color={color.amber} />
              <Text style={styles.simBannerText}>SIMULATED — nothing was sent</Text>
            </View>
            <View style={styles.filedRow}>
              <Text style={styles.filedKey}>Reference</Text>
              <Text style={styles.filedRef}>{filing.reference}</Text>
            </View>
            <View style={styles.filedRow}>
              <Text style={styles.filedKey}>Filed</Text>
              <Text style={styles.filedVal}>{relativeDay(filing.filed_at)}</Text>
            </View>
            <View style={styles.filedRow}>
              <Text style={styles.filedKey}>Status</Text>
              <Text style={[styles.filedVal, { color: color.signal }]}>
                {filing.status.replace(/_/g, " ")}
              </Text>
            </View>

            <View style={styles.timeline}>
              {filing.timeline.map((step, i) => (
                <View key={`${step.status}-${i}`} style={styles.step}>
                  <View style={styles.stepRail}>
                    <View style={styles.stepDot} />
                    {i < filing.timeline.length - 1 ? <View style={styles.stepLine} /> : null}
                  </View>
                  <View style={{ flex: 1, paddingBottom: 14 }}>
                    <Text style={styles.stepStatus}>{step.status.replace(/_/g, " ")}</Text>
                    <Text style={styles.stepNote}>{step.note}</Text>
                  </View>
                </View>
              ))}
            </View>

            <Text style={styles.disclaimer}>{filing.disclaimer}</Text>
          </Card>
        ) : (
          <Card style={styles.fileCard}>
            <View style={styles.simBanner}>
              <Ionicons name="flask" size={14} color={color.amber} />
              <Text style={styles.simBannerText}>SIMULATED — no real report is filed</Text>
            </View>
            <Text style={styles.body}>
              Generate the hand-off an anti-scam unit would receive: the risk rationale,
              the call transcript, the scam classification and the beneficiary account.
            </Text>
            <Button
              label="Alert authorities"
              icon="shield"
              onPress={confirmFile}
              loading={filingBusy}
            />
            <Text style={styles.realHelp}>
              To report a real scam in Singapore, call the ScamShield helpline on 1799 or
              file at police.gov.sg.
            </Text>
          </Card>
        )}
      </ScrollView>
    </SafeAreaView>
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
  missing: { color: color.muted, fontSize: 14, textAlign: "center", marginTop: 40 },
  who: { color: color.muted, fontSize: 13.5, fontWeight: font.semi },
  when: { color: color.faint, fontWeight: font.regular },
  amount: {
    color: color.ink,
    fontSize: 34,
    fontWeight: font.black,
    letterSpacing: -1,
    marginTop: 6,
    fontVariant: ["tabular-nums"],
  },
  payee: { color: color.muted, fontSize: 14.5, marginTop: 2 },
  badges: { flexDirection: "row", flexWrap: "wrap", gap: 7, marginTop: 14 },
  narrativeCard: { marginTop: 18, marginBottom: 26, backgroundColor: color.abyss },
  narrative: { color: color.ink, fontSize: 14, lineHeight: 21 },
  body: { color: color.muted, fontSize: 13.5, lineHeight: 20 },
  scamTitle: { color: color.amber, fontSize: 15.5, fontWeight: font.bold },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: 6, marginTop: 2 },
  chip: {
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: color.hairline,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  chipText: { color: color.faint, fontSize: 11.5 },
  signal: { flexDirection: "row", alignItems: "flex-start", gap: 10 },
  signalLabel: { color: color.ink, fontSize: 13.5, fontWeight: font.semi },
  signalDetail: { color: color.faint, fontSize: 12.5, lineHeight: 18, marginTop: 2 },
  turn: { gap: 3 },
  speaker: {
    fontSize: 10.5,
    fontWeight: font.bold,
    letterSpacing: 1.1,
    textTransform: "uppercase",
  },
  turnText: { color: color.ink, fontSize: 13.5, lineHeight: 20 },
  fileCard: { marginTop: 10, gap: 14 },
  filedCard: { marginTop: 10, gap: 9 },
  simBanner: {
    flexDirection: "row",
    alignItems: "center",
    gap: 7,
    alignSelf: "flex-start",
    borderRadius: radius.sm,
    borderWidth: 1,
    borderColor: color.amber + "55",
    backgroundColor: color.amber + "14",
    paddingHorizontal: 10,
    paddingVertical: 6,
  },
  simBannerText: {
    color: color.amber,
    fontSize: 10.5,
    fontWeight: font.bold,
    letterSpacing: 0.8,
  },
  filedRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  filedKey: { color: color.faint, fontSize: 12.5 },
  filedVal: { color: color.ink, fontSize: 13, fontWeight: font.semi, textTransform: "capitalize" },
  filedRef: {
    color: color.ink,
    fontSize: 13,
    fontWeight: font.bold,
    fontVariant: ["tabular-nums"],
  },
  timeline: { marginTop: 10 },
  step: { flexDirection: "row", gap: 11 },
  stepRail: { alignItems: "center", width: 10 },
  stepDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: color.signal, marginTop: 5 },
  stepLine: { flex: 1, width: 1, backgroundColor: color.hairline, marginTop: 3 },
  stepStatus: {
    color: color.ink,
    fontSize: 12.5,
    fontWeight: font.semi,
    textTransform: "capitalize",
  },
  stepNote: { color: color.faint, fontSize: 12, lineHeight: 17, marginTop: 2 },
  disclaimer: {
    color: color.faint,
    fontSize: 11.5,
    lineHeight: 17,
    marginTop: 6,
    borderTopWidth: 1,
    borderTopColor: color.hairline,
    paddingTop: 12,
  },
  realHelp: { color: color.faint, fontSize: 11.5, lineHeight: 17 },
});
