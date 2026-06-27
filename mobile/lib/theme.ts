// HyperGuard Wallet design tokens, the console's "interdiction" palette, tuned
// for a calm consumer banking surface with the same signal-lime identity.

export const color = {
  void: "#07080c",
  abyss: "#0c0e15",
  surface: "#12141d",
  raised: "#1a1d28",
  hairline: "rgba(141,152,178,0.16)",
  ink: "#eceef4",
  muted: "#9aa1b4",
  faint: "#626a80",

  signal: "#c9f24a",
  signalSoft: "rgba(201,242,74,0.14)",
  ice: "#79d6e6",
  amber: "#ffc24b",
  ember: "#ff7a45",
  crimson: "#ff4d5e",
};

export const bandColor: Record<string, string> = {
  minimal: color.signal,
  elevated: color.amber,
  high: color.ember,
  critical: color.crimson,
};

export const radius = { sm: 10, md: 16, lg: 22, pill: 999 };

export const space = (n: number) => n * 4;

export const font = {
  // System fonts keep the bundle light; weights carry the hierarchy.
  black: "800" as const,
  bold: "700" as const,
  semi: "600" as const,
  medium: "500" as const,
  regular: "400" as const,
};
