import React, { useEffect, useRef, useState } from "react";
import {
  Animated,
  Dimensions,
  Keyboard,
  KeyboardEvent,
  Platform,
  ScrollView,
  StyleProp,
  StyleSheet,
  View,
  ViewStyle,
} from "react-native";
import { SafeAreaView, useSafeAreaInsets } from "react-native-safe-area-context";
import { color } from "@/lib/theme";

/**
 * Screen shell for anything with a text field and a submit button.
 *
 * We deliberately do *not* use `KeyboardAvoidingView`. On RN 0.74 its `padding`
 * behaviour sizes itself from the first `keyboardWillShow` frame and never re-applies
 * when the frame changes afterwards — which is exactly what the QuickType suggestion
 * bar does on an alphabetic keyboard. The result was a submit button covered by
 * roughly the height of that bar on any form whose first field wasn't numeric.
 *
 * Instead we read the keyboard's own geometry, which is authoritative in every case:
 * `window height - endCoordinates.screenY` is the real overlap, whether the keyboard
 * is alphabetic, numeric, split, floating, or accompanied by a hardware keyboard bar.
 *
 * The safe area claims only the top edge — the bottom home-indicator inset belongs to
 * the footer, which drops it while the keyboard is up (the indicator is hidden behind
 * the keyboard anyway). Applying it via SafeAreaView instead would sit *outside* this
 * padding and double-count.
 */
export function FormScaffold({
  header,
  footer,
  children,
  contentStyle,
}: {
  /** Title bar. Stays put while the content scrolls. */
  header?: React.ReactNode;
  /** Sticky submit area. Omit to let the button scroll with the content. */
  footer?: React.ReactNode;
  children: React.ReactNode;
  contentStyle?: StyleProp<ViewStyle>;
}) {
  const insets = useSafeAreaInsets();
  const { padding, visible } = useKeyboardOverlap();

  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <Animated.View style={{ flex: 1, paddingBottom: padding }}>
        {header}
        <ScrollView
          contentContainerStyle={[styles.content, contentStyle]}
          keyboardShouldPersistTaps="handled"
          keyboardDismissMode="on-drag"
          showsVerticalScrollIndicator={false}
        >
          {children}
        </ScrollView>
        {footer ? (
          <View style={[styles.footer, { paddingBottom: visible ? 16 : 16 + insets.bottom }]}>
            {footer}
          </View>
        ) : (
          <View style={{ height: visible ? 0 : insets.bottom }} />
        )}
      </Animated.View>
    </SafeAreaView>
  );
}

/**
 * How much of the screen the keyboard currently covers, as an animated value that
 * tracks the system animation.
 *
 * Android is left at 0 on purpose: `adjustResize` (the Expo default) already shrinks
 * the window, so adding our own padding would double it.
 */
function useKeyboardOverlap(): { padding: Animated.Value; visible: boolean } {
  const padding = useRef(new Animated.Value(0)).current;
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (Platform.OS !== "ios") {
      const show = Keyboard.addListener("keyboardDidShow", () => setVisible(true));
      const hide = Keyboard.addListener("keyboardDidHide", () => setVisible(false));
      return () => {
        show.remove();
        hide.remove();
      };
    }

    const onFrame = (event: KeyboardEvent) => {
      // screenY is the keyboard's top edge; anything below it is covered. This stays
      // correct when the suggestion bar appears or the keyboard type changes.
      const overlap = Math.max(
        0,
        Dimensions.get("window").height - event.endCoordinates.screenY,
      );
      setVisible(overlap > 0);
      Animated.timing(padding, {
        toValue: overlap,
        duration: event.duration || 250,
        useNativeDriver: false, // padding isn't a transform
      }).start();
    };

    // willChangeFrame covers show, hide, and every mid-flight resize in one event.
    const change = Keyboard.addListener("keyboardWillChangeFrame", onFrame);
    const hide = Keyboard.addListener("keyboardWillHide", (event) => {
      setVisible(false);
      Animated.timing(padding, {
        toValue: 0,
        duration: event.duration || 250,
        useNativeDriver: false,
      }).start();
    });
    return () => {
      change.remove();
      hide.remove();
    };
  }, [padding]);

  return { padding, visible };
}

/** True while the software keyboard is on screen. */
export function useKeyboardVisible(): boolean {
  return useKeyboardOverlap().visible;
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: color.void },
  content: { padding: 20, flexGrow: 1 },
  footer: {
    paddingHorizontal: 20,
    paddingTop: 16,
    borderTopWidth: 1,
    borderTopColor: color.hairline,
    backgroundColor: color.void,
  },
});
