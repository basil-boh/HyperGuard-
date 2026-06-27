// A custom shield mark whose interior is the swarm itself: a core node ringed by
// four satellites, the five agents. No icon library; drawn by hand.

export function Logomark({ size = 30, active = false }: { size?: number; active?: boolean }) {
  const ring = active ? "var(--signal)" : "var(--faint)";
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      role="img"
      aria-label="HyperGuard"
    >
      <path
        d="M16 1.5 L28.5 7.5 V16.5 C28.5 23.8 22.7 28.8 16 30.5 C9.3 28.8 3.5 23.8 3.5 16.5 V7.5 Z"
        stroke="var(--ink)"
        strokeWidth="1.4"
        fill="rgba(201,242,74,0.04)"
        strokeLinejoin="round"
      />
      <circle cx="16" cy="16" r="8.5" stroke={ring} strokeWidth="0.8" opacity="0.5" />
      {/* four satellite agents */}
      {[
        [16, 7.5],
        [24.5, 16],
        [16, 24.5],
        [7.5, 16],
      ].map(([cx, cy], i) => (
        <circle key={i} cx={cx} cy={cy} r="1.4" fill={ring} />
      ))}
      {/* core */}
      <circle
        cx="16"
        cy="16"
        r="3"
        fill="var(--signal)"
        className={active ? "animate-breathe" : ""}
      />
    </svg>
  );
}
