"use client";
// The ground of the console: low Earth orbit. A photographic Earth (NASA Blue Marble day, city lights at night,
// relief, oceans that catch the sun) filling the lower frame like the view from a station, a thin scattering
// atmosphere on the limb, the real night sky behind, the sun's glare, and a stainless-steel spacecraft holding
// station in front of the planet whose engines light only while the agent works. Restrained on purpose.
import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useFrame, useLoader, useThree } from "@react-three/fiber";
import { Bloom, EffectComposer, Noise, Vignette } from "@react-three/postprocessing";
import gsap from "gsap";
import * as THREE from "three";

export type SpaceState = "off" | "idle" | "listening" | "thinking" | "working" | "speaking";
const SUN = new THREE.Vector3(-0.55, 0.42, -0.72).normalize();       // behind and above: a lit crescent and a bright limb
const R = 10;                                                           // the Earth is big; we are close to it

const earthVert = `varying vec2 vUv; varying vec3 vN; varying vec3 vW;
void main(){ vUv = uv; vN = normalize(mat3(modelMatrix) * normal); vec4 w = modelMatrix * vec4(position,1.); vW = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }`;
// the samplers carry a Map suffix: a local called "day" once shadowed the day texture, the shader failed to compile
// and only the blue atmosphere shell drew. Ends in three's tone mapping and sRGB output so it matches the rest.
const earthFrag = `uniform sampler2D dayMap; uniform sampler2D nightMap; uniform sampler2D waterMap; uniform sampler2D bumpMap; uniform sampler2D cloudMap;
uniform vec3 sun; uniform float cloudShift;
varying vec2 vUv; varying vec3 vN; varying vec3 vW;
void main(){
  vec3 g = normalize(vN); vec3 n = g;
  vec2 e = vec2(1.0/2048.0, 1.0/1024.0); float h = texture2D(bumpMap, vUv).r;                      // relief from the topography
  float hx = texture2D(bumpMap, vUv + vec2(e.x,0.)).r - h; float hy = texture2D(bumpMap, vUv + vec2(0.,e.y)).r - h;
  vec3 t = normalize(cross(vec3(0.,1.,0.), g)); vec3 b = cross(g, t); n = normalize(g - (t * hx + b * hy) * 2.2);
  float d = dot(n, sun); float dg = dot(g, sun); float lit = smoothstep(-0.10, 0.25, dg);
  vec3 V = normalize(cameraPosition - vW);
  vec3 albedo = texture2D(dayMap, vUv).rgb;
  float land = 1.0 - texture2D(waterMap, vUv).r;
  vec3 dayC = albedo * (0.02 + 1.15 * max(d, 0.));
  vec3 H = normalize(sun + V); float nh = max(dot(g, H), 0.);
  dayC += (1.0 - land) * (vec3(1., .93, .82) * (pow(nh, 160.) * 2.2 + pow(nh, 18.) * .07)) * smoothstep(0., .2, dg);  // sun glint on the oceans
  vec2 cuv = vUv - vec2(cloudShift, 0.); float cl = texture2D(cloudMap, cuv).r;
  float sh = texture2D(cloudMap, cuv + vec2(sun.x, -sun.y) * .0015).r; dayC *= 1.0 - sh * .45;              // clouds cast shadows
  vec3 nightC = pow(texture2D(nightMap, vUv).rgb, vec3(1.6)) * vec3(1.9, 1.35, .85) * 1.6 * (1.0 - cl * .8);
  vec3 col = mix(nightC, dayC, lit);
  col += vec3(1., .38, .12) * exp(-pow(dg * 6., 2.)) * .05;                                             // dusk along the terminator
  float fres = pow(1. - max(dot(g, V), 0.), 3.);
  col = mix(col, vec3(.32, .58, 1.) * (0.04 + lit * .9), fres * .7);                                       // air thickens towards the limb
  gl_FragColor = vec4(col, 1.);
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
}`;
const cloudFrag = `uniform sampler2D cloudMap; uniform vec3 sun; varying vec2 vUv; varying vec3 vN; varying vec3 vW;
void main(){ vec3 g = normalize(vN); float dg = dot(g, sun); float lit = smoothstep(-0.12, 0.3, dg); float c = texture2D(cloudMap, vUv).r;
  vec3 V = normalize(cameraPosition - vW); float edge = 1. - pow(1. - max(dot(g, V), 0.), 6.);
  vec3 col = mix(vec3(1., .55, .35), vec3(1.), smoothstep(0., .35, dg)) * (0.015 + 1.05 * max(dg, 0.));
  gl_FragColor = vec4(col, smoothstep(.08, .9, c) * (0.12 + lit * .88) * edge);
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
}`;
const atmoVert = `varying vec3 vN; varying vec3 vW; void main(){ vN = normalize(mat3(modelMatrix) * normal); vec4 w = modelMatrix * vec4(position,1.); vW = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }`;
const atmoFrag = `uniform vec3 sun; uniform vec3 tint; uniform float strength; varying vec3 vN; varying vec3 vW;
void main(){ vec3 n = normalize(vN); vec3 V = normalize(cameraPosition - vW);
  float rim = pow(smoothstep(0.0, 0.19, -dot(n, V)), 2.2);                                                    // back faces: densest at the ground, gone at the shell's edge
  float lit = smoothstep(-0.3, 0.5, dot(n, sun)); float fwd = pow(max(dot(-V, sun), 0.), 8.) * 1.4;           // forward scattering towards the sun
  vec3 c = mix(tint, vec3(1., .6, .4), smoothstep(.25, -.15, dot(n, sun)) * lit * .6);                      // warmer where the air meets the night
  gl_FragColor = vec4(c * (lit + fwd), clamp(rim * (lit * 0.85 + fwd) * strength, 0., 1.)); }`;

