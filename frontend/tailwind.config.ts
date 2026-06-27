import type { Config } from "tailwindcss";

/**
 * HyperGuard's design language, "interdiction console".
 * A deep-obsidian operations surface, an acid-lime "shield-active" signal, and a
 * graduated amber→ember→crimson threat scale. Tokens are CSS variables so themes
 * can shift at runtime; Tailwind just names them.
 */
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        void: "var(--void)",
        abyss: "var(--abyss)",
        surface: "var(--surface)",
        raised: "var(--raised)",
        hairline: "var(--hairline)",
        ink: "var(--ink)",
        muted: "var(--muted)",
        faint: "var(--faint)",
        signal: "var(--signal)",
        "signal-dim": "var(--signal-dim)",
        onsignal: "var(--on-signal)",
        ice: "var(--ice)",
        amber: "var(--amber)",
        ember: "var(--ember)",
        crimson: "var(--crimson)",
      },
      fontFamily: {
        display: ["var(--font-display)", "sans-serif"],
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "monospace"],
      },
      letterSpacing: {
        readout: "0.22em",
      },
      boxShadow: {
        signal: "0 0 0 1px var(--signal-dim), 0 0 24px -6px var(--signal)",
        panel: "0 24px 60px -30px rgba(0,0,0,0.9)",
        inset: "inset 0 1px 0 0 rgba(255,255,255,0.04)",
      },
      keyframes: {
        sweep: {
          "0%": { transform: "translateY(-100%)" },
          "100%": { transform: "translateY(220%)" },
        },
        breathe: {
          "0%, 100%": { opacity: "1", transform: "scale(1)" },
          "50%": { opacity: "0.45", transform: "scale(0.82)" },
        },
        charge: {
          "0%": { strokeDashoffset: "1" },
          "100%": { strokeDashoffset: "0" },
        },
        rise: {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        flicker: {
          "0%, 100%": { opacity: "1" },
          "42%": { opacity: "1" },
          "44%": { opacity: "0.5" },
          "46%": { opacity: "1" },
        },
      },
      animation: {
        sweep: "sweep 2.4s linear infinite",
        breathe: "breathe 1.6s ease-in-out infinite",
        rise: "rise 0.35s ease-out both",
        flicker: "flicker 3s linear infinite",
      },
    },
  },
  plugins: [],
};

export default config;
