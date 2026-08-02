import React, { useState } from "react";
import { Alert, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { router } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Avatar, Button, Card, Kicker, Pill } from "@/components/ui";
import { api } from "@/lib/api";
import { useFocusFetch } from "@/lib/useFocusFetch";
import { color, font, radius } from "@/lib/theme";
import type { GuardianLink, Network } from "@/lib/types";

/**
 * The guardian network, both directions.
 *
 * "Protecting me" is who HyperGuard alerts when I'm being scammed. "I'm protecting"
 * is who I watch over — their incidents land in my inbox. An invitation I've been
 * sent sits at the top, because being watched over is my decision to make.
 */
export default function NetworkTab() {
  const { data, reload } = useFocusFetch<Network>(api.network);
  const [busyId, setBusyId] = useState<string | null>(null);

  const network = data;
  const invitations = network?.invitations ?? [];
  const guardians = network?.guardians ?? [];
  const protecting = network?.protecting ?? [];
  const sent = network?.invitations_sent ?? [];

  const respond = async (link: GuardianLink, accept: boolean) => {
    setBusyId(link.id);
    try {
      await api.respondToInvitation(link.id, accept);
      reload();
    } catch (e: any) {
      Alert.alert("Couldn't respond", e?.message ?? "Try again.");
    } finally {
      setBusyId(null);
    }
  };

  const confirmRevoke = (link: GuardianLink, label: string, blurb: string) =>
    Alert.alert(`Remove ${label}?`, blurb, [
      { text: "Cancel", style: "cancel" },
      {
        text: "Remove",
        style: "destructive",
        onPress: async () => {
          await api.revokeLink(link.id).catch(() => {});
          reload();
        },
      },
    ]);

  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <ScrollView
        contentContainerStyle={{ padding: 20, paddingBottom: 40 }}
        showsVerticalScrollIndicator={false}
      >
        <Text style={styles.title}>Network</Text>
        <Text style={styles.subtitle}>
          The people who look out for you, and the people you look out for. HyperGuard
          alerts them in real time when it detects a scam in progress.
        </Text>

        {/* Invitations — answered here, because consent is the protected person's */}
        {invitations.map((link) => (
          <Card key={link.id} style={styles.invite}>
            <View style={styles.inviteHead}>
              <Ionicons name="mail-unread" size={19} color={color.amber} />
              <Text style={styles.inviteTitle}>Invitation</Text>
            </View>
            <Text style={styles.inviteBody}>
              <Text style={{ color: color.ink, fontWeight: font.semi }}>
                {link.guardian.name}
              </Text>{" "}
              ({link.relationship}) wants to help protect your account. They'll be alerted
              if HyperGuard spots a scam, and can see incident reports about you.
            </Text>
            <View style={styles.inviteActions}>
              <View style={{ flex: 1 }}>
                <Button
                  label="Accept"
                  icon="checkmark"
                  onPress={() => respond(link, true)}
                  loading={busyId === link.id}
                />
              </View>
              <View style={{ flex: 1 }}>
                <Button
                  label="Decline"
                  variant="ghost"
                  onPress={() => respond(link, false)}
                  disabled={busyId === link.id}
                />
              </View>
            </View>
          </Card>
        ))}

        {/* Who protects me */}
        <View style={styles.sectionHead}>
          <Kicker>Protecting me</Kicker>
          <Text style={styles.count}>{guardians.length}</Text>
        </View>

        {guardians.length === 0 ? (
          <Card style={styles.empty}>
            <Ionicons name="shield-outline" size={20} color={color.faint} />
            <Text style={styles.emptyText}>
              No one is watching over you yet. Adding a guardian is the single biggest
              thing you can do to protect this account.
            </Text>
          </Card>
        ) : (
          <View style={{ gap: 10 }}>
            {guardians.map((link) => (
              <Card key={link.id} style={styles.row}>
                <Avatar name={link.guardian.name} />
                <View style={{ flex: 1 }}>
                  <Text style={styles.name}>{link.guardian.name}</Text>
                  <Text style={styles.meta}>
                    {link.relationship}
                    {link.guardian.phone ? ` · ${link.guardian.phone}` : ""}
                  </Text>
                </View>
                <Pressable
                  onPress={() =>
                    confirmRevoke(
                      link,
                      link.guardian.name,
                      `${link.guardian.name} will no longer be alerted or see incident reports about you.`,
                    )
                  }
                  hitSlop={10}
                >
                  <Ionicons name="close" size={18} color={color.faint} />
                </Pressable>
              </Card>
            ))}
          </View>
        )}

        <View style={{ marginTop: 14 }}>
          <Button
            label="Add guardian"
            icon="person-add"
            variant="ghost"
            onPress={() => router.push("/add-contact")}
          />
        </View>

        {/* Who I protect */}
        <View style={[styles.sectionHead, { marginTop: 30 }]}>
          <Kicker>I'm protecting</Kicker>
          <Text style={styles.count}>{protecting.length}</Text>
        </View>

        {protecting.length === 0 ? (
          <Card style={styles.empty}>
            <Ionicons name="people-outline" size={20} color={color.faint} />
            <Text style={styles.emptyText}>
              Add a parent or relative you worry about. Once they accept, you'll see
              exactly what happened whenever HyperGuard steps in for them.
            </Text>
          </Card>
        ) : (
          <View style={{ gap: 10 }}>
            {protecting.map((link) => {
              const unread = link.incidents?.unread ?? 0;
              const total = link.incidents?.total ?? 0;
              return (
                <Pressable
                  key={link.id}
                  onPress={() => router.push(`/protecting/${link.protected_user_id}`)}
                >
                  <Card style={styles.row}>
                    <Avatar name={link.protected.name} tint={color.signal} />
                    <View style={{ flex: 1 }}>
                      <View style={styles.nameRow}>
                        <Text style={styles.name}>{link.protected.name}</Text>
                        {unread > 0 ? <Pill label={`${unread} new`} tint={color.ember} /> : null}
                      </View>
                      <Text style={styles.meta}>
                        {link.relationship}
                        {link.protected.age ? ` · ${link.protected.age}` : ""}
                      </Text>
                      <Text style={[styles.incidentLine, total > 0 && { color: color.amber }]}>
                        {total === 0
                          ? "No incidents — all clear"
                          : `${total} incident${total === 1 ? "" : "s"} on file`}
                      </Text>
                    </View>
                    <Ionicons name="chevron-forward" size={18} color={color.faint} />
                  </Card>
                </Pressable>
              );
            })}
          </View>
        )}

        {/* Invitations I've sent that haven't been answered */}
        {sent.length > 0 ? (
          <View style={{ marginTop: 14, gap: 8 }}>
            {sent.map((link) => (
              <View key={link.id} style={styles.pendingRow}>
                <Ionicons name="hourglass-outline" size={15} color={color.faint} />
                <Text style={styles.pendingText}>
                  Waiting for {link.protected.name} to accept
                </Text>
                <Pressable
                  onPress={() =>
                    confirmRevoke(
                      link,
                      "invitation",
                      `Cancel the invitation to ${link.protected.name}?`,
                    )
                  }
                  hitSlop={10}
                >
                  <Text style={styles.cancelLink}>Cancel</Text>
                </Pressable>
              </View>
            ))}
          </View>
        ) : null}

        <View style={{ marginTop: 14 }}>
          <Button
            label="Add someone to protect"
            icon="heart-circle"
            variant="ghost"
            onPress={() => router.push("/add-protected")}
          />
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: color.void },
  title: { color: color.ink, fontSize: 26, fontWeight: font.black, letterSpacing: -0.5 },
  subtitle: { color: color.muted, fontSize: 14, lineHeight: 20, marginTop: 8 },
  sectionHead: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginTop: 26,
    marginBottom: 12,
  },
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
  row: { flexDirection: "row", alignItems: "center", gap: 13 },
  nameRow: { flexDirection: "row", alignItems: "center", gap: 8 },
  name: { color: color.ink, fontSize: 15.5, fontWeight: font.semi },
  meta: { color: color.faint, fontSize: 12.5, marginTop: 2, textTransform: "capitalize" },
  incidentLine: { color: color.faint, fontSize: 12, marginTop: 4 },
  empty: { flexDirection: "row", alignItems: "flex-start", gap: 12 },
  emptyText: { color: color.muted, fontSize: 13, lineHeight: 19, flex: 1 },
  invite: {
    marginTop: 20,
    borderColor: color.amber + "55",
    backgroundColor: color.amber + "0f",
    gap: 10,
  },
  inviteHead: { flexDirection: "row", alignItems: "center", gap: 8 },
  inviteTitle: {
    color: color.amber,
    fontSize: 11,
    fontWeight: font.bold,
    letterSpacing: 1.4,
    textTransform: "uppercase",
  },
  inviteBody: { color: color.muted, fontSize: 13.5, lineHeight: 20 },
  inviteActions: { flexDirection: "row", gap: 10, marginTop: 4 },
  pendingRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    paddingHorizontal: 13,
    paddingVertical: 11,
    borderRadius: radius.sm,
    borderWidth: 1,
    borderColor: color.hairline,
    borderStyle: "dashed",
  },
  pendingText: { color: color.faint, fontSize: 12.5, flex: 1 },
  cancelLink: { color: color.muted, fontSize: 12.5, fontWeight: font.semi },
});
