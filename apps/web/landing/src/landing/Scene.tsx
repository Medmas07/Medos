import { useEffect, useMemo, useRef } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";
import { BEATS, finishIntro, story } from "./story";
import { copy } from "./copy";
import {
  cardFragment,
  cardVertex,
  glowFragment,
  glowVertex,
  nodeFragment,
  nodeVertex,
  particleFragment,
  particleVertex,
  threadFragment,
  threadVertex,
} from "./shaders";

/* Colors mirror the design-system tokens (brand-950, brand-300, brand-600, brand-800, warning accent). */
export const INK = new THREE.Color("#0e3b36");
export const MINT = new THREE.Color("#a7e3d4");
const LINE = new THREE.Color("#309180");
const STRONG = new THREE.Color("#195d54");
export const CORAL = new THREE.Color("#c2462a");

const CARD_COUNT = 38;
const PARTICLE_COUNT = 2200;
const FOCUS_INDEX = 0;
const NODE_LABELS = copy.sceneNodes;

/* Intro timeline (seconds) */
const INTRO = { assemble: 1.15, hold: 0.45, release: 0.9 };

function mulberry32(seed: number) {
  return () => {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let r = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    r = (r + Math.imul(r ^ (r >>> 7), 61 | r)) ^ r;
    return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
  };
}

const smooth = (a: number, b: number, x: number) => {
  const k = Math.min(1, Math.max(0, (x - a) / (b - a)));
  return k * k * (3 - 2 * k);
};


/**
 * R3F 9 copies each uniform when `uniforms` is passed as a prop, which breaks the
 * shared-by-reference uniforms this scene mutates per frame. Owning the material
 * keeps one set of uniform objects for JS and GPU.
 */
