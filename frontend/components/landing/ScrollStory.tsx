"use client";

import { useRef } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useGSAP } from "@gsap/react";

if (typeof window !== "undefined") {
  gsap.registerPlugin(ScrollTrigger, useGSAP);
}

const SHIELD = "M16 1.5 L28.5 7.5 L28.5 16.5 C28.5 23.8 22.7 28.8 16 30.5 C9.3 28.8 3.5 23.8 3.5 16.5 L3.5 7.5 Z";

// ── Reusable bits ────────────────────────────────────────────────────────────
function Waves({ x, y, color, dir = 1 }: { x: number; y: number; color: string; dir?: number }) {
  return (
    <>
      {[11, 19, 27].map((r, i) => (
        <path
          key={r}
          className={`wave-arc ${i === 1 ? "w2" : i === 2 ? "w3" : ""}`}
          d={`M ${x} ${y - r} A ${r} ${r} 0 0 ${dir > 0 ? 1 : 0} ${x} ${y + r}`}
          fill="none"
          stroke={color}
          strokeWidth={2}
          strokeLinecap="round"
        />
      ))}
    </>
  );
}

function Person({ x, y, color }: { x: number; y: number; color: string }) {
  return (
    <g stroke={color} strokeWidth={2} fill="none" strokeLinecap="round">
      <circle className="draw" cx={x} cy={y} r={9} pathLength={1} />
      <path className="draw" d={`M ${x - 16} ${y + 30} a 16 18 0 0 1 32 0`} pathLength={1} />
    </g>
  );
}

// ── Scene 1: the scam call ───────────────────────────────────────────────────
function SceneCall() {
  return (
    <svg viewBox="0 0 240 190" className="h-auto w-full">
      <circle className="ring-pulse" cx={78} cy={112} r={52} fill="none" stroke="var(--crimson)" strokeWidth={1} opacity={0.25} />
      {/* phone */}
      <rect className="draw" x={52} y={66} width={52} height={92} rx={12} fill="var(--abyss)" stroke="var(--ink)" strokeWidth={2} pathLength={1} />
      <rect x={60} y={78} width={36} height={60} rx={3} fill="var(--surface)" stroke="var(--faint)" strokeWidth={1} />
      <circle cx={78} cy={96} r={9} fill="none" stroke="var(--crimson)" strokeWidth={2} />
      <text x={78} y={100} textAnchor="middle" fontSize={11} fontWeight={700} fill="var(--crimson)">?</text>
      <line x1={66} y1={116} x2={90} y2={116} stroke="var(--faint)" strokeWidth={2} strokeLinecap="round" />
      <line x1={66} y1={124} x2={84} y2={124} stroke="var(--faint)" strokeWidth={2} strokeLinecap="round" />
      {/* scam speech bubble */}
      <g>
        <rect className="draw" x={120} y={42} width={104} height={52} rx={12} fill="rgba(255,77,94,0.08)" stroke="var(--crimson)" strokeWidth={1.5} pathLength={1} />
        <path d="M120 78 l-12 10 l14 0 z" fill="rgba(255,77,94,0.08)" stroke="var(--crimson)" strokeWidth={1.5} />
        <line x1={134} y1={58} x2={210} y2={58} stroke="var(--crimson)" strokeWidth={2} strokeLinecap="round" opacity={0.8} />
        <line x1={134} y1={68} x2={196} y2={68} stroke="var(--ember)" strokeWidth={2} strokeLinecap="round" opacity={0.7} />
        <line x1={134} y1={78} x2={206} y2={78} stroke="var(--crimson)" strokeWidth={2} strokeLinecap="round" opacity={0.55} />
      </g>
      <g transform="translate(108 112)">
        <Waves x={0} y={0} color="var(--crimson)" />
      </g>
      {/* warning */}
      <g className="blink" transform="translate(40 150)">
        <path d="M0 12 L8 -4 L16 12 Z" fill="none" stroke="var(--crimson)" strokeWidth={2} strokeLinejoin="round" />
        <line x1={8} y1={2} x2={8} y2={7} stroke="var(--crimson)" strokeWidth={2} strokeLinecap="round" />
        <circle cx={8} cy={10} r={1} fill="var(--crimson)" />
      </g>
    </svg>
  );
}

