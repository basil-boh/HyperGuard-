import React from "react";
import { Alert, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { router } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Avatar, Button, Card } from "@/components/ui";
import { api } from "@/lib/api";
import { useFocusFetch } from "@/lib/useFocusFetch";
import { color, font } from "@/lib/theme";
import type { Contact } from "@/lib/types";

export default function Family() {
  const { data, reload } = useFocusFetch<Contact[]>(api.contacts);
  const contacts = data ?? [];

  const remove = (c: Contact) =>
    Alert.alert("Remove guardian?", `${c.name} will no longer be alerted to suspicious transfers.`, [
      { text: "Cancel", style: "cancel" },
      {
        text: "Remove",
        style: "destructive",
        onPress: async () => {
          await api.removeContact(c.id).catch(() => {});
          reload();
        },
      },
    ]);

  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <ScrollView contentContainerStyle={{ padding: 20, paddingBottom: 40 }} showsVerticalScrollIndicator={false}>
        <Text style={styles.title}>Guardians</Text>
        <Text style={styles.subtitle}>
          Your next of kin. If HyperGuard detects you're being scammed, it alerts them in real time to
          step in.
        </Text>

        <Card style={styles.banner}>
          <Ionicons name="people-circle" size={26} color={color.signal} />
          <Text style={styles.bannerText}>
            {contacts.length} trusted contact{contacts.length === 1 ? "" : "s"} protecting this account
          </Text>
        </Card>

        <View style={{ gap: 12, marginTop: 20 }}>
          {contacts.map((c) => (
            <Card key={c.id} style={styles.contact}>
              <Avatar name={c.name} />
              <View style={{ flex: 1 }}>
                <Text style={styles.name}>{c.name}</Text>
                <Text style={styles.meta}>
                  {c.relationship} · {c.phone}
                </Text>
              </View>
              {c.priority === 1 && (
                <View style={styles.primaryTag}>
                  <Text style={styles.primaryTagText}>1st</Text>
                </View>
              )}
              <Pressable onPress={() => remove(c)} hitSlop={10}>
                <Ionicons name="close" size={18} color={color.faint} />
              </Pressable>
            </Card>
          ))}
        </View>

        <View style={{ marginTop: 22 }}>
          <Button label="Add next of kin" icon="person-add" variant="ghost" onPress={() => router.push("/add-contact")} />
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: color.void },
  title: { color: color.ink, fontSize: 26, fontWeight: font.black, letterSpacing: -0.5 },
  subtitle: { color: color.muted, fontSize: 14, lineHeight: 20, marginTop: 8 },
  banner: { flexDirection: "row", alignItems: "center", gap: 12, marginTop: 20, backgroundColor: color.signalSoft, borderColor: color.signal + "44" },
  bannerText: { color: color.ink, fontSize: 13.5, fontWeight: font.medium, flex: 1 },
  contact: { flexDirection: "row", alignItems: "center", gap: 13 },
  name: { color: color.ink, fontSize: 15.5, fontWeight: font.semi },
  meta: { color: color.faint, fontSize: 12.5, marginTop: 2, textTransform: "capitalize" },
  primaryTag: { borderRadius: 6, backgroundColor: color.ice + "22", paddingHorizontal: 7, paddingVertical: 3 },
  primaryTagText: { color: color.ice, fontSize: 10.5, fontWeight: font.bold },
});
