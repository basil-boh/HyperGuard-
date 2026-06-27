import React, { useEffect, useRef } from "react";
import { ActivityIndicator, Animated, ScrollView, StyleSheet, Text, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Button, Card, Kicker } from "@/components/ui";
import { AgentRelay } from "@/components/AgentRelay";
import { RiskGauge } from "@/components/RiskGauge";
import { Transcript } from "@/components/Transcript";
import { useIntervention } from "@/lib/useIntervention";
import { pct } from "@/lib/format";
import { color, font, radius } from "@/lib/theme";

const VERDICT = {
  block: { label: "Transfer blocked", tint: color.crimson, icon: "shield" as const, sub: "Your money stayed in your account" },
  hold: { label: "Held for review", tint: color.amber, icon: "pause" as const, sub: "Pending your confirmation" },
  approve: { label: "Transfer approved", tint: color.signal, icon: "checkmark-circle" as const, sub: "Sent securely" },
};

const ACTION_META: Record<string, { label: string; tint: string }> = {
  escalate: { label: "Likely scam — escalated", tint: color.crimson },
  monitor: { label: "Monitoring", tint: color.amber },
  clear: { label: "Looks legitimate", tint: color.signal },
};

export default function Intervention() {
  const { caseId } = useLocalSearchParams<{ caseId: string }>();
  const v = useIntervention(caseId);
  const reviewing = !v.done;
  const showCall = !!v.call || v.transcript.length > 0;
  const scam = v.classification && v.classification.archetype !== "none" && v.classification.confidence >= 0.4;

  return (
    <SafeAreaView style={styles.safe} edges={["top", "bottom"]}>
      <LiveHeader reviewing={reviewing} decision={v.decision} />

      <ScrollView contentContainerStyle={{ padding: 20, paddingBottom: 28 }} showsVerticalScrollIndicator={false}>
        {/* Risk */}
        <Card>
          <RiskGauge
            score={v.risk?.score ?? null}
            band={v.risk?.band ?? null}
            rationale={v.risk?.rationale}
            pending={reviewing}
          />
        </Card>

        {/* Relay */}
        <Kicker tint={color.faint}>{" "}</Kicker>
        <Text style={styles.section}>Agent swarm</Text>
        <Card>
          <AgentRelay agents={v.agents} />
        </Card>

        {/* Call */}
        {showCall && (
          <>
            <Text style={styles.section}>Live call</Text>
            <Card>
              <View style={styles.callHead}>
                <Ionicons name="call" size={15} color={v.call?.live ? color.signal : color.faint} />
                <Text style={styles.callMeta}>{v.call?.live ? "Telephony connected" : "Simulated call"}</Text>
              </View>
              <Transcript turns={v.transcript} live={reviewing && showCall} />
            </Card>
          </>
        )}

        {/* Scam classification */}
        {scam && (
          <>
            <Text style={styles.section}>What we detected</Text>
            <Card style={{ borderColor: color.crimson + "55" }}>
              <View style={styles.scamHead}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.scamKicker}>Scam pattern matched</Text>
                  <Text style={styles.scamTitle}>{v.classification!.title}</Text>
                </View>
                <Text style={styles.scamConf}>{pct(v.classification!.confidence)}</Text>
              </View>
              <View style={styles.tags}>
                {v.classification!.indicators.slice(0, 6).map((i) => (
                  <View key={i} style={styles.tag}>
                    <Text style={styles.tagText}>{i}</Text>
                  </View>
                ))}
              </View>
              <View style={styles.guidance}>
                <Text style={styles.guidanceText}>{v.classification!.guidance}</Text>
              </View>
            </Card>
          </>
        )}

        {/* Guardian */}
        {v.guardian && (
          <>
            <Text style={styles.section}>Guardian alerted</Text>
            <Card style={{ flexDirection: "row", alignItems: "center", gap: 13 }}>
              <View style={styles.guardianIcon}>
                <Ionicons name="people" size={20} color={color.ice} />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={styles.guardianName}>{v.guardian.name}</Text>
                <Text style={styles.guardianMeta}>
                  {v.guardian.relationship} · notified via {v.guardian.channel}
                </Text>
              </View>
              {v.guardian.acknowledged && (
                <View style={styles.ackTag}>
                  <Text style={styles.ackText}>Acknowledged</Text>
                </View>
              )}
            </Card>
          </>
        )}

        {/* Voice follow-up: what the customer told us */}
        {v.context.length > 0 && (
          <>
            <Text style={styles.section}>What you told us</Text>
            <Card>
              {v.context.map((c, i) => (
                <View key={i} style={i > 0 ? styles.qaBorder : undefined}>
                  <Text style={styles.qaQ}>{c.question}</Text>
                  <Text style={styles.qaA}>“{c.answer}”</Text>
                </View>
              ))}
            </Card>
          </>
        )}

        {/* Follow-up in progress */}
        {v.followupPending && !v.assessment && (
          <Card style={styles.pendingCard}>
            <ActivityIndicator color={color.signal} />
            <Text style={styles.pendingText}>On a call with you — gathering context and reasoning about this transfer…</Text>
          </Card>
        )}

        {/* AI assessment */}
        {v.assessment && (
          <>
            <Text style={styles.section}>AI assessment</Text>
            <Card style={v.assessment.recommended_action === "escalate" ? { borderColor: color.crimson + "55" } : undefined}>
              <View style={styles.assessHead}>
                <Text style={[styles.assessAction, { color: (ACTION_META[v.assessment.recommended_action] ?? ACTION_META.monitor).tint }]}>
                  {(ACTION_META[v.assessment.recommended_action] ?? ACTION_META.monitor).label}
                </Text>
                <Text style={styles.assessConf}>{pct(v.assessment.scam_likelihood)}</Text>
              </View>
              <Text style={styles.assessReason}>{v.assessment.reasoning}</Text>
              {v.assessment.escalation_reasons?.length > 0 && (
                <View style={styles.tags}>
                  {v.assessment.escalation_reasons.map((r) => (
                    <View key={r} style={styles.tag}><Text style={styles.tagText}>{r}</Text></View>
                  ))}
                </View>
              )}
            </Card>
          </>
        )}

        {/* Escalation + incident report */}
        {v.escalation?.escalated && (
          <>
            <Text style={styles.section}>Escalation</Text>
            <Card>
              <View style={styles.escRow}>
                <Ionicons name="people" size={16} color={color.ice} />
                <Text style={styles.escText}>
                  {v.escalation.guardians_notified} guardian{v.escalation.guardians_notified === 1 ? "" : "s"} alerted by SMS
                </Text>
              </View>
              <View style={[styles.escRow, { marginTop: 10 }]}>
                <Ionicons name="document-text" size={16} color={color.signal} />
                <Text style={styles.escText}>Incident report filed with authorities</Text>
              </View>
            </Card>
            {v.report && (
              <>
                <Text style={styles.section}>Incident report</Text>
                <Card><Text style={styles.reportText}>{v.report}</Text></Card>
              </>
            )}
          </>
        )}

        {/* Verdict */}
        {v.done && v.decision && (
          <View style={styles.verdictWrap}>
            <Verdict decision={v.decision} narrative={v.narrative} />
          </View>
        )}
      </ScrollView>

      {v.done && (
        <View style={styles.footer}>
          <Button
            label={v.decision === "block" ? "Got it, keep me safe" : "Done"}
            icon={v.decision === "block" ? "shield-checkmark" : "checkmark"}
            onPress={() => router.replace("/")}
          />
        </View>
      )}
    </SafeAreaView>
  );
}

