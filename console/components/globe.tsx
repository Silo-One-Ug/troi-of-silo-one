"use client";
// The agent's presence: a gold wireframe globe with an orbit ring. Slow when idle, quick when working, pulsing when speaking.
import { Canvas, useFrame } from "@react-three/fiber";
import { useRef } from "react";
import * as THREE from "three";
export type AgentState = "idle" | "listening" | "thinking" | "working" | "speaking";

function Globe({ state }: { state: AgentState }) {
  const g = useRef<THREE.Group>(null); const ring = useRef<THREE.Mesh>(null); const t = useRef(0);
  useFrame((_, dt) => {
    t.current += dt; const speed = state === "thinking" || state === "working" ? 1.6 : state === "speaking" ? 0.9 : 0.3;
    if (g.current) { g.current.rotation.y += dt * speed; g.current.rotation.z = 23.4 * Math.PI / 180; }
    if (ring.current) { ring.current.rotation.z += dt * speed * 0.6; const s = state === "speaking" ? 1 + 0.06 * Math.sin(t.current * 8) : 1; ring.current.scale.setScalar(s); }
  });
  const gold = new THREE.Color("#d4a640");
  return (
    <group>
      <group ref={g}>
        <mesh><sphereGeometry args={[1, 24, 16]} /><meshBasicMaterial color={gold} wireframe transparent opacity={0.55} /></mesh>
        <mesh><sphereGeometry args={[0.98, 32, 32]} /><meshStandardMaterial color="#1a140a" transparent opacity={0.85} roughness={0.9} /></mesh>
      </group>
      <mesh ref={ring} rotation={[1.2, 0, 0.35]}><torusGeometry args={[1.5, 0.025, 8, 96]} /><meshStandardMaterial color={gold} emissive={gold} emissiveIntensity={0.6} metalness={0.8} roughness={0.3} /></mesh>
      <ambientLight intensity={0.6} /><pointLight position={[3, 3, 3]} intensity={12} color="#ffe2a8" />
    </group>
  );
}

export function GlobeCanvas({ state = "idle", className = "h-40 w-40" }: { state?: AgentState; className?: string }) {
  return (
    <div className={className} aria-hidden>
      <Canvas camera={{ position: [0, 0, 4.2], fov: 40 }} dpr={[1, 2]} gl={{ alpha: true, antialias: true }}><Globe state={state} /></Canvas>
    </div>
  );
}