const CLOUD_SPEED = 0.0016;                                                                           // clouds drift a little faster than the ground
function Earth({ state }: { state: SpaceState }) {
  const [day, night, water, bump, clouds] = useLoader(THREE.TextureLoader, ["/space/earth-blue-marble.jpg", "/space/earth-night.jpg", "/space/earth-water.png", "/space/earth-topology.png", "/space/earth-clouds-4k.jpg"]);
  const { gl } = useThree();
  useMemo(() => { [day, night].forEach(t => { t.colorSpace = THREE.SRGBColorSpace; }); [day, night, water, bump, clouds].forEach(t => { t.anisotropy = gl.capabilities.getMaxAnisotropy(); t.wrapS = THREE.RepeatWrapping; t.needsUpdate = true; }); }, [day, night, water, bump, clouds, gl]);
  const spin = useRef<THREE.Group>(null); const cloudSpin = useRef<THREE.Mesh>(null); const atmo = useRef<THREE.ShaderMaterial>(null);
  const uniforms = useMemo(() => ({ dayMap: { value: day }, nightMap: { value: night }, waterMap: { value: water }, bumpMap: { value: bump }, cloudMap: { value: clouds }, sun: { value: SUN.clone() }, cloudShift: { value: 0 } }), [day, night, water, bump, clouds]);
  const cU = useMemo(() => ({ cloudMap: { value: clouds }, sun: { value: SUN.clone() } }), [clouds]);
  const aU = useMemo(() => ({ sun: { value: SUN }, tint: { value: new THREE.Color("#4f9dff") }, strength: { value: 1 } }), []);
  useFrame((_, dt) => {
    if (spin.current) spin.current.rotation.y += dt * 0.006;                               // orbital drift, slow
    if (cloudSpin.current) { cloudSpin.current.rotation.y += dt * CLOUD_SPEED; uniforms.cloudShift.value = cloudSpin.current.rotation.y / (Math.PI * 2); }
    if (atmo.current) { const c = state === "thinking" || state === "working" ? "#7fb6ff" : state === "speaking" ? "#8f9cff" : "#4f9dff"; (atmo.current.uniforms.tint.value as THREE.Color).lerp(new THREE.Color(c), Math.min(1, dt)); }
  });
  return (
    <group position={[2.5, -11.4, -4]} rotation={[0.35, 0, -0.18]}>
      <group ref={spin} rotation={[0, 2.1, 0]}>
        <mesh><sphereGeometry args={[R, 192, 192]} /><shaderMaterial vertexShader={earthVert} fragmentShader={earthFrag} uniforms={uniforms} /></mesh>
        <mesh ref={cloudSpin} scale={1.004}><sphereGeometry args={[R, 160, 160]} /><shaderMaterial vertexShader={earthVert} fragmentShader={cloudFrag} uniforms={cU} transparent depthWrite={false} /></mesh>
      </group>
      <mesh scale={1.022}><sphereGeometry args={[R, 128, 128]} /><shaderMaterial ref={atmo} vertexShader={atmoVert} fragmentShader={atmoFrag} uniforms={aU} transparent blending={THREE.AdditiveBlending} side={THREE.BackSide} depthWrite={false} /></mesh>
    </group>
  );
}

