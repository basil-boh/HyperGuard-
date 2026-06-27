"use client";

import { BAND_VAR, pct } from "@/lib/format";
import type { RiskAssessment } from "@/lib/types";

// A 240° radial instrument. The arc charges to the score, tinted by band; while the
// Twin is still scoring it shows a sweeping scanline instead of a number.
const SIZE = 168;
const R = 64;
const CX = SIZE / 2;
const VISIBLE = 240 / 360; // fraction of the circle drawn
const LEN = 2 * Math.PI * R;

export function RiskMeter({
  risk,
  analysing,
}: {
  risk: RiskAssessment | null;
  analysing: boolean;
}) {
  const score = risk?.score ?? 0;
  const color = risk ? BAND_VAR[risk.band] : "var(--faint)";
  const track = LEN * VISIBLE;
  const value = LEN * VISIBLE * score;

  return (
    <div className="flex flex-col items-center">
      <div className="relative" style={{ width: SIZE, height: SIZE }}>
        <svg width={SIZE} height={SIZE} viewBox={`0 0 ${SIZE} ${SIZE}`}>
          <g transform={`rotate(150 ${CX} ${CX})`}>
            <circle
              cx={CX}
              cy={CX}
              r={R}
              fill="none"
              stroke="var(--raised)"
              strokeWidth={10}
              strokeLinecap="round"
              strokeDasharray={`${track} ${LEN}`}
            />
            <circle
              cx={CX}
              cy={CX}
              r={R}
              fill="none"
              stroke={color}
              strokeWidth={10}
              strokeLinecap="round"
              strokeDasharray={`${value} ${LEN}`}
              style={{
                transition: "stroke-dasharray 900ms cubic-bezier(0.22,1,0.36,1), stroke 400ms",
                filter: `drop-shadow(0 0 10px ${color})`,
              }}
            />
          </g>
          {/* tick marks every 20% */}
          {[0, 0.2, 0.4, 0.6, 0.8, 1].map((t) => {
            const a = (150 + t * 240) * (Math.PI / 180);
            const x1 = CX + Math.cos(a) * (R + 9);
            const y1 = CX + Math.sin(a) * (R + 9);
            const x2 = CX + Math.cos(a) * (R + 13);
            const y2 = CX + Math.sin(a) * (R + 13);
            return (
              <line key={t} x1={x1} y1={y1} x2={x2} y2={y2} stroke="var(--faint)" strokeWidth={1} />
            );
          })}
        </svg>

        <div className="absolute inset-0 flex flex-col items-center justify-center">
          {analysing && !risk ? (
            <span className="readout animate-flicker text-signal">scoring</span>
          ) : (
            <>
              <span
                className="numeric text-4xl font-semibold leading-none"
                style={{ color }}
              >
                {risk ? pct(score) : "—"}
              </span>
              <span
                className="readout mt-2"
                style={{ color: risk ? color : "var(--faint)" }}
              >
                {risk ? risk.band : "standby"}
              </span>
            </>
          )}
        </div>

        {analysing && !risk && (
          <div className="scanline rounded-full" style={{ borderRadius: "50%" }} />
        )}
      </div>

      <p className="mt-3 text-center text-[0.78rem] leading-relaxed text-muted">
        {risk ? risk.rationale : "Awaiting transaction. The Digital Twin scores against the customer's behavioural baseline."}
      </p>
    </div>
  );
}
