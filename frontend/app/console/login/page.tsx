"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Wordmark } from "@/components/brand/Wordmark";
import { login } from "@/lib/auth";

export default function OperatorLogin() {
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!password || busy) return;
    setBusy(true);
    setErr(null);
    try {
      await login(password);
      // Return the operator to wherever the 401 bounced them from.
      const next = new URLSearchParams(window.location.search).get("next");
      router.replace(next && next.startsWith("/") ? next : "/console");
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
      setBusy(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center p-5">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex flex-col items-center gap-3">
          <Wordmark />
          <span className="readout">Operations Control Centre</span>
        </div>

        <form
          onSubmit={submit}
          className="rounded-lg border border-hairline bg-surface/40 p-6 backdrop-blur-sm"
        >
          <h1 className="font-display text-lg font-semibold tracking-tight text-ink">
            Operator sign-in
          </h1>
          <p className="mt-1 text-[0.85rem] leading-relaxed text-muted">
            Enter the operator password to open the console.
          </p>

          <label className="readout mt-5 block" htmlFor="operator-password">
            Password
          </label>
          <input
            id="operator-password"
            type="password"
            autoFocus
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-2 w-full rounded-md border border-hairline bg-void/60 px-3 py-2 text-[0.95rem] text-ink outline-none transition focus:border-signal"
          />

          {err && <p className="mt-3 text-[0.82rem] text-ember">{err}</p>}

          <button
            type="submit"
            disabled={!password || busy}
            className="mt-5 w-full rounded-md border border-signal/40 bg-signal/10 px-4 py-2 font-display text-[0.9rem] font-semibold tracking-wide text-signal transition hover:bg-signal/20 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {busy ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
