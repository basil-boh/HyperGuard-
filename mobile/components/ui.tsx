import React from "react";
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  View,
  ViewStyle,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { color, font, radius } from "@/lib/theme";

export function ShieldLogo({ size = 26 }: { size?: number }) {
  return (
    <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
      <Ionicons name="shield-checkmark" size={size} color={color.signal} />
      <Text style={{ color: color.ink, fontSize: 16, fontWeight: font.bold, letterSpacing: -0.3 }}>
        Hyper<Text style={{ color: color.signal }}>Guard</Text>
      </Text>
    </View>
  );
}

export function Kicker({ children, tint }: { children: React.ReactNode; tint?: string }) {
  return <Text style={[styles.kicker, tint ? { color: tint } : null]}>{children}</Text>;
}

export function Card({
  children,
  style,
  padded = true,
}: {
  children: React.ReactNode;
  style?: ViewStyle;
  padded?: boolean;
}) {
  return <View style={[styles.card, padded && { padding: 18 }, style]}>{children}</View>;
}

export function Avatar({ name, tint = color.ice, size = 44 }: { name: string; tint?: string; size?: number }) {
  const ini = name
    .split(" ")
    .map((p) => p[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
  return (
    <View
      style={{
        width: size,
        height: size,
        borderRadius: size / 3,
        backgroundColor: color.raised,
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <Text style={{ color: tint, fontWeight: font.bold, fontSize: size * 0.32 }}>{ini}</Text>
    </View>
  );
}

export function Pill({ label, tint }: { label: string; tint: string }) {
  return (
    <View style={[styles.pill, { borderColor: tint, backgroundColor: tint + "1a" }]}>
      <Text style={{ color: tint, fontSize: 11, fontWeight: font.semi, textTransform: "uppercase", letterSpacing: 0.6 }}>
        {label}
      </Text>
    </View>
  );
}

export function Button({
  label,
  onPress,
  variant = "primary",
  icon,
  loading,
  disabled,
}: {
  label: string;
  onPress?: () => void;
  variant?: "primary" | "ghost" | "danger";
  icon?: keyof typeof Ionicons.glyphMap;
  loading?: boolean;
  disabled?: boolean;
}) {
  const bg =
    variant === "primary" ? color.signal : variant === "danger" ? color.crimson : "transparent";
  const fg = variant === "primary" ? color.void : variant === "danger" ? "#fff" : color.ink;
  const border = variant === "ghost" ? color.hairline : "transparent";
  return (
    <Pressable
      onPress={disabled || loading ? undefined : onPress}
      style={({ pressed }) => [
        styles.btn,
        { backgroundColor: bg, borderColor: border, opacity: disabled ? 0.4 : pressed ? 0.85 : 1 },
      ]}
    >
      {loading ? (
        <ActivityIndicator color={fg} />
      ) : (
        <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
          {icon && <Ionicons name={icon} size={18} color={fg} />}
          <Text style={{ color: fg, fontWeight: font.bold, fontSize: 15 }}>{label}</Text>
        </View>
      )}
    </Pressable>
  );
}

export function Divider() {
  return <View style={styles.divider} />;
}

const styles = StyleSheet.create({
  kicker: {
    color: color.faint,
    fontSize: 11,
    fontWeight: font.semi,
    letterSpacing: 2,
    textTransform: "uppercase",
  },
  card: {
    backgroundColor: color.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: color.hairline,
  },
  pill: {
    alignSelf: "flex-start",
    borderRadius: radius.pill,
    borderWidth: 1,
    paddingHorizontal: 10,
    paddingVertical: 3,
  },
  btn: {
    borderRadius: radius.md,
    borderWidth: 1,
    paddingVertical: 15,
    alignItems: "center",
    justifyContent: "center",
  },
  divider: { height: 1, backgroundColor: color.hairline, marginVertical: 4 },
});
