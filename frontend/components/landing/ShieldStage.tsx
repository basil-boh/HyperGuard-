"use client";

import dynamic from "next/dynamic";

const Hero3D = dynamic(() => import("./Hero3D"), { ssr: false });

// The HyperGuard shield silhouette, taken straight from the logomark.
// CLIP is the same path normalised to a 0..1 bounding box for `clip-path`.
const OUTLINE =
  "M16 1.5 L28.5 7.5 L28.5 16.5 C28.5 23.8 22.7 28.8 16 30.5 C9.3 28.8 3.5 23.8 3.5 16.5 L3.5 7.5 Z";
const CLIP =
  "M0.5 0.047 L0.891 0.234 L0.891 0.516 C0.891 0.744 0.709 0.9 0.5 0.953 C0.291 0.9 0.109 0.744 0.109 0.516 L0.109 0.234 Z";

export function ShieldStage() {
  return (
    <div className="hero-stage relative mx-auto aspect-square w-full max-w-[440px]">
      {/* ambient bloom behind the shield */}
      <div
        aria-hidden
        className="absolute inset-[10%] -z-10 blur-3xl"
        style={{
          background: "radial-gradient(circle at 50% 46%, rgba(201,242,74,0.20), transparent 60%)",
        }}
      />

      {/* clip-path definition (normalised shield) */}
      <svg width="0" height="0" className="absolute" aria-hidden>
        <defs>
          <clipPath id="hg-shield" clipPathUnits="objectBoundingBox">
            <path d={CLIP} />
          </clipPath>
        </defs>
      </svg>

      {/* the 3D field, clipped into the shield */}
      <div className="absolute inset-0" style={{ clipPath: "url(#hg-shield)" }}>
        <div
          aria-hidden
          className="absolute inset-0"
          style={{
            background:
              "radial-gradient(circle at 50% 38%, rgba(20,24,34,0.55), rgba(7,8,12,0.92))",
          }}
        />
        <Hero3D />
      </div>

      {/* glowing shield edge, single + inner line, echoing the logomark */}
      <svg
        viewBox="0 0 32 32"
        preserveAspectRatio="none"
        className="pointer-events-none absolute inset-0 h-full w-full"
        style={{ filter: "drop-shadow(0 0 6px rgba(201,242,74,0.5))" }}
      >
        <path
          d={OUTLINE}
          fill="none"
          stroke="var(--signal)"
          strokeWidth="0.3"
          strokeLinejoin="round"
          opacity="0.92"
        />
        <path
          d={OUTLINE}
          fill="none"
          stroke="var(--ice)"
          strokeWidth="0.12"
          strokeLinejoin="round"
          opacity="0.4"
          transform="translate(16 16) scale(0.87) translate(-16 -16)"
        />
        {/* corner ticks at the shield shoulders, like the logo's satellite nodes */}
        {[
          [16, 4.6],
          [25.6, 16],
          [16, 27],
          [6.4, 16],
        ].map(([cx, cy], i) => (
          <circle key={i} cx={cx} cy={cy} r="0.5" fill="var(--ice)" opacity="0.7" />
        ))}
      </svg>
    </div>
  );
}