function LiveHeader({ reviewing, decision }: { reviewing: boolean; decision: string | null }) {
  const a = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    if (!reviewing) return;
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(a, { toValue: 1, duration: 600, useNativeDriver: true }),
        Animated.timing(a, { toValue: 0, duration: 600, useNativeDriver: true }),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [reviewing]);

  const tint = reviewing ? color.signal : decision === "block" ? color.crimson : color.signal;
  return (
    <View style={styles.header}>
      <Animated.View style={[styles.liveDot, { backgroundColor: tint, opacity: reviewing ? a : 1 }]} />
      <Text style={styles.headerTitle}>
        {reviewing ? "HyperGuard is reviewing this transfer" : "Review complete"}
      </Text>
    </View>
  );
}

function Verdict({ decision, narrative }: { decision: string; narrative: string | null }) {
  const f = VERDICT[decision as keyof typeof VERDICT] ?? VERDICT.approve;
  return (
    <View style={[styles.verdict, { borderColor: f.tint, backgroundColor: f.tint + "12" }]}>
      <View style={[styles.verdictIcon, { borderColor: f.tint }]}>
        <Ionicons name={f.icon} size={30} color={f.tint} />
      </View>
      <Text style={[styles.verdictLabel, { color: f.tint }]}>{f.label}</Text>
      <Text style={styles.verdictSub}>{f.sub}</Text>
      {narrative ? <Text style={styles.verdictNarr}>{narrative}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: color.void },
  header: { flexDirection: "row", alignItems: "center", gap: 9, paddingHorizontal: 20, paddingVertical: 16, borderBottomWidth: 1, borderBottomColor: color.hairline },
  liveDot: { width: 9, height: 9, borderRadius: 5 },
  headerTitle: { color: color.ink, fontSize: 14.5, fontWeight: font.semi, flex: 1 },
  section: { color: color.muted, fontSize: 12, fontWeight: font.bold, letterSpacing: 1.4, textTransform: "uppercase", marginTop: 22, marginBottom: 10 },
  callHead: { flexDirection: "row", alignItems: "center", gap: 7, marginBottom: 14 },
  callMeta: { color: color.faint, fontSize: 11.5, textTransform: "uppercase", letterSpacing: 1 },
  scamHead: { flexDirection: "row", alignItems: "flex-start" },
  scamKicker: { color: color.crimson, fontSize: 11, fontWeight: font.bold, textTransform: "uppercase", letterSpacing: 1 },
  scamTitle: { color: color.ink, fontSize: 18, fontWeight: font.bold, marginTop: 4 },
  scamConf: { color: color.crimson, fontSize: 22, fontWeight: font.black, fontVariant: ["tabular-nums"] },
  tags: { flexDirection: "row", flexWrap: "wrap", gap: 6, marginTop: 12 },
  tag: { borderRadius: 6, borderWidth: 1, borderColor: color.crimson + "44", backgroundColor: color.crimson + "12", paddingHorizontal: 8, paddingVertical: 3 },
  tagText: { color: color.ember, fontSize: 11 },
  guidance: { marginTop: 14, borderLeftWidth: 2, borderLeftColor: color.signal, backgroundColor: color.signalSoft, borderRadius: 8, padding: 12 },
  guidanceText: { color: color.ink, fontSize: 13.5, lineHeight: 20 },
  guardianIcon: { width: 40, height: 40, borderRadius: 12, backgroundColor: color.ice + "1a", alignItems: "center", justifyContent: "center" },
  guardianName: { color: color.ink, fontSize: 15, fontWeight: font.semi },
  guardianMeta: { color: color.faint, fontSize: 12.5, marginTop: 2, textTransform: "capitalize" },
  ackTag: { borderRadius: radius.pill, backgroundColor: color.signalSoft, paddingHorizontal: 9, paddingVertical: 4 },
  ackText: { color: color.signal, fontSize: 10.5, fontWeight: font.bold, textTransform: "uppercase" },
  qaBorder: { borderTopWidth: 1, borderTopColor: color.hairline, marginTop: 12, paddingTop: 12 },
  qaQ: { color: color.faint, fontSize: 12.5, lineHeight: 18 },
  qaA: { color: color.ink, fontSize: 14.5, lineHeight: 20, marginTop: 4, fontStyle: "italic" },
  pendingCard: { marginTop: 18, flexDirection: "row", alignItems: "center", gap: 12 },
  pendingText: { color: color.muted, fontSize: 13, lineHeight: 19, flex: 1 },
  assessHead: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginBottom: 8 },
  assessAction: { fontSize: 15.5, fontWeight: font.bold },
  assessConf: { color: color.muted, fontSize: 18, fontWeight: font.black, fontVariant: ["tabular-nums"] },
  assessReason: { color: color.ink, fontSize: 13.5, lineHeight: 20 },
  escRow: { flexDirection: "row", alignItems: "center", gap: 10 },
  escText: { color: color.ink, fontSize: 14, flex: 1 },
  reportText: { color: color.muted, fontSize: 12.5, lineHeight: 19, fontVariant: ["tabular-nums"] },
  verdictWrap: { marginTop: 26 },
  verdict: { borderRadius: radius.lg, borderWidth: 1, padding: 24, alignItems: "center" },
  verdictIcon: { width: 60, height: 60, borderRadius: 30, borderWidth: 2, alignItems: "center", justifyContent: "center", marginBottom: 14 },
  verdictLabel: { fontSize: 22, fontWeight: font.black, letterSpacing: -0.4 },
  verdictSub: { color: color.muted, fontSize: 12.5, textTransform: "uppercase", letterSpacing: 1, marginTop: 6 },
  verdictNarr: { color: color.muted, fontSize: 14, lineHeight: 21, marginTop: 16, textAlign: "center" },
  footer: { padding: 20, borderTopWidth: 1, borderTopColor: color.hairline },
});