// ── Scene 2: the money is leaving ─────────────────────────────────────────────
function SceneTransfer() {
  return (
    <svg viewBox="0 0 240 190" className="h-auto w-full">
      {/* pulsing danger ring on the destination */}
      <circle className="ring-pulse" cx={206} cy={95} r={32} fill="none" stroke="var(--crimson)" strokeWidth={1} opacity={0.28} />
      {/* flowing route */}
      <path className="flow-dash" d="M52 95 H188" stroke="var(--ember)" strokeWidth={2} strokeDasharray="3 6" fill="none" opacity={0.85} />
      <path d="M176 86 l14 9 l-14 9" fill="none" stroke="var(--amber)" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
      {/* destination, shady account */}
      <circle className="draw" cx={206} cy={95} r={24} fill="rgba(255,77,94,0.06)" stroke="var(--crimson)" strokeWidth={2} pathLength={1} />
      <circle cx={206} cy={89} r={6} fill="none" stroke="var(--crimson)" strokeWidth={2} />
      <path d="M194 110 a12 10 0 0 1 24 0" fill="none" stroke="var(--crimson)" strokeWidth={2} />
      {/* money packets continuously draining toward the account */}
      {[0, 1.1].map((begin, i) => (
        <circle key={i} r={3.4} fill="var(--amber)">
          <animateMotion dur="2.2s" begin={`${begin}s`} repeatCount="indefinite" path="M74 95 H182" />
          <animate attributeName="opacity" values="0;1;1;0" dur="2.2s" begin={`${begin}s`} repeatCount="indefinite" />
        </circle>
      ))}
      {/* banknote (slides in once on scroll) */}
      <g className="money">
        <rect x={26} y={78} width={52} height={34} rx={6} fill="var(--surface)" stroke="var(--ice)" strokeWidth={2} />
        <circle cx={52} cy={95} r={8} fill="none" stroke="var(--ice)" strokeWidth={2} />
        <text x={52} y={99} textAnchor="middle" fontSize={10} fontWeight={700} fill="var(--ice)">$</text>
        <line x1={33} y1={84} x2={40} y2={84} stroke="var(--faint)" strokeWidth={2} strokeLinecap="round" />
        <line x1={64} y1={106} x2={71} y2={106} stroke="var(--faint)" strokeWidth={2} strokeLinecap="round" />
      </g>
      <text x={206} y={140} textAnchor="middle" fontSize={9} fill="var(--faint)" letterSpacing={1}>UNKNOWN</text>
    </svg>
  );
}

// ── Scene 3: the Digital Twin spikes ──────────────────────────────────────────
function SceneRisk() {
  return (
    <svg viewBox="0 0 240 190" className="h-auto w-full">
      <defs>
        <linearGradient id="riskGrad" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="var(--signal)" />
          <stop offset="0.5" stopColor="var(--amber)" />
          <stop offset="1" stopColor="var(--crimson)" />
        </linearGradient>
      </defs>
      <circle className="ring-pulse" cx={120} cy={150} r={96} fill="none" stroke="var(--crimson)" strokeWidth={1} opacity={0.18} />
      {/* track + value arc */}
      <path d="M44 150 A76 76 0 0 1 196 150" fill="none" stroke="var(--raised)" strokeWidth={12} strokeLinecap="round" />
      <path className="draw" d="M44 150 A76 76 0 0 1 196 150" fill="none" stroke="url(#riskGrad)" strokeWidth={12} strokeLinecap="round" pathLength={1} />
      {/* ticks */}
      {[0, 0.25, 0.5, 0.75, 1].map((t) => {
        const a = Math.PI - t * Math.PI;
        const x1 = 120 + Math.cos(a) * 64;
        const y1 = 150 - Math.sin(a) * 64;
        const x2 = 120 + Math.cos(a) * 54;
        const y2 = 150 - Math.sin(a) * 54;
        return <line key={t} x1={x1} y1={y1} x2={x2} y2={y2} stroke="var(--faint)" strokeWidth={1.5} />;
      })}
      {/* needle */}
      <g className="needle">
        <line x1={120} y1={150} x2={120} y2={88} stroke="var(--ink)" strokeWidth={3} strokeLinecap="round" />
      </g>
      <circle cx={120} cy={150} r={7} fill="var(--ink)" />
      <text x={120} y={176} textAnchor="middle" fontSize={11} fontWeight={700} fill="var(--crimson)" letterSpacing={1}>ANOMALY</text>
    </svg>
  );
}