function useShaderMaterial(vertexShader: string, fragmentShader: string, uniforms: Record<string, THREE.IUniform>, extra?: THREE.ShaderMaterialParameters) {
  const material = useMemo(
    () => new THREE.ShaderMaterial({ vertexShader, fragmentShader, uniforms, transparent: true, depthWrite: false, ...extra }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [vertexShader, fragmentShader, uniforms],
  );
  useEffect(() => () => material.dispose(), [material]);
  return material;
}

/** Ecosystem nodes (Governance, hospitals, apps, research) orbit the Hospital Node on a tilted ellipse. */
const NODES: THREE.Vector3[] = Array.from({ length: 6 }, (_, i) => {
  const a = (i / 6) * Math.PI * 2 + 0.45;
  return new THREE.Vector3(Math.cos(a) * 3.9, Math.sin(a) * 2.4, Math.sin(a * 2) * 0.7 - 0.4);
});

/* Camera rail: positions and look targets sampled with the same parameter. */
const CAM_POS = new THREE.CatmullRomCurve3([
  new THREE.Vector3(0.6, 0.5, 14),
  new THREE.Vector3(0.4, 0.7, 10.5),
  new THREE.Vector3(3.2, 1.6, 9.6),
  new THREE.Vector3(2.6, 2.4, 11.5),
]);
const CAM_LOOK = new THREE.CatmullRomCurve3([
  new THREE.Vector3(-1.4, 0, 0),
  new THREE.Vector3(-1.6, 0, 0),
  new THREE.Vector3(0.4, 0.4, 0),
  new THREE.Vector3(-0.6, 0, 0),
]);

export function Cards({ uniforms, count = CARD_COUNT }: { uniforms: Record<string, THREE.IUniform>; count?: number }) {
  const geometry = useMemo(() => {
    const rand = mulberry32(7);
    const g = new THREE.InstancedBufferGeometry();
    const plane = new THREE.PlaneGeometry(1, 1.3);
    g.index = plane.index;
    g.attributes.position = plane.attributes.position!;
    g.attributes.uv = plane.attributes.uv!;
    const scatter = new Float32Array(count * 3);
    const stack = new Float32Array(count * 3);
    const rot = new Float32Array(count * 3);
    const seed = new Float32Array(count);
    const kind = new Float32Array(count);
    for (let i = 0; i < count; i++) {
      // scattered in a wide shell, biased away from the headline on the left
      const x = (rand() - 0.3) * 15;
      const y = (rand() - 0.5) * 8.5;
      const z = -rand() * 14 + 2.5;
      scatter.set([x, y, z], i * 3);
      stack.set([(rand() - 0.5) * 0.06, (rand() - 0.5) * 0.06, (i - count / 2) * 0.016], i * 3);
      rot.set([(rand() - 0.5) * 1.4, (rand() - 0.5) * 1.6, (rand() - 0.5) * 1.2], i * 3);
      seed[i] = rand();
      kind[i] = i % 3;
    }
    g.setAttribute("aScatter", new THREE.InstancedBufferAttribute(scatter, 3));
    g.setAttribute("aStack", new THREE.InstancedBufferAttribute(stack, 3));
    g.setAttribute("aRot", new THREE.InstancedBufferAttribute(rot, 3));
    g.setAttribute("aSeed", new THREE.InstancedBufferAttribute(seed, 1));
    g.setAttribute("aKind", new THREE.InstancedBufferAttribute(kind, 1));
    g.instanceCount = count;
    return g;
  }, [count]);
  const material = useShaderMaterial(cardVertex, cardFragment, uniforms, { side: THREE.DoubleSide });

  return <mesh geometry={geometry} material={material} frustumCulled={false} renderOrder={2} />;
}

/** Particle field that assembles into the wordmark during the intro. */
function Particles({ uniforms, logoCenter }: { uniforms: Record<string, THREE.IUniform>; logoCenter: THREE.Vector3 }) {
  const geometry = useMemo(() => {
    const rand = mulberry32(11);
    const g = new THREE.BufferGeometry();
    const pos = new Float32Array(PARTICLE_COUNT * 3);
    const seed = new Float32Array(PARTICLE_COUNT);
    for (let i = 0; i < PARTICLE_COUNT; i++) {
      pos.set([(rand() - 0.5) * 26, (rand() - 0.5) * 15, -rand() * 18 + 4], i * 3);
      seed[i] = rand();
    }
    g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    g.setAttribute("aSeed", new THREE.BufferAttribute(seed, 1));
    // until the font is sampled, the "logo" target is the field itself
    g.setAttribute("aLogo", new THREE.BufferAttribute(pos.slice(), 3));
    return g;
  }, []);

  useEffect(() => {
    let cancelled = false;
    document.fonts.ready.then(() => {
      if (cancelled) return;
      const pts = sampleWordmark("medos", '600 128px "Bricolage Grotesque Variable", ui-sans-serif, system-ui, sans-serif');
      if (!pts.length) return;
      const rand = mulberry32(3);
      const logo = geometry.getAttribute("aLogo") as THREE.BufferAttribute;
      for (let i = 0; i < PARTICLE_COUNT; i++) {
        const p = pts[Math.floor(rand() * pts.length)]!;
        logo.setXYZ(i, logoCenter.x + p[0] * 4.6, logoCenter.y + p[1] * 4.6, logoCenter.z + (rand() - 0.5) * 0.15);
      }
      logo.needsUpdate = true;
    });
    return () => {
      cancelled = true;
    };
  }, [geometry, logoCenter]);

  const material = useShaderMaterial(particleVertex, particleFragment, uniforms);
  return <points geometry={geometry} material={material} frustumCulled={false} renderOrder={1} />;
}

/** Returns points in [-0.5, 0.5] x [-0.125, 0.125] sampled from rendered text. */
function sampleWordmark(word: string, font: string): [number, number][] {
  const W = 640;
  const H = 160;
  const canvas = document.createElement("canvas");
  canvas.width = W;
  canvas.height = H;
  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  if (!ctx) return [];
  ctx.fillStyle = "#000";
  ctx.font = font;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(word, W / 2, H / 2 + 6);
  const data = ctx.getImageData(0, 0, W, H).data;
  const out: [number, number][] = [];
  for (let y = 0; y < H; y += 2) {
    for (let x = 0; x < W; x += 2) {
      if (data[(y * W + x) * 4 + 3]! > 140) out.push([x / W - 0.5, (H / 2 - y) / W]);
    }
  }
  return out;
}

function Threads({ uniforms }: { uniforms: Record<string, THREE.IUniform> }) {
  const geometry = useMemo(() => {
    const parts = NODES.map((node, i) => {
      const start = new THREE.Vector3(0, 0, 0.3);
      const mid = start.clone().lerp(node, 0.5).add(new THREE.Vector3(0, 0.5, 0.9));
      const curve = new THREE.QuadraticBezierCurve3(start, mid, node);
      const tube = new THREE.TubeGeometry(curve, 48, 0.014, 5, false);
      const idx = new Float32Array(tube.attributes.position!.count).fill(i);
      tube.setAttribute("aIndex", new THREE.BufferAttribute(idx, 1));
      tube.deleteAttribute("normal");
      return tube;
    });
    return mergeGeometries(parts)!;
  }, []);

  const material = useShaderMaterial(threadVertex, threadFragment, uniforms);
  return <mesh geometry={geometry} material={material} frustumCulled={false} renderOrder={3} />;
}

function Nodes({ uniforms }: { uniforms: Record<string, THREE.IUniform> }) {
  const geometry = useMemo(() => {
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(new Float32Array(NODES.flatMap((n) => [n.x, n.y, n.z])), 3));
    g.setAttribute("aIndex", new THREE.BufferAttribute(new Float32Array(NODES.map((_, i) => i)), 1));
    return g;
  }, []);
  const material = useShaderMaterial(nodeVertex, nodeFragment, uniforms);
  return <points geometry={geometry} material={material} frustumCulled={false} renderOrder={4} />;
}

