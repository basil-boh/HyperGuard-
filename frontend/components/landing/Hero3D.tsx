"use client";

import { useMemo, useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Icosahedron, Line } from "@react-three/drei";
import { Bloom, EffectComposer } from "@react-three/postprocessing";
import * as THREE from "three";

const SIGNAL = "#c9f24a";
const ICE = "#79d6e6";

// ── The shield core: nested wireframe icosahedra + a solid emissive heart ──────
function Core() {
  const inner = useRef<THREE.Mesh>(null);
  const outer = useRef<THREE.Mesh>(null);
  const heart = useRef<THREE.Mesh>(null);

  useFrame((s, dt) => {
    if (inner.current) {
      inner.current.rotation.y += dt * 0.22;
      inner.current.rotation.x += dt * 0.09;
    }
    if (outer.current) outer.current.rotation.y -= dt * 0.12;
    const pulse = 1 + Math.sin(s.clock.elapsedTime * 1.6) * 0.05;
    heart.current?.scale.setScalar(pulse);
  });

  return (
    <group>
      <Icosahedron ref={outer} args={[1.95, 1]}>
        <meshBasicMaterial color={ICE} wireframe transparent opacity={0.1} />
      </Icosahedron>
      <Icosahedron ref={inner} args={[1.3, 1]}>
        <meshStandardMaterial
          color={SIGNAL}
          emissive={SIGNAL}
          emissiveIntensity={1.3}
          wireframe
          roughness={0.4}
        />
      </Icosahedron>
      <Icosahedron ref={heart} args={[0.55, 0]}>
        <meshStandardMaterial color={SIGNAL} emissive={SIGNAL} emissiveIntensity={2.4} />
      </Icosahedron>
    </group>
  );
}

// ── Five agents orbiting on a tilted ring, tethered to the core ────────────────
function Swarm() {
  const g = useRef<THREE.Group>(null);
  useFrame((_, dt) => {
    if (g.current) g.current.rotation.y += dt * 0.32;
  });

  const sats = useMemo(() => {
    const R = 2.05;
    return Array.from({ length: 5 }, (_, i) => {
      const a = (i / 5) * Math.PI * 2;
      return new THREE.Vector3(Math.cos(a) * R, 0, Math.sin(a) * R);
    });
  }, []);

  const ring = useMemo(() => {
    const R = 2.05;
    return Array.from({ length: 65 }, (_, i) => {
      const a = (i / 64) * Math.PI * 2;
      return new THREE.Vector3(Math.cos(a) * R, 0, Math.sin(a) * R);
    });
  }, []);

  return (
    <group ref={g} rotation={[0.5, 0, 0]}>
      <Line points={ring} color={ICE} transparent opacity={0.12} lineWidth={1} />
      {sats.map((p, i) => (
        <group key={i}>
          <Line
            points={[new THREE.Vector3(0, 0, 0), p]}
            color={ICE}
            transparent
            opacity={0.16}
            lineWidth={1}
          />
          <mesh position={p}>
            <sphereGeometry args={[0.13, 18, 18]} />
            <meshStandardMaterial color={ICE} emissive={ICE} emissiveIntensity={2.2} />
          </mesh>
        </group>
      ))}
    </group>
  );
}

// ── A faint drifting data field ───────────────────────────────────────────────
function Field() {
  const ref = useRef<THREE.Points>(null);
  const positions = useMemo(() => {
    const N = 850;
    const arr = new Float32Array(N * 3);
    for (let i = 0; i < N; i++) {
      const r = 4 + Math.random() * 5;
      const t = Math.random() * Math.PI * 2;
      const p = Math.acos(2 * Math.random() - 1);
      arr[i * 3] = r * Math.sin(p) * Math.cos(t);
      arr[i * 3 + 1] = r * Math.sin(p) * Math.sin(t) * 0.6;
      arr[i * 3 + 2] = r * Math.cos(p);
    }
    return arr;
  }, []);

  useFrame((_, dt) => {
    if (ref.current) ref.current.rotation.y += dt * 0.015;
  });

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          args={[positions, 3]}
          count={positions.length / 3}
        />
      </bufferGeometry>
      <pointsMaterial size={0.022} color={ICE} transparent opacity={0.45} sizeAttenuation />
    </points>
  );
}

// ── Eased mouse parallax wrapper ───────────────────────────────────────────────
function Parallax({ offset, children }: { offset: number; children: React.ReactNode }) {
  const ref = useRef<THREE.Group>(null);
  useFrame((s) => {
    if (!ref.current) return;
    ref.current.rotation.y += (s.pointer.x * 0.35 - ref.current.rotation.y) * 0.04;
    ref.current.rotation.x += (-s.pointer.y * 0.25 - ref.current.rotation.x) * 0.04;
  });
  return (
    <group ref={ref} position={[offset, 0, 0]}>
      {children}
    </group>
  );
}

export default function Hero3D({ offset = 0 }: { offset?: number }) {
  return (
    <Canvas
      camera={{ position: [0, 0, 7], fov: 42 }}
      gl={{ antialias: true, alpha: true }}
      dpr={[1, 2]}
      style={{ background: "transparent" }}
    >
      <ambientLight intensity={0.5} />
      <pointLight position={[5, 5, 5]} intensity={40} color={SIGNAL} />
      <pointLight position={[-6, -3, -4]} intensity={25} color={ICE} />
      <Parallax offset={offset}>
        <Core />
        <Swarm />
        <Field />
      </Parallax>
      <EffectComposer>
        <Bloom
          intensity={0.9}
          luminanceThreshold={0.2}
          luminanceSmoothing={0.35}
          mipmapBlur
        />
      </EffectComposer>
    </Canvas>
  );
}
