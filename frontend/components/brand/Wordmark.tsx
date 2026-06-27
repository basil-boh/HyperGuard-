import Link from "next/link";
import { Logomark } from "./Logomark";

export function Wordmark({ active = false }: { active?: boolean }) {
  return (
    <Link href="/" className="group inline-flex items-center gap-3">
      <Logomark active={active} />
      <span className="leading-none">
        <span className="block font-display text-[15px] font-semibold tracking-tight text-ink">
          Hyper<span className="text-signal">Guard</span>
        </span>
        <span className="readout mt-1 block text-[0.55rem]">Intervention Swarm</span>
      </span>
    </Link>
  );
}
