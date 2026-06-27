"use client";

import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";

// The threats the swarm intercepts, sampled at random for the live feed.
const SCAMS = [
  "Investment scam",
  "Police impersonation",
  "Romance scam",
  "Job & task scam",
  "Tech-support scam",
  "Bank impersonation",
  "Crypto recovery scam",
  "Parcel / customs scam",
  "Loan-fee advance scam",
];

type Status = "intercepting" | "blocked" | "hold";
type Row = { id: number; time: string; scam: string; amount: string; status: Status };

const MAX_ROWS = 5;
const NEW_ROW_MS = 2600; // cadence of incoming interceptions
const RESOLVE_MS = 850; // how long a row sits "INTERCEPT" before the verdict flips
const SEED_COUNT = 1284; // "intercepted today" starting point

// Deterministic seed: server and client render this identical first paint, so
// there's no hydration mismatch. Live, time-stamped rows only begin after mount.
const SEED: Row[] = [
  { id: -1, time: "09:42:11", scam: "Investment scam", amount: "S$14,200", status: "blocked" },
  { id: -2, time: "09:41:58", scam: "Police impersonation", amount: "S$8,500", status: "blocked" },
  { id: -3, time: "09:41:40", scam: "Romance scam", amount: "S$3,900", status: "hold" },
  { id: -4, time: "09:41:22", scam: "Job & task scam", amount: "S$1,250", status: "blocked" },
  { id: -5, time: "09:40:55", scam: "Bank impersonation", amount: "S$22,800", status: "blocked" },
];

const pad = (n: number) => n.toString().padStart(2, "0");
const nowStamp = () => {
  const d = new Date();
  return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
};
const randAmount = () =>
  "S$" + Math.floor(800 + Math.random() * 39000).toLocaleString("en-SG");
const pick = <T,>(arr: T[]) => arr[Math.floor(Math.random() * arr.length)];

export function InterceptionFeed() {
  const reduce = useReducedMotion();
  const [rows, setRows] = useState<Row[]>(SEED);
  const [count, setCount] = useState(SEED_COUNT);
  const idRef = useRef(0);
  const timers = useRef<Set<ReturnType<typeof setTimeout>>>(new Set());

  useEffect(() => {
    const emit = () => {
      const id = ++idRef.current;
      const row: Row = {
        id,
        time: nowStamp(),
        scam: pick(SCAMS),
        amount: randAmount(),
        status: "intercepting",
      };
      setRows((prev) => [row, ...prev].slice(0, MAX_ROWS));

      // After a beat the verdict lands: mostly BLOCKED, occasionally HOLD.
      const t = setTimeout(() => {
        const verdict: Status = Math.random() < 0.18 ? "hold" : "blocked";
        setRows((prev) => prev.map((r) => (r.id === id ? { ...r, status: verdict } : r)));
        if (verdict === "blocked") setCount((c) => c + 1);
        timers.current.delete(t);
      }, RESOLVE_MS);
      timers.current.add(t);
    };

    const interval = setInterval(emit, NEW_ROW_MS);
    const snapshot = timers.current;
    return () => {
      clearInterval(interval);
      snapshot.forEach(clearTimeout);
      snapshot.clear();
    };
  }, []);

  return (
    <section className="relative z-10 mx-auto max-w-6xl px-6 py-20">
      <div className="bracketed overflow-hidden rounded-xl border border-hairline bg-abyss/60 shadow-panel backdrop-blur-sm">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-hairline px-6 py-3.5">
          <span className="readout text-faint">Live interceptions</span>
          <span className="flex items-center gap-2">
            <span className="h-1.5 w-1.5 animate-breathe rounded-full bg-crimson" />
            <span className="readout text-crimson">Rec</span>
          </span>
        </div>

        {/* Feed */}
        <div className="relative overflow-hidden">
          <AnimatePresence initial={false} mode="popLayout">
            {rows.map((r) => (
              <motion.div
                key={r.id}
                layout
                initial={reduce ? false : { opacity: 0, y: -16 }}
                animate={{ opacity: 1, y: 0 }}
                exit={reduce ? { opacity: 0 } : { opacity: 0, transition: { duration: 0.2 } }}
                transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
                className="relative flex items-center gap-4 border-b border-hairline/60 px-6 py-4 last:border-b-0"
              >
                <span className="numeric text-[0.84rem] tabular-nums text-faint">{r.time}</span>
                <span className="text-faint">◆</span>
                <span className="flex-1 truncate text-[1rem] text-ink">{r.scam}</span>
                <span className="numeric hidden text-[0.84rem] tabular-nums text-muted sm:inline">
                  {r.amount}
                </span>
                <StatusBadge status={r.status} reduce={!!reduce} />
              </motion.div>
            ))}
          </AnimatePresence>
        </div>

        {/* Footer counter */}
        <div className="flex items-center justify-between border-t border-hairline px-6 py-3.5">
          <span className="readout text-faint">Intercepted today</span>
          <span className="numeric text-base font-semibold tabular-nums text-signal">
            {count.toLocaleString("en-SG")}
          </span>
        </div>
      </div>
    </section>
  );
}

const BADGE: Record<Status, { label: string; tint: string }> = {
  intercepting: {
    label: "● Intercept",
    tint: "border-crimson/45 bg-crimson/10 text-crimson",
  },
  blocked: { label: "▸ Blocked", tint: "border-signal/45 bg-signal/10 text-signal" },
  hold: { label: "⟳ Hold", tint: "border-amber/45 bg-amber/10 text-amber" },
};

function StatusBadge({ status, reduce }: { status: Status; reduce: boolean }) {
  const { label, tint } = BADGE[status];
  return (
    <span className="flex w-[7.4rem] justify-end">
      <AnimatePresence mode="wait" initial={false}>
        <motion.span
          key={status}
          initial={reduce ? false : { opacity: 0, scale: 0.82 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={reduce ? { opacity: 0 } : { opacity: 0, scale: 0.82 }}
          transition={{ duration: 0.18 }}
          className={`inline-flex items-center justify-center rounded-sm border px-2.5 py-1.5 text-[0.62rem] uppercase tracking-[0.16em] ${tint}`}
        >
          {label}
        </motion.span>
      </AnimatePresence>
    </span>
  );
}
