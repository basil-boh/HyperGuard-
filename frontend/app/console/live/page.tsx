"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Wordmark } from "@/components/brand/Wordmark";
import { ThemeToggle } from "@/components/ThemeToggle";
import { Panel } from "@/components/primitives/Panel";
import { CapabilityStrip } from "@/components/console/CapabilityStrip";
import { ClassificationCard } from "@/components/console/ClassificationCard";
import { GuardianCard } from "@/components/console/GuardianCard";
import { RelayTrack } from "@/components/console/RelayTrack";
import { RiskMeter } from "@/components/console/RiskMeter";
import { ScenarioLauncher } from "@/components/console/ScenarioLauncher";
import { SignalLedger } from "@/components/console/SignalLedger";
import { SubjectCard } from "@/components/console/SubjectCard";
import { TranscriptStream } from "@/components/console/TranscriptStream";
import { VerdictSeal } from "@/components/console/VerdictSeal";
import { fetchHealth, fetchScenarios } from "@/lib/api";
import type { Scenario } from "@/lib/types";
import { useSwarmStream } from "@/lib/useSwarmStream";

export default function LiveConsolePage() {
  const { state, link, launch } = useSwarmStream();
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [bootCaps, setBootCaps] = useState<Record<string, boolean> | null>(null);

  useEffect(() => {
    fetchScenarios().then(setScenarios).catch(() => setScenarios([]));
    fetchHealth().then((h) => setBootCaps(h.capabilities)).catch(() => {});
  }, []);

  const busy = state.phase === "arming" || state.phase === "running";
  const caps = state.capabilities ?? bootCaps;
  const callLive = state.phase === "running" && !!state.call;

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-20 flex items-center justify-between border-b border-hairline bg-void/80 px-5 py-3 backdrop-blur-md">
        <div className="flex items-center gap-6">
          <Wordmark active={busy} />
          <span className="hidden h-4 w-px bg-hairline sm:block" />
          <span className="hidden items-center gap-2 sm:flex">
            <span className="readout">live case</span>
            <span className="numeric text-[0.72rem] text-ink">{state.caseId ?? "—"}</span>
          </span>
        </div>
        <div className="flex items-center gap-5">
          <CapabilityStrip capabilities={caps} link={link} />
          <ThemeToggle />
          <Link href="/console" className="readout transition hover:text-ink">
            ← control centre
          </Link>
        </div>
      </header>

      <main className="mx-auto grid max-w-[1500px] grid-cols-1 gap-4 p-5 lg:grid-cols-12">
        <div className="flex flex-col gap-4 lg:col-span-3">
          <Panel label="Scenario queue" index="00" accent="var(--signal)">
            <ScenarioLauncher scenarios={scenarios} busy={busy} onLaunch={launch} />
          </Panel>
          <Panel label="Subject under review" index="◉">
            <SubjectCard state={state} />
          </Panel>
        </div>

        <div className="flex flex-col gap-4 lg:col-span-6">
          <Panel label="Agent relay" index="↯" accent="var(--ice)">
            <RelayTrack agents={state.agents} />
          </Panel>
          <Panel
            label="Live call transcript"
            index="02"
            accent="var(--signal)"
            right={
              state.call && (
                <span className="readout" style={{ color: state.call.live ? "var(--signal)" : "var(--faint)" }}>
                  {state.call.live ? "● telephony" : "○ simulated"}
                </span>
              )
            }
            bodyClassName="p-3"
          >
            <TranscriptStream turns={state.transcript} live={callLive} />
          </Panel>
        </div>

        <div className="flex flex-col gap-4 lg:col-span-3">
          <Panel label="Risk index" index="01" accent="var(--crimson)">
            <RiskMeter risk={state.risk} analysing={busy} />
          </Panel>
          <Panel label="Signal ledger" index="∑">
            <SignalLedger signals={state.risk?.signals ?? []} />
          </Panel>
        </div>

        <div className="lg:col-span-4">
          <Panel label="Scam classification" index="03" accent="var(--crimson)" className="h-full">
            <ClassificationCard c={state.classification} />
          </Panel>
        </div>
        <div className="lg:col-span-4">
          <Panel label="Guardian network" index="04" accent="var(--ice)" className="h-full">
            <GuardianCard alerts={state.guardianAlerts} />
          </Panel>
        </div>
        <div className="lg:col-span-4">
          <Panel label="Adjudication" index="◆" accent="var(--signal)" className="h-full">
            <VerdictSeal
              decision={state.decision}
              narrative={state.narrative}
              hasEvidence={!!state.evidence}
              pending={busy && !state.decision}
            />
          </Panel>
        </div>
      </main>
    </div>
  );
}
