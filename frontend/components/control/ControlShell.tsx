"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Wordmark } from "@/components/brand/Wordmark";
import { ThemeToggle } from "@/components/ThemeToggle";
import { cn } from "@/lib/format";

export function ControlShell({
  children,
  crumbs,
}: {
  children: React.ReactNode;
  crumbs?: { label: string; href?: string }[];
}) {
  const pathname = usePathname();
  const onOverview = pathname === "/console";

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-20 flex items-center justify-between gap-4 border-b border-hairline bg-void/85 px-5 py-3 backdrop-blur-md">
        <div className="flex items-center gap-5">
          <Wordmark />
          <span className="hidden h-4 w-px bg-hairline sm:block" />
          <span className="readout hidden sm:inline">Operations Control Centre</span>
        </div>
        <nav className="flex items-center gap-4">
          <Link
            href="/console"
            className={cn("readout transition hover:text-ink", onOverview ? "text-signal" : "text-faint")}
          >
            Overview
          </Link>
          <Link href="/console/live" className="readout text-faint transition hover:text-ink">
            Live interception
          </Link>
          <ThemeToggle />
        </nav>
      </header>

      {crumbs && crumbs.length > 0 && (
        <div className="mx-auto flex max-w-[1400px] items-center gap-2 px-5 pt-5 sm:px-7">
          {crumbs.map((c, i) => (
            <span key={i} className="flex items-center gap-2">
              {i > 0 && <span className="text-faint">/</span>}
              {c.href ? (
                <Link href={c.href} className="readout transition hover:text-ink">
                  {c.label}
                </Link>
              ) : (
                <span className="readout text-ink">{c.label}</span>
              )}
            </span>
          ))}
        </div>
      )}

      <main className="mx-auto max-w-[1400px] p-5 sm:p-7">{children}</main>
    </div>
  );
}
