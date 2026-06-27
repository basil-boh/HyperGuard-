"use client";

import { useRef } from "react";
import Link from "next/link";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useGSAP } from "@gsap/react";
import { Wordmark } from "@/components/brand/Wordmark";
import { ShieldStage } from "@/components/landing/ShieldStage";
import { ScrollStory } from "@/components/landing/ScrollStory";
import { InterceptionFeed } from "@/components/landing/InterceptionFeed";

type Stat = {
  display: string;
  label: string;
  to?: number;
  to2?: number;
  prefix?: string;
  suffix?: string;
  sep?: string;
};

const STATS: Stat[] = [
  { to: 94, suffix: "%", display: "94%", label: "of fraud losses come from payments the victim authorised themselves" },
  { prefix: "<", to: 60, suffix: "s", display: "<60s", label: "from “I'll send it” to “sent”, HyperGuard's window to intervene" },
  { to: 5, suffix: "", display: "5", label: "AI agents working in concert on every high-risk transfer" },
  { to: 24, to2: 7, sep: "/", display: "24/7", label: "always-on interception, with an audit trail for every decision" },
];

if (typeof window !== "undefined") {
  gsap.registerPlugin(ScrollTrigger, useGSAP);
  // Don't let a slow frame (e.g. the WebGL hero on weak GPUs) stretch GSAP's clock
  // and leave entrance tweens unfinished — advance on real elapsed time instead.
  gsap.ticker.lagSmoothing(0);
}

const AGENTS = [
  { n: "01", name: "Digital Twin", role: "Behavioural risk scoring", body: "Learns each customer's baseline, amounts, payees, hours, velocity, and scores every transfer with an explainable anomaly read. It decides whether the moment is worth interrupting." },
  { n: "02", name: "Voice Negotiator", role: "Real-time intervention", body: "Places an outbound call the instant risk spikes, and holds a calm, contextual conversation to understand who asked for the money and why." },
  { n: "03", name: "Educator", role: "Scam classification", body: "Reads the customer's replies for social-engineering fingerprints, names the scam narrative, and feeds the right warning back into the live call." },
  { n: "04", name: "Guardian", role: "Family escalation", body: "On confirmed coercion, pulls a pre-authorised trusted contact into the loop with full context, a second pair of eyes for vulnerable customers." },
  { n: "05", name: "Recovery Coordinator", role: "Evidence & recovery", body: "When fraud gets through, assembles an investigator-ready package, timeline, transcript, risk rationale, and a recommended-action checklist for the bank and police." },
];

const FLOW = ["Transaction", "Risk score", "Voice call", "Classify", "Escalate", "Verdict", "Recover"];

// ── Before/after ("the gap") section ───────────────────────────────────────
const LEGACY_ROWS: { label: string; on: boolean }[] = [
  { label: "Flags a suspicious transaction", on: true },
  { label: "Files a report after the fact", on: true },
  { label: "No real-time intervention", on: false },
  { label: "No family escalation", on: false },
  { label: "No recovery orchestration", on: false },
];

const LIVE_ROWS = [
  "Live voice negotiation in the moment",
  "Scam education during the call",
  "Trusted-contact escalation",
  "Post-incident evidence & recovery",
  "Explainable, audited decisions",
];