// the sky: the Milky Way photographed all round (ESO, via Solar System Scope), kept dim as the eye sees it next to a
// sunlit planet, with a field of sharp stars in front so the points stay crisp at any resolution
function Sky() {
  const tex = useLoader(THREE.TextureLoader, "/space/milky-way-8k.jpg");
  useMemo(() => { tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 8; }, [tex]);
  return <mesh rotation={[0.6, 0, 0.9]}><sphereGeometry args={[400, 96, 96]} /><meshBasicMaterial map={tex} side={THREE.BackSide} color="#8d96a8" toneMapped={false} depthWrite={false} /></mesh>;
}
const starVert = `attribute float size; attribute vec3 tint; attribute float phase; uniform float time; uniform float px; varying vec3 vT; varying float vA;
void main(){ vT = tint; vA = 0.75 + 0.25 * sin(time * (0.6 + phase) + phase * 40.); gl_PointSize = size * px; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.); }`;
const starFrag = `varying vec3 vT; varying float vA; void main(){ vec2 c = gl_PointCoord - .5; float r = length(c); float a = smoothstep(.5, 0., r); a = a * a; gl_FragColor = vec4(vT * vA, a * vA); }`;
function Stars({ count = 5200 }: { count?: number }) {
  const mat = useRef<THREE.ShaderMaterial>(null); const { gl } = useThree();
  const geo = useMemo(() => {
    const pos = new Float32Array(count * 3), size = new Float32Array(count), tint = new Float32Array(count * 3), phase = new Float32Array(count);
    const temps = [[.62, .72, 1], [.8, .86, 1], [1, 1, 1], [1, .95, .84], [1, .82, .62]];
    for (let i = 0; i < count; i++) {
      const u = Math.random() * 2 - 1, th = Math.random() * Math.PI * 2, r = 300, q = Math.sqrt(1 - u * u);
      pos.set([r * q * Math.cos(th), r * u, r * q * Math.sin(th)], i * 3);
      const m = Math.pow(Math.random(), 7); size[i] = 1.1 + m * 4.2; phase[i] = Math.random();                // most faint, a few bright
      const c = temps[Math.floor(Math.pow(Math.random(), 0.8) * temps.length)]; const k = 0.35 + m * 0.9; tint.set([c[0] * k, c[1] * k, c[2] * k], i * 3);
    }
    const g = new THREE.BufferGeometry(); g.setAttribute("position", new THREE.BufferAttribute(pos, 3)); g.setAttribute("size", new THREE.BufferAttribute(size, 1)); g.setAttribute("tint", new THREE.BufferAttribute(tint, 3)); g.setAttribute("phase", new THREE.BufferAttribute(phase, 1)); return g;
  }, [count]);
  const u = useMemo(() => ({ time: { value: 0 }, px: { value: gl.getPixelRatio() } }), [gl]);
  useFrame(({ clock }) => { u.time.value = clock.elapsedTime; u.px.value = gl.getPixelRatio(); });
  return <points geometry={geo}><shaderMaterial ref={mat} vertexShader={starVert} fragmentShader={starFrag} uniforms={u} transparent depthWrite={false} blending={THREE.AdditiveBlending} toneMapped={false} /></points>;
}

