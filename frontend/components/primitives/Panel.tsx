import { cn } from "@/lib/format";

// Minimal section chrome shared across the console: a tracked-out kicker label, an
// optional index tag, and a framed body. Interiors are authored per-module so no
// two panels read the same.
export function Panel({
  label,
  index,
  accent,
  right,
  className,
  bodyClassName,
  children,
}: {
  label: string;
  index?: string;
  accent?: string;
  right?: React.ReactNode;
  className?: string;
  bodyClassName?: string;
  children: React.ReactNode;
}) {
  return (
    <section
      className={cn(
        "relative rounded-md border border-hairline bg-surface/70 shadow-panel backdrop-blur-sm",
        className,
      )}
    >
      <header className="flex items-center justify-between border-b border-hairline px-4 py-2.5">
        <div className="flex items-center gap-2.5">
          {index && (
            <span
              className="numeric text-[0.6rem] font-semibold"
              style={{ color: accent ?? "var(--faint)" }}
            >
              {index}
            </span>
          )}
          <span className="readout">{label}</span>
        </div>
        {right}
      </header>
      <div className={cn("p-4", bodyClassName)}>{children}</div>
    </section>
  );
}