// ── Scene 4: HyperGuard calls and talks you down ──────────────────────────────
function SceneNegotiate() {
  return (
    <svg viewBox="0 0 240 190" className="h-auto w-full">
      {/* shield */}
      <g transform="translate(28 50) scale(2.6)">
        <path className="draw" d={SHIELD} fill="rgba(201,242,74,0.06)" stroke="var(--signal)" strokeWidth={1.4} strokeLinejoin="round" pathLength={1} />
      </g>
      {/* handset glyph inside shield (clean telephone receiver) */}
      <path
        className="draw"
        transform="translate(51 75) scale(1.5)"
        d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"
        fill="none"
        stroke="var(--signal)"
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
        pathLength={1}
      />
      <g transform="translate(118 96)">
        <Waves x={0} y={0} color="var(--signal)" />
      </g>
      <Person x={196} y={86} color="var(--ice)" />
      {/* calm guidance bubble */}
      <g transform="translate(120 128)">
        <rect className="draw" x={0} y={0} width={104} height={40} rx={11} fill="rgba(201,242,74,0.07)" stroke="var(--signal)" strokeWidth={1.5} pathLength={1} />
        <path d="M18 12 l5 6 l11 -13" fill="none" stroke="var(--signal)" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
        <line x1={42} y1={14} x2={92} y2={14} stroke="var(--signal)" strokeWidth={2} strokeLinecap="round" opacity={0.7} />
        <line x1={42} y1={24} x2={80} y2={24} stroke="var(--signal)" strokeWidth={2} strokeLinecap="round" opacity={0.5} />
      </g>
    </svg>
  );
}

// ── Scene 5: blocked, family looped in ────────────────────────────────────────
function SceneBlock() {
  return (
    <svg viewBox="0 0 240 190" className="h-auto w-full">
      {/* incoming money arrow, stopped */}
      <path d="M18 96 H78" stroke="var(--crimson)" strokeWidth={2} strokeDasharray="3 6" fill="none" />
      <g className="money">
        <rect x={20} y={84} width={34} height={24} rx={5} fill="var(--surface)" stroke="var(--crimson)" strokeWidth={2} />
        <text x={37} y={100} textAnchor="middle" fontSize={9} fontWeight={700} fill="var(--crimson)">$</text>
      </g>
      {/* shield block */}
      <g className="shield-block" transform="translate(74 56) scale(2.4)">
        <path d={SHIELD} fill="rgba(201,242,74,0.1)" stroke="var(--signal)" strokeWidth={1.6} strokeLinejoin="round" />
        <path d="M11 16 l4 5 l9 -11" fill="none" stroke="var(--signal)" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" />
      </g>
      {/* family node + ping */}
      <line x1={150} y1={96} x2={206} y2={56} stroke="var(--hairline)" strokeWidth={1.5} />
      <g transform="translate(196 38)">
        <rect className="draw" x={0} y={0} width={26} height={38} rx={6} fill="var(--abyss)" stroke="var(--ice)" strokeWidth={2} pathLength={1} />
        <path d="M8 12 a5 5 0 0 1 10 0 c0 6 2 7 2 9 l-14 0 c0 -2 2 -3 2 -9z" fill="none" stroke="var(--ice)" strokeWidth={1.5} />
        <circle cx={13} cy={24} r={1.6} fill="var(--ice)" />
      </g>
      <Person x={209} y={134} color="var(--ice)" />
      <line x1={209} y1={120} x2={209} y2={80} stroke="var(--hairline)" strokeWidth={1.5} />
      {/* travelling alert pings */}
      <circle r={3} fill="var(--signal)">
        <animateMotion dur="1.9s" repeatCount="indefinite" path="M150 96 L206 56" />
      </circle>
      <circle r={2.5} fill="var(--ice)">
        <animateMotion dur="1.9s" begin="0.6s" repeatCount="indefinite" path="M209 80 L209 120" />
      </circle>
      <text x={108} y={172} textAnchor="middle" fontSize={11} fontWeight={700} fill="var(--signal)" letterSpacing={1.5}>BLOCKED</text>
    </svg>
  );
}