function Rig({ reduced }: { reduced: boolean }) {
  const { camera, size, gl } = useThree();
  const smoothP = useRef(reduced ? 0.86 : 0);
  const pointer = useRef(new THREE.Vector2());
  const look = useMemo(() => new THREE.Vector3(), []);
  const pos = useMemo(() => new THREE.Vector3(), []);

  useEffect(() => {
    if (reduced) return;
    const onMove = (e: PointerEvent) => {
      pointer.current.set((e.clientX / window.innerWidth) * 2 - 1, (e.clientY / window.innerHeight) * 2 - 1);
    };
    window.addEventListener("pointermove", onMove, { passive: true });
    return () => window.removeEventListener("pointermove", onMove);
  }, [reduced]);

  useFrame((_, dt) => {
    // exponential smoothing: interruptible, always starts from the current value
    const target = reduced ? 0.86 : story.progress;
    smoothP.current += (target - smoothP.current) * (1 - Math.exp(-dt * 3.2));
    const u = Math.min(1, Math.max(0, smoothP.current));
    CAM_POS.getPointAt(u, pos);
    CAM_LOOK.getPointAt(u, look);
    // shift the composition right on wide screens so the headline column stays clear
    const aspect = size.width / size.height;
    const shift = Math.min(1, Math.max(0, (aspect - 1) / 0.8));
    look.x *= shift;
    if (!reduced) {
      pos.x += pointer.current.x * 0.35;
      pos.y -= pointer.current.y * 0.22;
    }
    camera.position.copy(pos);
    camera.lookAt(look);
  });

  useEffect(() => {
    gl.domElement.setAttribute("aria-hidden", "true");
  }, [gl]);

  return null;
}

const LABEL_OFFSET = new THREE.Vector3(0, -0.42, 0);