function IcoCheck() {
  return (
    <svg className="gap-ico" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path d="M3.5 8.6l2.7 2.7L12.5 5" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
function IcoCross() {
  return (
    <svg className="gap-ico" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path d="M4.6 4.6l6.8 6.8M11.4 4.6l-6.8 6.8" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
    </svg>
  );
}
function IcoDot() {
  return (
    <svg className="gap-ico" viewBox="0 0 16 16" aria-hidden="true">
      <circle cx="8" cy="8" r="2.1" fill="currentColor" />
    </svg>
  );
}
function ShieldNode() {
  return (
    <svg className="gap-node-ico" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M12 2.6l7 2.6v5.9c0 4.4-3 8-7 10.3-4-2.3-7-5.9-7-10.3V5.2l7-2.6z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
      <path d="M9 12l2 2 4.2-4.6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export default function Landing() {
  const root = useRef<HTMLDivElement>(null);

  useGSAP(
    () => {
      const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      if (reduce) return;

      // ── Hero entrance ────────────────────────────────────────────────────────
      // NB: never animate `scale` (or any size-changing transform) on .hero-stage —
      // it holds the WebGL canvas, and React-Three-Fiber measures size with a
      // ResizeObserver that ignores transforms, so a scaled mount renders the scene
      // off-centre until the next resize. Fade + translate only.
      // Independent tweens (not a chained timeline) so a single stall can never
      // leave another element stuck in its hidden "from" state.
      gsap.from(".hero-stage", { opacity: 0, duration: 1.1, ease: "power2.out" });
      gsap.from(".hero-kicker", { y: 16, opacity: 0, duration: 0.6, delay: 0.15, ease: "power3.out" });
      gsap.from(".hero-line > span", { yPercent: 115, duration: 0.85, stagger: 0.1, delay: 0.3, ease: "power3.out" });
      gsap.from(".hero-copy", { y: 20, opacity: 0, duration: 0.7, delay: 0.9, ease: "power3.out" });
      gsap.from(".hero-cta", { y: 16, opacity: 0, duration: 0.6, stagger: 0.1, delay: 1.1, ease: "power3.out" });

      // gentle float on the shield, translateY only (safe for the WebGL canvas).
      gsap.to(".hero-stage", { y: -14, duration: 3.4, ease: "sine.inOut", repeat: -1, yoyo: true, delay: 1.3 });

      // ── Scale callout ────────────────────────────────────────────────────────
      gsap.from(".scale-reveal", { scrollTrigger: { trigger: ".scale", start: "top 80%" }, y: 24, opacity: 0, duration: 0.8, stagger: 0.14 });

      // ── The gap: columns slide in ────────────────────────────────────────────
      // The gap: passive settles, the wire ignites from the node, live caps charge in.
      const gapTl = gsap.timeline({ scrollTrigger: { trigger: ".gap", start: "top 75%" } });
      gapTl
        .from(".gap-passive", { x: -24, opacity: 0, duration: 0.7, ease: "power3.out" })
        .from(".gap-wire", { scaleY: 0, opacity: 0, duration: 0.55, ease: "power2.out" }, "-=0.15")
        .from(".gap-node", { scale: 0, opacity: 0, duration: 0.5, ease: "back.out(2)" }, "-=0.2")
        .from(".gap-live", { x: 24, opacity: 0, duration: 0.7, ease: "power3.out" }, "-=0.4")
        .from(".gap-live .gap-cap", { x: 14, opacity: 0, duration: 0.5, stagger: 0.08, ease: "power3.out" }, "-=0.35");

      // ── The layer: copy + integration nodes ──────────────────────────────────
      gsap.from(".layer-copy", { scrollTrigger: { trigger: ".layer", start: "top 78%" }, y: 24, opacity: 0, duration: 0.8 });
      gsap.from(".layer-node", { scrollTrigger: { trigger: ".layer", start: "top 66%" }, y: 16, opacity: 0, duration: 0.5, stagger: 0.1, ease: "back.out(1.5)" });

      // ── Swarm roster: staggered reveal ───────────────────────────────────────
      gsap.from(".agent-row", { scrollTrigger: { trigger: ".swarm", start: "top 70%" }, y: 26, opacity: 0, duration: 0.7, stagger: 0.12 });
      gsap.from(".agent-num", { scrollTrigger: { trigger: ".swarm", start: "top 70%" }, scale: 0.6, opacity: 0, duration: 0.6, stagger: 0.12, ease: "back.out(2)" });

      // ── Pipeline chips: pop in ───────────────────────────────────────────────
      gsap.from(".flow-chip", { scrollTrigger: { trigger: ".flow", start: "top 82%" }, y: 14, opacity: 0, duration: 0.5, stagger: 0.07, ease: "back.out(1.6)" });

      // ── CTA ──────────────────────────────────────────────────────────────────
      gsap.from(".cta-block", { scrollTrigger: { trigger: ".cta-block", start: "top 85%" }, scale: 0.94, opacity: 0, duration: 0.7 });

      // ── Top scroll-progress bar ──────────────────────────────────────────────
      gsap.to(".scroll-progress", {
        scaleX: 1,
        ease: "none",
        scrollTrigger: { trigger: root.current, start: "top top", end: "bottom bottom", scrub: 0.3 },
      });

      // ── Stats reveal + count-up ──────────────────────────────────────────────
      gsap.from(".stat", { scrollTrigger: { trigger: ".stats", start: "top 82%" }, y: 26, opacity: 0, duration: 0.7, stagger: 0.12, ease: "power3.out" });
      // One shared tween drives every metric off the same progress value, so all
      // four start and land on the same frame regardless of magnitude (5, 24/7,
      // 94 all finish together). Linear ease keeps each one ticking up to the end.
      const statNums = gsap.utils.toArray<HTMLElement>(".stat-num");
      const counter = { p: 0 };
      const renderStats = () => {
        statNums.forEach((el) => {
          const to = parseFloat(el.dataset.to || "");
          if (isNaN(to)) return;
          const to2 = el.dataset.to2;
          if (to2 !== undefined) {
            const sep = el.dataset.sep || "/";
            el.textContent =
              Math.round(counter.p * to) + sep + Math.round(counter.p * parseFloat(to2));
          } else {
            el.textContent =
              (el.dataset.prefix || "") + Math.round(counter.p * to) + (el.dataset.suffix || "");
          }
        });
      };
      gsap.to(counter, {
        p: 1,
        duration: 1.8,
        ease: "none",
        scrollTrigger: { trigger: ".stats", start: "top 82%" },
        onUpdate: renderStats,
        onComplete: renderStats,
      });

      // ── Pipeline: a pulse travels through the stages ─────────────────────────
      const pills = gsap.utils.toArray<HTMLElement>(".flow-pill");
      if (pills.length) {
        gsap
          .timeline({ repeat: -1, repeatDelay: 0.9, scrollTrigger: { trigger: ".flow", start: "top 80%" } })
          .to(pills, { borderColor: "var(--signal)", color: "var(--ink)", boxShadow: "0 0 16px -5px var(--signal)", duration: 0.22, stagger: 0.16 })
          .to(pills, { borderColor: "var(--hairline)", color: "var(--muted)", boxShadow: "none", duration: 0.22, stagger: 0.16 }, ">0.15");
      }
    },
    { scope: root },
  );

  return (
    <div ref={root} className="relative min-h-screen overflow-x-clip">
      {/* scroll progress */}
      <div
        className="scroll-progress fixed left-0 top-0 z-50 h-[2px] w-full bg-signal"
        style={{ boxShadow: "0 0 8px var(--signal)" }}
        aria-hidden
      />
      {/* film grain asset overlay */}
      <div
        aria-hidden
        className="pointer-events-none fixed inset-0 z-[1] opacity-[0.05] mix-blend-overlay"
        style={{ backgroundImage: "url(/grain.svg)", backgroundSize: "160px" }}
      />

      {/* Nav */}
      <header className="relative z-10 mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
        <Wordmark />
        <nav className="flex items-center gap-4">
          <a href="#swarm" className="readout hidden transition hover:text-ink sm:inline">
            the swarm
          </a>
          <Link
            href="/console"
            className="rounded-md bg-signal px-4 py-2 font-display text-[0.82rem] font-semibold text-onsignal transition hover:brightness-110"
          >
            Launch console →
          </Link>
        </nav>
      </header>

      {/* Hero */}
      <section className="relative z-10 mx-auto grid max-w-6xl items-center gap-8 px-6 pb-24 pt-8 lg:grid-cols-[1.1fr_0.9fr] lg:pt-14">
        <div>
          <div className="hero-kicker mb-6 inline-flex items-center gap-2.5 rounded-full border border-signal/45 bg-signal/10 py-1.5 pl-3 pr-4 shadow-signal">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-breathe rounded-full bg-signal opacity-70" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-signal" />
            </span>
            <span className="font-mono text-[0.74rem] font-semibold uppercase tracking-[0.16em] text-signal">
              Agentic Payment Protection Layer
            </span>
          </div>
          <h1 className="mt-5 font-display text-[2.5rem] font-bold leading-[1.07] tracking-tight text-ink sm:text-[3.5rem]">
            <span className="hero-line block overflow-hidden">
              <span className="block">Detection</span>
            </span>
            <span className="hero-line block overflow-hidden">
              <span className="block">
                tells you <span className="text-faint">after</span>.
              </span>
            </span>
            <span className="hero-line mt-5 block overflow-hidden sm:mt-7">
              <span className="block">HyperGuard</span>
            </span>
            <span className="hero-line block overflow-hidden">
              <span className="block">
                intervenes <span className="shimmer-text">during</span>.
              </span>
            </span>
          </h1>
          <p className="hero-copy mt-6 max-w-xl text-[1.02rem] leading-relaxed text-muted">
            Scams don't break the bank's defences. They convince the customer to wire the money
            themselves. HyperGuard is a five-agent swarm that catches a victim mid-scam, calls
            them, talks them out of it, loops in their family, and, if it's too late, builds the
            evidence to get the money back.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-3">
            <Link
              href="/console"
              className="hero-cta rounded-md bg-signal px-5 py-3 font-display text-[0.9rem] font-semibold text-onsignal transition hover:scale-[1.03] hover:brightness-110"
            >
              Open the console
            </Link>
            <a
              href="#swarm"
              className="hero-cta rounded-md border border-hairline px-5 py-3 font-display text-[0.9rem] font-medium text-ink transition hover:border-ink/40"
            >
              Meet the agents
            </a>
          </div>
        </div>

        {/* Shield-shaped 3D stage */}
        <ShieldStage />
      </section>

      {/* Stats */}
      <section className="stats relative z-10 mx-auto max-w-6xl px-6 py-16">
        <div className="grid grid-cols-2 gap-x-8 gap-y-10 sm:grid-cols-4">
          {STATS.map((s) => (
            <div key={s.label} className="stat">
              <div
                className="stat-num font-display text-4xl font-bold tracking-tight text-ink sm:text-5xl"
                data-to={s.to ?? ""}
                data-prefix={s.prefix ?? ""}
                data-suffix={s.suffix ?? ""}
                data-to2={s.to2 ?? undefined}
                data-sep={s.sep ?? undefined}
              >
                {s.display}
              </div>
              <p className="mt-3 text-[0.86rem] leading-snug text-muted">{s.label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Live interception feed */}
      <InterceptionFeed />

      {/* Scale argument, why it has to be agentic */}
      <section className="scale relative z-10 mx-auto max-w-5xl px-6 py-20">
        <p className="scale-reveal readout text-signal">Why it has to be agentic</p>
        <p className="scale-reveal mt-5 font-display text-2xl font-medium leading-snug tracking-tight text-ink sm:text-[2rem]">
          A bank clears <span className="text-signal">millions of transfers a day</span> with only a
          handful of fraud officers. No human team can step into every high-risk moment in time. An
          agentic layer can be in <span className="text-signal">every one of them at once</span>.
        </p>
      </section>

      {/* The gap — passive (inert) vs HyperGuard (live), split by a live wire */}
      <section className="gap relative z-10 border-y border-hairline bg-abyss/40">
        <div className="relative mx-auto grid max-w-6xl items-stretch gap-6 px-6 py-12 md:grid-cols-[1fr_auto_1fr] md:gap-3 md:py-16">

          {/* Passive / archived */}
          <article className="gap-passive relative rounded-xl border border-hairline p-7">
            <header className="flex items-center gap-2.5">
              <span className="gap-dot gap-dot--dead" aria-hidden="true" />
              <span className="readout text-faint">Passive · after the fact</span>
            </header>
            <h3 className="mt-4 font-display text-xl text-muted">Existing shields</h3>
            <p className="mt-1 text-sm text-faint">Detect &amp; report</p>
            <ul className="mt-6 flex flex-col gap-3 text-[0.92rem]">
              {LEGACY_ROWS.map((r) => (
                <li key={r.label} className={`gap-row ${r.on ? "gap-row--has" : "gap-row--miss"}`}>
                  {r.on ? <IcoDot /> : <IcoCross />}
                  <span>{r.label}</span>
                </li>
              ))}
            </ul>
          </article>

          {/* The live wire */}
          <div className="gap-seam relative hidden md:flex" aria-hidden="true">
            <span className="gap-wire" />
            <span className="gap-node">
              <ShieldNode />
            </span>
          </div>

          {/* Live / intervening */}
          <article className="gap-live relative rounded-xl border p-7">
            <header className="flex items-center gap-2.5">
              <span className="gap-dot gap-dot--live" aria-hidden="true" />
              <span className="readout text-signal">Live · intervening now</span>
            </header>
            <h3 className="mt-4 font-display text-xl text-ink">HyperGuard</h3>
            <p className="mt-1 text-sm text-muted">Intervene, educate, recover</p>
            <ul className="mt-6 flex flex-col gap-3 text-[0.92rem] text-ink">
              {LIVE_ROWS.map((label) => (
                <li key={label} className="gap-cap">
                  <IcoCheck />
                  <span>{label}</span>
                </li>
              ))}
            </ul>
          </article>
        </div>
      </section>

      {/* The layer, positioning as drop-in infrastructure */}
      <section className="layer relative z-10 mx-auto max-w-6xl px-6 py-20">
        <div className="layer-copy max-w-3xl">
          <p className="readout text-signal">A layer, not a rip-and-replace</p>
          <h2 className="mt-4 font-display text-3xl font-semibold leading-tight tracking-tight text-ink sm:text-[2.4rem]">
            An agentic layer between intent and settlement
          </h2>
          <p className="mt-5 text-[1.02rem] leading-relaxed text-muted">
            HyperGuard wraps any outbound payment in a real-time agent intervention, sitting{" "}
            <span className="text-ink">alongside your existing fraud engine, not instead of it</span>.
            One API call on a high-risk transfer and the swarm takes over: score, call, educate,
            escalate, decide. For banks and payment providers it closes the one gap rules and ML
            can't, the socially-engineered customer who authorises the transfer themselves.
          </p>
        </div>

        {/* Integration diagram */}
        <div className="mt-12 flex flex-col items-stretch gap-3 sm:flex-row sm:items-center">
          <LayerNode label="Bank / PSP" sub="payment request" />
          <Arrow />
          <div className="layer-node relative flex-1 rounded-xl border border-signal/50 bg-signal/[0.06] p-5 text-center shadow-signal">
            <span className="readout text-signal">HyperGuard layer</span>
            <p className="mt-1.5 font-display text-base font-semibold text-ink">
              Agentic intervention
            </p>
            <p className="mt-1 text-[0.78rem] text-muted">5-agent swarm · approve / block</p>
          </div>
          <Arrow />
          <LayerNode label="Payment rails" sub="settle or hold" />
        </div>

        {/* Integration facts */}
        <div className="mt-8 flex flex-wrap gap-2.5">
          {[
            "REST + WebSocket API",
            "Sits beside your fraud stack",
            "Explainable, audited decisions",
            "Deploys in days",
          ].map((f) => (
            <span
              key={f}
              className="layer-node rounded-md border border-hairline bg-surface px-3.5 py-2 text-[0.8rem] text-muted"
            >
              {f}
            </span>
          ))}
        </div>
      </section>

      {/* The swarm */}
      <section id="swarm" className="swarm relative z-10 mx-auto max-w-6xl px-6 py-20">
        <div className="flex items-end justify-between">
          <h2 className="font-display text-3xl font-semibold tracking-tight text-ink">
            Five agents, one interception
          </h2>
          <span className="readout hidden sm:inline">multi-agent · langgraph</span>
        </div>
        <div className="mt-10 flex flex-col">
          {AGENTS.map((a) => (
            <article
              key={a.n}
              className="agent-row group grid gap-4 border-t border-hairline py-7 transition-colors hover:bg-surface/40 sm:grid-cols-[auto_1fr_2fr] sm:items-baseline sm:gap-8"
            >
              <span className="agent-num numeric text-2xl font-semibold text-faint transition-colors group-hover:text-signal">
                {a.n}
              </span>
              <div>
                <h3 className="font-display text-lg font-semibold text-ink">{a.name}</h3>
                <p className="readout mt-1 text-signal">{a.role}</p>
              </div>
              <p className="text-[0.94rem] leading-relaxed text-muted">{a.body}</p>
            </article>
          ))}
        </div>
      </section>

      {/* Scroll story, the interception, illustrated */}
      <ScrollStory />

      {/* The flow */}
      <section className="flow relative z-10 border-t border-hairline bg-abyss/40 py-16">
        <div className="mx-auto max-w-6xl px-6">
          <p className="readout">Interception pipeline</p>
          <div className="mt-6 flex flex-wrap items-center gap-2">
            {FLOW.map((step, i) => (
              <div key={step} className="flow-chip flex items-center gap-2">
                <span className="flow-pill rounded-md border border-hairline bg-surface px-3 py-2 font-mono text-[0.74rem] text-muted">
                  {step}
                </span>
                {i < FLOW.length - 1 && <span className="text-faint">→</span>}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="relative z-10 mx-auto max-w-6xl px-6 py-20 text-center">
        <div className="cta-block">
          <h2 className="mx-auto max-w-2xl font-display text-3xl font-semibold tracking-tight text-ink">
            Put an agent in the room when it matters most.
          </h2>
          <Link
            href="/console"
            className="mt-8 inline-block rounded-md bg-signal px-6 py-3.5 font-display text-[0.95rem] font-semibold text-onsignal transition hover:scale-[1.03] hover:brightness-110"
          >
            Launch the console →
          </Link>
        </div>
      </section>

      <footer className="relative z-10 border-t border-hairline">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-3 px-6 py-8 text-center sm:flex-row sm:text-left">
          <Wordmark />
          <p className="text-[0.72rem] text-faint">
            Hackathon prototype · not connected to live banking rails.
          </p>
        </div>
      </footer>
    </div>
  );
}

function LayerNode({ label, sub }: { label: string; sub: string }) {
  return (
    <div className="layer-node flex-1 rounded-xl border border-hairline bg-abyss/60 p-5 text-center">
      <span className="readout">{label}</span>
      <p className="mt-1.5 text-[0.82rem] text-muted">{sub}</p>
    </div>
  );
}

function Arrow() {
  return (
    <span className="layer-node flex shrink-0 items-center justify-center text-faint sm:px-1">
      <span className="hidden sm:inline">→</span>
      <span className="sm:hidden">↓</span>
    </span>
  );
}
