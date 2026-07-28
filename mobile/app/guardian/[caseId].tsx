import React, { useEffect, useRef, useState } from "react";
import { ActivityIndicator, Alert, Animated, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import * as Haptics from "expo-haptics";
import { Button, Card } from "@/components/ui";
import { AgentRelay } from "@/components/AgentRelay";
import { RiskGauge } from "@/components/RiskGauge";
import { Transcript } from "@/components/Transcript";
import { api } from "@/lib/api";
import { useIntervention } from "@/lib/useIntervention";
import { pct } from "@/lib/format";
import { color, font, radius } from "@/lib/theme";

/**
 * Guardian live view: watch the intervention for a family member in real time
 * (same event feed as the victim's screen) and, once the swarm blocks, decide to
 * keep the block or release the transfer.
 */
export default function GuardianCaseView() {
  const { caseId, ward } = useLocalSearchParams<{ caseId: string; ward?: string }>();
  const v = useIntervention(caseId);
  const wardName = ward || "your family member";
  const reviewing = !v.done;
  const showCall = !!v.call || v.transcript.length > 0;
  const scam = v.classification && v.classification.archetype !== "none" && v.classification.confidence >= 0.4;

  const [acting, setActing] = useState<"release" | "hold" | null>(null);
  const [localAction, setLocalAction] = useState<{ action: string; by: string } | null>(null);
  // The guardian.action bus event is authoritative (covers another guardian acting
  // first); our own POST result fills in when the socket is down.
  const acted = v.guardianAction ?? localAction;

  const act = async (action: "release" | "hold") => {
    setActing(action);
    try {
      const res = await api.guardianAction(caseId, action);
      setLocalAction({ action: res.action, by: "You" });
      Haptics.notificationAsync(
        action === "hold"
          ? Haptics.NotificationFeedbackType.Success
          : Haptics.NotificationFeedbackType.Warning,
      ).catch(() => {});
    } catch (e: any) {
      Alert.alert("Couldn't do that", String(e?.message ?? e));
    } finally {
      setActing(null);
    }
  };

  const confirmRelease = () =>
    Alert.alert(
      "Release this transfer?",
      `The money leaves ${wardName}'s account immediately. Only release it if you've spoken to them and are sure this is genuine.`,
      [
        { text: "Cancel", style: "cancel" },
        { text: "Release", style: "destructive", onPress: () => act("release") },
      ],
    );

  const canAct = v.done && v.decision === "block" && !acted;

  return (
    <SafeAreaView style={styles.safe} edges={["top", "bottom"]}>
      <Header wardName={wardName} reviewing={reviewing} link={v.link} />

      <ScrollView contentContainerStyle={{ padding: 20, paddingBottom: 28 }} showsVerticalScrollIndicator={false}>
        <Card>
          <RiskGauge
            score={v.risk?.score ?? null}
            band={v.risk?.band ?? null}
            rationale={v.risk?.rationale}
            pending={reviewing}
          />
        </Card>

        <Text style={styles.section}>Agent swarm</Text>
        <Card>
          <AgentRelay agents={v.agents} />
        </Card>

        {showCall && (
          <>
            <Text style={styles.section}>Call with {wardName}</Text>
            <Card>
              <Transcript turns={v.transcript} live={reviewing && showCall} />
            </Card>
          </>
        )}

        {scam && (
          <>
            <Text style={styles.section}>What HyperGuard detected</Text>
            <Card style={{ borderColor: color.crimson + "55" }}>
              <View style={styles.scamHead}>
                <Text style={styles.scamTitle}>{v.classification!.title}</Text>
                <Text style={styles.scamConf}>{pct(v.classification!.confidence)}</Text>
              </View>
              <Text style={styles.guidanceText}>{v.classification!.guidance}</Text>
            </Card>
          </>
        )}

        {reviewing && (
          <Card style={styles.pendingCard}>
            <ActivityIndicator color={color.signal} />
            <Text style={styles.pendingText}>
              The swarm is still working this transfer. You can step in as soon as it decides.
            </Text>
          </Card>
        )}

        {v.done && v.decision && (
          <>
            <Text style={styles.section}>Verdict</Text>
            <Card
              style={{
                borderColor: (v.decision === "block" ? color.crimson : color.signal) + "66",
              }}
            >
              <View style={styles.verdictRow}>
                <Ionicons
                  name={v.decision === "block" ? "shield" : "checkmark-circle"}
                  size={20}
                  color={v.decision === "block" ? color.crimson : color.signal}
                />
                <Text style={styles.verdictLabel}>
                  {v.decision === "block" ? "Transfer blocked" : v.decision === "hold" ? "Held for review" : "Transfer approved"}
                </Text>
              </View>
              {v.narrative ? <Text style={styles.narrative}>{v.narrative}</Text> : null}
            </Card>
          </>
        )}

        {canAct && (
          <>
            <Text style={styles.section}>Your call</Text>
            <Card>
              <Text style={styles.explain}>
                HyperGuard blocked this transfer. As {wardName}'s guardian you can confirm the
                block — or release the money if you've checked with them and it's genuine.
              </Text>
              <View style={{ gap: 10, marginTop: 16 }}>
                <Button
                  label="Keep it blocked"
                  icon="shield-checkmark"
                  onPress={() => act("hold")}
                  loading={acting === "hold"}
                  disabled={acting !== null}
                />
                <Button
                  label="Release the transfer"
                  icon="alert-circle"
                  variant="danger"
                  onPress={confirmRelease}
                  loading={acting === "release"}
                  disabled={acting !== null}
                />
              </View>
            </Card>
          </>
        )}

        {acted && (
          <Card style={styles.actedCard}>
            <Ionicons
              name={acted.action === "released" ? "arrow-redo" : "shield-checkmark"}
              size={18}
              color={acted.action === "released" ? color.amber : color.signal}
            />
            <Text style={styles.actedText}>
              {acted.by === "You" ? "You" : acted.by}{" "}
              {acted.action === "released" ? "released the transfer." : "kept the block in place."}
            </Text>
          </Card>
        )}
      </ScrollView>

      <View style={styles.footer}>
        <Button label="Back to Guardians" icon="chevron-back" variant="ghost" onPress={() => router.back()} />
      </View>
    </SafeAreaView>
  );
}

function Header({ wardName, reviewing, link }: { wardName: string; reviewing: boolean; link: string }) {
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

  return (
    <View style={styles.header}>
      <Pressable onPress={() => router.back()} hitSlop={10}>
        <Ionicons name="chevron-back" size={22} color={color.ink} />
      </Pressable>
      <View style={{ flex: 1 }}>
        <Text style={styles.headerKicker}>Guardian view</Text>
        <Text style={styles.headerTitle}>Watching over {wardName}</Text>
      </View>
      {reviewing && (
        <View style={styles.liveTag}>
          <Animated.View style={[styles.liveDot, { opacity: a }]} />
          <Text style={styles.liveText}>{link === "live" ? "LIVE" : "SYNCING"}</Text>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: color.void },
  header: { flexDirection: "row", alignItems: "center", gap: 12, paddingHorizontal: 16, paddingVertical: 14, borderBottomWidth: 1, borderBottomColor: color.hairline },
  headerKicker: { color: color.faint, fontSize: 10.5, fontWeight: font.bold, letterSpacing: 1.4, textTransform: "uppercase" },
  headerTitle: { color: color.ink, fontSize: 15.5, fontWeight: font.semi, marginTop: 2 },
  liveTag: { flexDirection: "row", alignItems: "center", gap: 6, borderRadius: radius.pill, borderWidth: 1, borderColor: color.crimson + "66", paddingHorizontal: 9, paddingVertical: 4 },
  liveDot: { width: 7, height: 7, borderRadius: 4, backgroundColor: color.crimson },
  liveText: { color: color.crimson, fontSize: 10, fontWeight: font.black, letterSpacing: 1 },
  section: { color: color.muted, fontSize: 12, fontWeight: font.bold, letterSpacing: 1.4, textTransform: "uppercase", marginTop: 22, marginBottom: 10 },
  scamHead: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  scamTitle: { color: color.ink, fontSize: 16.5, fontWeight: font.bold, flex: 1 },
  scamConf: { color: color.crimson, fontSize: 18, fontWeight: font.black, fontVariant: ["tabular-nums"] },
  guidanceText: { color: color.muted, fontSize: 13, lineHeight: 19, marginTop: 10 },
  pendingCard: { marginTop: 18, flexDirection: "row", alignItems: "center", gap: 12 },
  pendingText: { color: color.muted, fontSize: 13, lineHeight: 19, flex: 1 },
  verdictRow: { flexDirection: "row", alignItems: "center", gap: 9 },
  verdictLabel: { color: color.ink, fontSize: 16, fontWeight: font.bold },
  narrative: { color: color.muted, fontSize: 13, lineHeight: 19, marginTop: 10 },
  explain: { color: color.ink, fontSize: 13.5, lineHeight: 20 },
  actedCard: { flexDirection: "row", alignItems: "center", gap: 10, marginTop: 18 },
  actedText: { color: color.ink, fontSize: 13.5, flex: 1 },
  footer: { padding: 20, borderTopWidth: 1, borderTopColor: color.hairline },
});
