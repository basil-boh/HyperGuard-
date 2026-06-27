import React, { useEffect, useRef } from "react";
import { Animated, StyleSheet, Text, View } from "react-native";
import { bandColor, color, font } from "@/lib/theme";
import { pct } from "@/lib/format";

export function RiskGauge({
  score,
  band,
  rationale,
  pending,
}: {
  score: number | null;
  band: string | null;
  rationale?: string | null;
  pending: boolean;
}) {
  const tint = band ? bandColor[band] ?? color.faint : color.faint;
  const w = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(w, {
      toValue: score ?? 0,
      duration: 800,
      useNativeDriver: false,
    }).start();
  }, [score]);

  const width = w.interpolate({ inputRange: [0, 1], outputRange: ["0%", "100%"] });

  return (
    <View>
      <View style={styles.head}>
        <Text style={styles.label}>Fraud risk</Text>
        <Text style={[styles.score, { color: tint }]}>
          {score == null ? (pending ? "···" : "—") : pct(score)}
        </Text>
      </View>
      <View style={styles.track}>
        <Animated.View style={[styles.fill, { width, backgroundColor: tint }]} />
      </View>
      <View style={styles.metaRow}>
        <Text style={[styles.band, { color: tint }]}>{band ?? (pending ? "scoring" : "standby")}</Text>
        {score != null && <Text style={styles.threshold}>intervene ≥ 58%</Text>}
      </View>
      {rationale ? <Text style={styles.rationale}>{rationale}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  head: { flexDirection: "row", alignItems: "flex-end", justifyContent: "space-between" },
  label: { color: color.muted, fontSize: 13, fontWeight: font.medium },
  score: { fontSize: 34, fontWeight: font.black, letterSpacing: -1, fontVariant: ["tabular-nums"] },
  track: {
    height: 6,
    backgroundColor: color.raised,
    borderRadius: 3,
    overflow: "hidden",
    marginTop: 8,
  },
  fill: { height: "100%", borderRadius: 3 },
  metaRow: { flexDirection: "row", justifyContent: "space-between", marginTop: 8 },
  band: { fontSize: 11, fontWeight: font.semi, textTransform: "uppercase", letterSpacing: 1.5 },
  threshold: { color: color.faint, fontSize: 11, fontVariant: ["tabular-nums"] },
  rationale: { color: color.muted, fontSize: 13, lineHeight: 19, marginTop: 12 },
});