function World({ reduced, labelRefs }: { reduced: boolean; labelRefs: React.RefObject<(HTMLDivElement | null)[]> }) {
  const { gl, invalidate, camera, size } = useThree();
  const projected = useMemo(() => new THREE.Vector3(), []);
  const introClock = useRef<number | null>(null);

  const logoCenter = useMemo(() => {
    // put the wordmark 8 units in front of the starting camera
    const start = CAM_POS.getPointAt(0);
    const dir = CAM_LOOK.getPointAt(0).clone().sub(start).normalize();
    return start.clone().add(dir.multiplyScalar(8));
  }, []);

  const shared = useMemo(
    () => ({
      uTime: { value: 0 },
      uPixelRatio: { value: Math.min(gl.getPixelRatio(), 2) },
    }),
    [gl],
  );
  const cardU = useMemo(() => ({ ...shared, uGather: { value: reduced ? 1 : 0 }, uInk: { value: INK }, uMint: { value: MINT }, uCoral: { value: CORAL } }), [shared, reduced]);
  const particleU = useMemo(() => ({ ...shared, uAssemble: { value: 0 }, uMint: { value: MINT.clone().lerp(LINE, 0.35) }, uInk: { value: STRONG } }), [shared]);
  const threadU = useMemo(
    () => ({ ...shared, uReveal: { value: reduced ? 1 : 0 }, uFocus: { value: 0 }, uFocusIndex: { value: FOCUS_INDEX }, uLine: { value: LINE }, uStrong: { value: STRONG } }),
    [shared, reduced],
  );
  const nodeU = useMemo(
    () => ({ ...shared, uReveal: threadU.uReveal, uFocus: threadU.uFocus, uFocusIndex: threadU.uFocusIndex, uMint: { value: MINT }, uStrong: { value: STRONG } }),
    [shared, threadU],
  );
  const glowU = useMemo(() => ({ uMint: { value: MINT }, uGlow: { value: reduced ? 1 : 0 } }), [reduced]);
  const glowMaterial = useShaderMaterial(glowVertex, glowFragment, glowU);

  useEffect(() => {
    if (reduced) {
      finishIntro();
      // demand mode: render again once the DOM labels have mounted
      const id = window.setTimeout(() => invalidate(), 50);
      return () => window.clearTimeout(id);
    }
    if (story.intro === "pending") story.intro = "playing";
  }, [reduced, invalidate]);

  useFrame((state, dt) => {
    shared.uTime.value += reduced ? 0 : dt;
    const p = story.progress;

    // intro: field -> wordmark -> field. Any scroll interrupts it.
    if (!reduced && story.intro === "playing") {
      introClock.current ??= state.clock.elapsedTime;
      const t = state.clock.elapsedTime - introClock.current;
      const { assemble, hold, release } = INTRO;
      let a: number;
      if (t < assemble) a = smooth(0, assemble, t);
      else if (t < assemble + hold) a = 1;
      else a = 1 - smooth(assemble + hold, assemble + hold + release, t);
      particleU.uAssemble.value = a;
      if (t > assemble + hold * 0.5) finishIntro();
      if (p > 0.01) finishIntro();
    } else {
      const u = particleU.uAssemble;
      u.value += (0 - u.value) * (1 - Math.exp(-dt * 5));
    }

    if (!reduced) {
      cardU.uGather.value = smooth(BEATS.gather[0], BEATS.gather[1], p);
      threadU.uReveal.value = smooth(BEATS.threads[0], BEATS.threads[1], p);
      threadU.uFocus.value = smooth(BEATS.focus[0], BEATS.focus[1], p);
      glowU.uGlow.value = smooth(BEATS.gather[0] + 0.15, BEATS.gather[1], p);
    } else {
      threadU.uFocus.value = 1;
    }

    // DOM labels follow the node shader's visibility (no React state per frame)
    const reveal = threadU.uReveal.value;
    const focus = threadU.uFocus.value;
    labelRefs.current.forEach((el, i) => {
      if (!el) return;
      const appear = smooth(0.55 + i * 0.06, 0.8 + i * 0.06, reveal * 1.35);
      const level = i === FOCUS_INDEX ? 1 : 1 - 0.7 * focus;
      el.style.opacity = String(appear * level);
      if (appear <= 0) return;
      projected.copy(NODES[i]!).add(LABEL_OFFSET).project(camera);
      const x = (projected.x * 0.5 + 0.5) * size.width;
      const y = (-projected.y * 0.5 + 0.5) * size.height + (1 - appear) * 4;
      el.style.transform = `translate3d(${x.toFixed(1)}px, ${y.toFixed(1)}px, 0) translate(-50%, -50%)`;
    });
  });

  return (
    <>
      <Rig reduced={reduced} />
      <mesh position={[0, 0, -0.6]} renderOrder={0} material={glowMaterial}>
        <planeGeometry args={[7, 7]} />
      </mesh>
      <Particles uniforms={particleU} logoCenter={logoCenter} />
      <Cards uniforms={cardU} />
      <Threads uniforms={threadU} />
      <Nodes uniforms={nodeU} />
    </>
  );
}

export default function Scene({ reduced, active }: { reduced: boolean; active: boolean }) {
  const labelRefs = useRef<(HTMLDivElement | null)[]>([]);
  return (
    <>
    <Canvas
      dpr={[1, 2]}
      gl={{ antialias: true, alpha: true, powerPreference: "high-performance" }}
      camera={{ fov: 35, near: 0.1, far: 60, position: [0.6, 0.5, 14] }}
      frameloop={!active ? "never" : reduced ? "demand" : "always"}
      onCreated={({ gl }) => gl.setClearColor(0x000000, 0)}
    >
      <World reduced={reduced} labelRefs={labelRefs} />
    </Canvas>
    {/* Node labels: plain DOM over the canvas, positioned by projecting the nodes each frame */}
    <div aria-hidden className="pointer-events-none absolute inset-0 overflow-hidden">
      {NODE_LABELS.map((label, i) => (
        <div
          key={label}
          ref={(el) => {
            labelRefs.current[i] = el;
          }}
          className="glass absolute left-0 top-0 whitespace-nowrap rounded-full px-3 py-1 text-[12px] font-medium text-ink will-change-transform"
          style={{ opacity: 0 }}
        >
          {label}
        </div>
      ))}
    </div>
    </>
  );
}
