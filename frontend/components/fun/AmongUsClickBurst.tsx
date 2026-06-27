"use client";

import { useEffect, useRef, useState } from "react";

// On every click, a crewmate pops out of the cursor, hops + spins in a random
// crewmate colour (hue-rotated off the single PNG), then floats up and fades.
// Pure overlay: pointer-events-none, so it never blocks the click underneath.

type Burst = { id: number; x: number; y: number; hue: number; flip: number };

export function AmongUsClickBurst() {
  const [bursts, setBursts] = useState<Burst[]>([]);
  const nextId = useRef(0);

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    const onPointerDown = (e: PointerEvent) => {
      if (e.button !== 0) return; // primary click only
      const id = nextId.current++;
      setBursts((b) => [
        ...b,
        {
          id,
          x: e.clientX,
          y: e.clientY,
          hue: Math.floor(Math.random() * 360),
          flip: Math.random() < 0.5 ? 1 : -1,
        },
      ]);
    };

    window.addEventListener("pointerdown", onPointerDown);
    return () => window.removeEventListener("pointerdown", onPointerDown);
  }, []);

  const remove = (id: number) => setBursts((b) => b.filter((x) => x.id !== id));

  return (
    <div className="pointer-events-none fixed inset-0 z-[9999]" aria-hidden>
      {bursts.map((b) => (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          key={b.id}
          src="/cursor-amongus.png"
          alt=""
          className="amongus-burst"
          onAnimationEnd={() => remove(b.id)}
          style={
            {
              left: b.x,
              top: b.y,
              filter: `hue-rotate(${b.hue}deg) saturate(1.7) drop-shadow(0 2px 5px rgba(0,0,0,0.45))`,
              "--flip": b.flip,
            } as React.CSSProperties
          }
        />
      ))}
    </div>
  );
}
