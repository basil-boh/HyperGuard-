import { cn } from "@/lib/format";

// A signal lamp. `pulse` adds the breathing animation for live/engaged states.
export function StatusDot({
  color = "var(--faint)",
  pulse = false,
  size = 7,
}: {
  color?: string;
  pulse?: boolean;
  size?: number;
}) {
  return (
    <span className="relative inline-flex" style={{ width: size, height: size }}>
      {pulse && (
        <span
          className="absolute inset-0 rounded-full animate-breathe"
          style={{ background: color, opacity: 0.5 }}
        />
      )}
      <span
        className={cn("relative inline-block rounded-full")}
        style={{ width: size, height: size, background: color, boxShadow: `0 0 8px ${color}` }}
      />
    </span>
  );
}