const SCENES = [
  { n: "01", tone: "var(--crimson)", title: "It starts with a phone call", body: "A stranger posing as the police tells the customer their account is compromised, and to move their savings to a “safe account”, urgently, in secret.", Visual: SceneCall },
  { n: "02", tone: "var(--amber)", title: "The money is about to leave", body: "Convinced and pressured, the customer authorises the transfer themselves. No firewall or password was breached, which is exactly why traditional fraud checks wave it through.", Visual: SceneTransfer },
  { n: "03", tone: "var(--crimson)", title: "The Digital Twin feels it", body: "HyperGuard scores the transfer against the customer's own history, a brand-new payee, four times their normal amount, at 2am. The risk needle swings hard into the red.", Visual: SceneRisk },
  { n: "04", tone: "var(--signal)", title: "HyperGuard calls, and talks you down", body: "An agent phones the customer mid-transfer, listens, recognises the police-impersonation script, and gently explains: no real agency ever asks you to move money to a “safe account”.", Visual: SceneNegotiate },
  { n: "05", tone: "var(--signal)", title: "It loops in family, and blocks it", body: "A trusted contact is alerted to step in, and the transfer is held. The money never leaves the account, and an evidence pack is ready to report the scammer.", Visual: SceneBlock },
];

export function ScrollStory() {
  const root = useRef<HTMLDivElement>(null);

  useGSAP(
    () => {
      const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

      gsap.fromTo(
        ".story-rail-fill",
        { scaleY: 0 },
        {
          scaleY: 1,
          ease: "none",
          transformOrigin: "top",
          scrollTrigger: { trigger: ".story-rail", start: "top 65%", end: "bottom 75%", scrub: true },
        },
      );

      gsap.utils.toArray<HTMLElement>(".story-scene").forEach((scene) => {
        const dot = scene.querySelector(".story-dot");
        gsap.to(dot, {
          backgroundColor: "var(--signal)",
          borderColor: "var(--signal)",
          boxShadow: "0 0 14px var(--signal)",
          scrollTrigger: { trigger: scene, start: "top 70%" },
        });

        if (reduce) return;
        const tl = gsap.timeline({ scrollTrigger: { trigger: scene, start: "top 72%" } });
        tl.from(scene.querySelectorAll(".reveal"), { y: 26, opacity: 0, duration: 0.7, stagger: 0.12, ease: "power3.out" });
        tl.fromTo(scene.querySelectorAll(".draw"), { strokeDashoffset: 1 }, { strokeDashoffset: 0, duration: 1, stagger: 0.05, ease: "power2.out" }, 0.1);

        const needle = scene.querySelector(".needle");
        if (needle) tl.fromTo(needle, { rotation: -84, svgOrigin: "120 150" }, { rotation: 56, duration: 1.2, ease: "power3.out" }, 0.3);
        const money = scene.querySelector(".money");
        if (money) tl.fromTo(money, { x: -44, opacity: 0 }, { x: 0, opacity: 1, duration: 1, ease: "power2.out" }, 0.3);
        const block = scene.querySelector(".shield-block");
        if (block) tl.fromTo(block, { scale: 0.4, opacity: 0, transformOrigin: "50% 50%" }, { scale: 1, opacity: 1, duration: 0.6, ease: "back.out(2)" }, 0.55);
      });
    },
    { scope: root },
  );

  return (
    <section ref={root} className="relative z-10 mx-auto max-w-5xl px-6 py-24">
      <header className="mb-16 max-w-2xl">
        <p className="readout text-signal">Watch an interception unfold</p>
        <h2 className="mt-4 font-display text-3xl font-semibold leading-tight tracking-tight text-ink sm:text-[2.4rem]">
          Sixty seconds that change the outcome
        </h2>
      </header>

      <div className="story-rail relative">
        <div className="absolute bottom-2 top-2 w-px bg-hairline" style={{ left: 7 }} />
        <div
          className="story-rail-fill absolute bottom-2 top-2 w-px bg-signal"
          style={{ left: 7, boxShadow: "0 0 10px var(--signal)" }}
        />

        <div className="flex flex-col gap-24 sm:gap-28">
          {SCENES.map((s) => (
            <div key={s.n} className="story-scene relative pl-9 sm:pl-16">
              <span
                className="story-dot absolute top-1.5 h-[15px] w-[15px] rounded-full border-2 border-faint"
                style={{ left: 0, backgroundColor: "var(--void)" }}
              />
              <div className="grid gap-8 lg:grid-cols-2 lg:items-center">
                <div className="reveal">
                  <div className="overflow-hidden rounded-2xl border border-hairline bg-surface/50 p-4">
                    <s.Visual />
                  </div>
                </div>
                <div>
                  <span className="reveal numeric block text-sm font-semibold" style={{ color: s.tone }}>
                    {s.n}
                  </span>
                  <h3 className="reveal mt-2 font-display text-xl font-semibold text-ink sm:text-2xl">
                    {s.title}
                  </h3>
                  <p className="reveal mt-3 text-[0.96rem] leading-relaxed text-muted">{s.body}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
