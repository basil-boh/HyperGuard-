"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Wordmark } from "@/components/brand/Wordmark";
import { EvidenceDossier } from "@/components/console/EvidenceDossier";
import type { EvidencePackage } from "@/lib/types";

export default function RecoveryPage() {
  const [pkg, setPkg] = useState<EvidencePackage | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    try {
      const raw = sessionStorage.getItem("hg:evidence");
      if (raw) setPkg(JSON.parse(raw));
    } catch {
      /* ignore */
    }
    setReady(true);
  }, []);

  return (
    <div className="min-h-screen">
      <header className="flex items-center justify-between border-b border-hairline px-5 py-3 print:hidden">
        <Wordmark />
        <Link href="/console" className="readout transition hover:text-ink">
          ← console
        </Link>
      </header>

      <main className="px-5 py-10">
        {!ready ? null : pkg ? (
          <EvidenceDossier pkg={pkg} />
        ) : (
          <div className="mx-auto max-w-md rounded-lg border border-hairline bg-surface px-6 py-12 text-center">
            <p className="readout text-faint">No dossier loaded</p>
            <p className="mt-3 text-[0.9rem] text-muted">
              Run an intervention that ends in a block or recovery case, then return here to view the
              generated evidence package.
            </p>
            <Link
              href="/console"
              className="mt-6 inline-block rounded-md bg-signal px-4 py-2.5 font-display text-[0.84rem] font-semibold text-onsignal transition hover:brightness-110"
            >
              Go to console
            </Link>
          </div>
        )}
      </main>
    </div>
  );
}
