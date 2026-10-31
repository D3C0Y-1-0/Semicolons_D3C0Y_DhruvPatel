import { Canvas, useFrame } from "@react-three/fiber";
import { useInView, useReducedMotion } from "framer-motion";
import { useMemo, useRef } from "react";
import * as THREE from "three";

// A voice spectrogram as a 3D landscape at dusk: x = time, z = frequency band, y = energy.
// A scan beam sweeps left to right; the cloned-voice segment runs hot once the beam has passed it.
const ROWS = 54, COLS = 150, W = 15, D = 8.5;
const FLAG = [0.55, 0.71]; // the synthetic segment, as a fraction of the time axis
const MINT = new THREE.Color("#ffffff"), NIGHT = new THREE.Color("#2b2370"), RED = new THREE.Color("#ff2d6f"), WHITE = new THREE.Color("#ffd84a");
const FOG = "#f3d7d0"; // matches the bottom of the .dusk sky so far ridges dissolve into it

function Ridges({ onPhase, alert, frozen }) {
  const t = useRef(frozen ? 5.2 : 0), phase = useRef("");
  const beam = useRef();
  const geo = useMemo(() => {
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(new Float32Array(ROWS * COLS * 3), 3));
    g.setAttribute("color", new THREE.BufferAttribute(new Float32Array(ROWS * COLS * 3), 3));
    const idx = [];
    for (let r = 0; r < ROWS; r++) for (let c = 0; c < COLS - 1; c++) idx.push(r * COLS + c, r * COLS + c + 1);
    g.setIndex(idx);
    return g;
  }, []);
  const tmp = useMemo(() => new THREE.Color(), []);

  useFrame((state, dt) => {
    if (!frozen) t.current = state.clock.elapsedTime;
    const time = t.current;
    const cycle = 7.5; // seconds per sweep
    const scan = frozen ? 1.1 : ((time % cycle) / cycle) * 1.3 - 0.1;
    const pos = geo.attributes.position.array, col = geo.attributes.color.array;
    for (let r = 0; r < ROWS; r++) {
      const z = r / (ROWS - 1);
      for (let c = 0; c < COLS; c++) {
        const x = c / (COLS - 1);
        const i = (r * COLS + c) * 3;
        // speech-like envelope: syllables + phrases, drifting slowly
        const env = 0.25 + 0.75 * Math.pow(Math.abs(Math.sin(x * 11 + time * 0.35)), 1.6) * (0.55 + 0.45 * Math.sin(x * 29 + 1.3));
        const inFlag = x > FLAG[0] && x < FLAG[1];
        const formant = inFlag
          ? 0.42 + 0.42 * Math.sin(c * 0.42 + r * 0.55 + time * 2.2) // too-regular harmonics: the clone's tell
          : 0.5 + 0.5 * Math.sin(c * 0.37 + r * 0.83 + time * 1.7) * Math.cos(r * 2.1 + c * 0.11 - time);
        const grain = 0.12 * Math.sin(r * 12.9898 + c * 78.233 + Math.floor(time * 6));
        const h = Math.max(0, env * formant * formant * (1.25 - z * 0.85) * 1.9 + (inFlag ? 0 : grain * env));
        pos[i] = (x - 0.5) * W;
        pos[i + 1] = h;
        pos[i + 2] = (z - 0.5) * D;

        const depth = 0.25 + 0.75 * (1 - z);
        tmp.copy(NIGHT).lerp(MINT, depth * (0.35 + 0.65 * Math.min(1, h / 1.4)));
        if (inFlag && x < scan) { tmp.lerp(RED, 0.85 * depth + 0.15); tmp.lerp(WHITE, Math.min(1, h / 1.6) * 0.7 * depth); } // hot peaks go white-hot
        else if (alert && x < scan) tmp.lerp(RED, 0.35 * alert * depth);
        const near = Math.abs(x - scan);
        if (near < 0.025) tmp.lerp(MINT, (1 - near / 0.025) * 0.9);
        col[i] = tmp.r; col[i + 1] = tmp.g; col[i + 2] = tmp.b;
      }
    }
    geo.attributes.position.needsUpdate = true;
    geo.attributes.color.needsUpdate = true;
    if (beam.current) beam.current.position.x = (Math.min(Math.max(scan, 0), 1) - 0.5) * W;

    const p = scan < FLAG[0] ? "scanning" : scan < FLAG[1] ? "flagging" : scan < 1.05 ? "verdict" : "hold";
    if (p !== phase.current) { phase.current = p; onPhase?.(p); }

    // gentle parallax towards the pointer
    const cam = state.camera;
    cam.position.x += (state.pointer.x * 1.4 - cam.position.x) * 0.04;
    cam.position.y += (5.2 + state.pointer.y * 0.6 - cam.position.y) * 0.04;
    cam.lookAt(0, 0.4, 0);
  });

  return (
    <>
      <lineSegments geometry={geo}>
        <lineBasicMaterial vertexColors transparent opacity={0.95} />
      </lineSegments>
      <mesh ref={beam} position={[0, 1.2, 0]}>
        <planeGeometry args={[0.05, 3.2]} />
        <meshBasicMaterial color="#ffffff" transparent opacity={frozen ? 0 : 0.8} depthWrite={false} />
      </mesh>
    </>
  );
}

export default function Spectrogram3D({ onPhase, alert = 0, className = "", fog = FOG }) {
  const box = useRef();
  const visible = useInView(box, { margin: "100px" });
  const reduced = useReducedMotion();
  return (
    <div ref={box} className={className} aria-hidden>
      <Canvas camera={{ position: [0, 5.2, 9.2], fov: 42 }} dpr={[1, 1.75]} frameloop={visible ? "always" : "never"}
        gl={{ antialias: true, alpha: true }} onCreated={({ scene }) => { scene.fog = new THREE.Fog(fog, 9, 18); }}>
        <Ridges onPhase={onPhase} alert={alert} frozen={!!reduced} />
      </Canvas>
    </div>
  );
}