function SunGlare() {
  const tex = useMemo(() => { const c = document.createElement("canvas"); c.width = c.height = 256; const x = c.getContext("2d")!; const g = x.createRadialGradient(128, 128, 0, 128, 128, 128); g.addColorStop(0, "rgba(255,250,240,1)"); g.addColorStop(0.08, "rgba(255,240,215,.9)"); g.addColorStop(0.25, "rgba(255,210,160,.22)"); g.addColorStop(1, "rgba(0,0,0,0)"); x.fillStyle = g; x.fillRect(0, 0, 256, 256); return new THREE.CanvasTexture(c); }, []);
  return <sprite position={SUN.clone().multiplyScalar(300)} scale={[70, 70, 1]}><spriteMaterial map={tex} blending={THREE.AdditiveBlending} depthWrite={false} toneMapped={false} /></sprite>;
}

// ---- the spacecraft: a stainless-steel ship in the style of a modern orbital vehicle. Turned hull, a dark heat
// shield on its belly, four flaps, three engine bells; the bells glow and a faint plume shows only while working.
function Ship({ state }: { state: SpaceState }) {
  const root = useRef<THREE.Group>(null); const flame = useRef<THREE.Group>(null); const cur = useRef(0);
  const hull = useMemo(() => { const p: THREE.Vector2[] = []; const L = 3.2, r = 0.3; for (let i = 0; i <= 40; i++) { const y = i / 40; const rr = y < 0.78 ? r : r * Math.sqrt(Math.max(0, 1 - Math.pow((y - 0.78) / 0.22, 2))); p.push(new THREE.Vector2(Math.max(0.002, rr), y * L - L / 2)); } return new THREE.LatheGeometry(p, 96); }, []);
  const shield = useMemo(() => new THREE.CylinderGeometry(0.303, 0.303, 2.4, 96, 1, true, Math.PI * 0.62, Math.PI * 0.76), []);
  const flap = useMemo(() => { const s = new THREE.Shape(); s.moveTo(0, 0); s.lineTo(0.34, 0.05); s.lineTo(0.34, 0.42); s.lineTo(0, 0.55); s.closePath(); return new THREE.ExtrudeGeometry(s, { depth: 0.02, bevelEnabled: true, bevelSize: 0.008, bevelThickness: 0.006, bevelSegments: 3 }); }, []);
  const steel = useMemo(() => new THREE.MeshPhysicalMaterial({ color: "#c9ced6", metalness: 1, roughness: 0.32, clearcoat: 0.4, clearcoatRoughness: 0.4 }), []);
  const tile = useMemo(() => new THREE.MeshStandardMaterial({ color: "#1b1d22", metalness: 0.1, roughness: 0.85 }), []);
  const want = state === "thinking" || state === "working" ? 1 : state === "speaking" ? 0.45 : 0;
  useFrame(({ clock }, dt) => {
    cur.current += (want - cur.current) * Math.min(1, dt * 1.8);
    const t = clock.elapsedTime;
    if (root.current) { root.current.position.y = 0.55 + Math.sin(t * 0.25) * 0.06; root.current.rotation.z = -0.52 + Math.sin(t * 0.18) * 0.02; root.current.rotation.y = 0.9 + Math.sin(t * 0.12) * 0.04; }
    if (flame.current) { flame.current.visible = cur.current > 0.02; flame.current.children.forEach((m: any, i) => { const f = 0.7 + cur.current * 0.9 + Math.sin(t * 43 + i) * 0.04; m.scale.set(1, f, 1); m.material.opacity = cur.current * 0.55; }); }
  });
  const bells = [[0, 0], [0.13, 0.075], [-0.13, 0.075]];
  return (
    <group ref={root} position={[-1.2, 0.55, 0.4]} rotation={[0.18, 0.9, -0.52]} scale={0.62}>
      <mesh geometry={hull} material={steel} />
      <mesh geometry={shield} material={tile} position={[0, -0.25, 0]} />
      {[[0.3, 0.95, 0], [-0.3, 0.95, Math.PI], [0.3, -1.1, 0], [-0.3, -1.1, Math.PI]].map(([x, y, ry], i) => <mesh key={i} geometry={flap} material={steel} position={[x as number, y as number, -0.01]} rotation={[0, ry as number, 0]} scale={i < 2 ? 0.7 : 1} />)}
      {bells.map(([x, z], i) => <mesh key={i} position={[x, -1.66, z]}><cylinderGeometry args={[0.06, 0.1, 0.16, 40, 1, true]} /><meshStandardMaterial color="#2a2c31" metalness={0.9} roughness={0.4} emissive="#ff8a3d" emissiveIntensity={0} side={THREE.DoubleSide} /></mesh>)}
      <group ref={flame}>{bells.map(([x, z], i) => <mesh key={i} position={[x, -2.05, z]}><coneGeometry args={[0.085, 0.65, 32, 1, true]} /><meshBasicMaterial color="#9fc6ff" transparent opacity={0} blending={THREE.AdditiveBlending} depthWrite={false} side={THREE.DoubleSide} toneMapped={false} /></mesh>)}</group>
    </group>
  );
}

// [camera x, y, z, look-at x, y]: each page frames the planet into the part of the window it leaves open
const VIEWS: Record<string, [number, number, number, number, number]> = {
  default: [0, 0, 8, 0, -0.4], conversation: [0.3, 0.1, 8, -2.4, -0.3], library: [0, 1.6, 10.5, 0, 0.6], modes: [0.3, 0, 8, -2.2, -0.5],
  routines: [0.3, 0, 8, -2.2, -0.5], reports: [0.3, 0, 8, -2.4, -0.4], approvals: [0.3, 0, 8, -2.2, -0.4],
  // the welcome's story: a pull-back reveal, then the camera travels a little with each scene
  "w-intro": [0, 2.2, 15.5, 0, 0.9], "w-listen": [0.3, 0.1, 8, -2.4, -0.3], "w-see": [-1.4, 0.7, 7.4, 1.1, -0.5], "w-work": [1.1, -0.1, 6.6, -1.3, -0.7],
  "w-remember": [0, 1.6, 10.5, 0, 0.6], "w-ask": [0.3, 0, 8, -2.2, -0.5], "w-setup": [0.6, 0.4, 9.2, -2.8, -0.2] };
function Rig({ view }: { view: string }) {
  const { camera } = useThree(); const look = useRef({ x: 0, y: 0 }); const target = useRef(new THREE.Vector3());
  useEffect(() => { const [x, y, z, lx, ly] = VIEWS[view] || VIEWS.default; gsap.to(camera.position, { x, y, z, duration: 2.6, ease: "power2.inOut" }); gsap.to(look.current, { x: lx, y: ly, duration: 2.6, ease: "power2.inOut" }); }, [view, camera]);
  useFrame(({ pointer }) => { target.current.set(look.current.x + pointer.x * 0.12, look.current.y + pointer.y * 0.08, 0); camera.lookAt(target.current); });
  return null;
}

function Ready({ onReady }: { onReady: () => void }) { useEffect(() => { onReady(); }, [onReady]); return null; }

export function Space({ state = "idle", view = "default", active = true }: { state?: SpaceState; view?: string; active?: boolean }) {
  const [ready, setReady] = useState(false); const done = useCallback(() => setReady(true), []);
  return (
    <div className="pointer-events-none fixed inset-0 -z-10 bg-black transition-opacity duration-700 ease-out" style={{ opacity: ready && active ? 1 : 0 }}>{/* fades in once the planet is loaded: never a half-built frame */}
      <Canvas frameloop={active ? "always" : "never"} camera={{ position: [0.3, 0.1, 8], fov: 38, near: 0.1, far: 1000 }} dpr={[1, 2]} gl={{ antialias: true, toneMapping: THREE.ACESFilmicToneMapping, toneMappingExposure: 1.0, outputColorSpace: THREE.SRGBColorSpace }}>
        <color attach="background" args={["#000"]} />
        <ambientLight intensity={0.03} />
        <directionalLight position={SUN.clone().multiplyScalar(50)} intensity={3.2} color="#fff6ea" />
        <hemisphereLight args={["#1a2a44", "#0a1a33", 0.25]} />
        <Suspense fallback={null}><Sky /><Earth state={state} /><Ready onReady={done} /></Suspense>
        <Stars />
        <SunGlare />
        <Ship state={state} />
        <Rig view={view} />
        <EffectComposer multisampling={4}><Bloom intensity={0.45} luminanceThreshold={0.85} luminanceSmoothing={0.2} mipmapBlur /><Noise opacity={0.02} /><Vignette eskil={false} offset={0.25} darkness={0.75} /></EffectComposer>
      </Canvas>
    </div>
  );
}
