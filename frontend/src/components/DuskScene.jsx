import { motion, useMotionValue, useReducedMotion, useSpring, useTransform } from "framer-motion";
import { useEffect, useMemo } from "react";

// An illustrated dusk valley in layers (sky, mountains, a city on both banks, a river), each layer
// drifting with the pointer at its own depth for a 3D parallax feel. `alert` (0..1) turns the city red.
const W = 1600, H = 900, HORIZON = 560;

// deterministic pseudo-random so the skyline is the same on every render
const rand = (s) => { const x = Math.sin(s * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); };

function skyline(side) {
  // buildings shrink toward the vanishing point in the middle
  const out = [];
  let x = side < 0 ? -40 : W + 40;
  for (let i = 0; i < 20; i++) {
    const d = Math.min(1, Math.abs(x - W / 2) / (W / 2)); // 1 at the edge, 0 at the centre
    const w = 35 + 55 * d + rand(i * 7 + side) * 30;
    const h = 70 + 280 * d * d + rand(i * 3 + side) * 50;
    const bx = side < 0 ? x : x - w;
    if (Math.abs(bx + w / 2 - W / 2) < 150) break; // leave the river valley open
    out.push({ x: bx, w, h, y: HORIZON + 40 + 150 * d - h, haze: 1 - d, seed: i * 13 + (side < 0 ? 1 : 2) });
    x -= side * (w - 4); // walk inward from the edge
  }
  return out.reverse(); // paint the small far ones first, big near ones on top
}

function windows(b) {
  const out = [];
  const cols = Math.max(2, Math.floor(b.w / 22)), rows = Math.floor(b.h / 30);
  for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) {
    const k = rand(b.seed * 31 + r * 7 + c);
    if (k < 0.45) continue;
    out.push({ x: b.x + 10 + c * ((b.w - 20) / cols), y: b.y + 18 + r * 30, w: Math.max(6, (b.w - 20) / cols - 8), lit: k > 0.72, twinkle: k > 0.97 });
  }
  return out;
}

function Layer({ depth, px, py, children }) {
  const x = useTransform(px, (v) => v * depth * 40);
  const y = useTransform(py, (v) => v * depth * 18);
  return <motion.g style={{ x, y }}>{children}</motion.g>;
}

export default function DuskScene({ onPhase, alert = 0, className = "" }) {
  const reduced = useReducedMotion();
  const mx = useMotionValue(0), my = useMotionValue(0);
  const px = useSpring(mx, { stiffness: 40, damping: 18 }), py = useSpring(my, { stiffness: 40, damping: 18 });

  useEffect(() => {
    if (reduced) return;
    const move = (e) => { mx.set(e.clientX / window.innerWidth - 0.5); my.set(e.clientY / window.innerHeight - 0.5); };
    window.addEventListener("pointermove", move);
    return () => window.removeEventListener("pointermove", move);
  }, [reduced, mx, my]);

  // the landing's call card follows a 7.5 s scan cycle
  useEffect(() => {
    if (!onPhase) return;
    if (reduced) { onPhase("hold"); return; }
    const start = performance.now();
    const id = setInterval(() => {
      const t = ((performance.now() - start) / 1000) % 7.5;
      onPhase(t < 4.1 ? "scanning" : t < 5.3 ? "flagging" : "verdict");
    }, 200);
    return () => clearInterval(id);
  }, [onPhase, reduced]);

  const left = useMemo(() => skyline(-1), []), right = useMemo(() => skyline(1), []);
  const lit = alert > 0.3 ? "#ff6b8f" : "#ffd27a";

  return (
    <div className={className} aria-hidden>
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="xMidYMax slice" className="size-full block">
        <defs>
          <radialGradient id="ds-sun" cx="0.5" cy="0.5" r="0.5">
            <stop offset="0" stopColor="#fff4dc" stopOpacity="0.95" />
            <stop offset="0.35" stopColor="#ffd9b8" stopOpacity="0.55" />
            <stop offset="1" stopColor="#ffd9b8" stopOpacity="0" />
          </radialGradient>
          <linearGradient id="ds-far" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#b9b2e6" /><stop offset="1" stopColor="#e6cfe0" /></linearGradient>
          <linearGradient id="ds-mid" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#8f80cf" /><stop offset="1" stopColor="#c9a9d4" /></linearGradient>
          <linearGradient id="ds-near" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#6a57ad" /><stop offset="1" stopColor="#a785c4" /></linearGradient>
          <linearGradient id="ds-mist" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#f3d7d0" stopOpacity="0" /><stop offset="1" stopColor="#f3d7d0" stopOpacity="0.9" /></linearGradient>
          <linearGradient id="ds-river" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#fff1e4" /><stop offset="0.5" stopColor="#b9d3f3" /><stop offset="1" stopColor="#7f9ee0" /></linearGradient>
          <linearGradient id="ds-bldg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#3d2c78" /><stop offset="1" stopColor="#24184f" /></linearGradient>
          <linearGradient id="ds-fall" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#ffffff" stopOpacity="0.2" /><stop offset="1" stopColor="#ffffff" stopOpacity="0.9" /></linearGradient>
        </defs>

        <Layer depth={0.1} px={px} py={py}>
          <circle cx={W / 2} cy={HORIZON - 150} r="330" fill="url(#ds-sun)" />
        </Layer>

        <Layer depth={0.2} px={px} py={py}>
          <path fill="url(#ds-far)" d={`M-80 ${HORIZON} L120 360 L260 430 L420 300 L560 400 L700 270 L800 330 L900 250 L1040 380 L1180 290 L1320 410 L1460 330 L1680 ${HORIZON} Z`} />
        </Layer>

        <Layer depth={0.35} px={px} py={py}>
          <path fill="url(#ds-mid)" d={`M-80 ${HORIZON + 10} L80 440 L230 360 L380 470 L560 340 L700 450 L800 390 L920 460 L1060 330 L1240 470 L1380 380 L1680 ${HORIZON + 10} Z`} />
          {/* snow on the sunlit faces */}
          <path fill="#fbe9f0" opacity="0.75" d="M560 340 L600 372 L578 368 L566 384 L548 360 Z M1060 330 L1102 362 L1080 360 L1066 378 L1046 352 Z M230 360 L262 386 L242 384 L230 398 L214 376 Z" />
          <rect x={W / 2 - 4} y="392" width="8" height={HORIZON - 380} fill="url(#ds-fall)" />
        </Layer>

        <Layer depth={0.5} px={px} py={py}>
          <path fill="url(#ds-near)" d={`M-80 ${HORIZON + 30} L60 470 L200 520 L360 440 L520 ${HORIZON} L1080 ${HORIZON} L1240 450 L1400 510 L1540 460 L1680 ${HORIZON + 30} Z`} />
          <rect x="-80" y={HORIZON - 70} width={W + 160} height="110" fill="url(#ds-mist)" />
        </Layer>

        <Layer depth={0.7} px={px} py={py}>
          <path fill="url(#ds-river)" d={`M${W / 2 - 34} ${HORIZON} L${W / 2 + 34} ${HORIZON} L${W / 2 + 240} ${H + 20} L${W / 2 - 240} ${H + 20} Z`} />
          {[0, 1, 2, 3, 4, 5].map((i) => {
            const y = HORIZON + 30 + i * 55, half = 40 + (y - HORIZON) * 0.85;
            return <line key={i} x1={W / 2 - half * 0.6} x2={W / 2 + half * 0.6} y1={y} y2={y} stroke="#ffffff" strokeOpacity="0.7" strokeWidth={1.5 + i * 0.5}
              strokeDasharray="60 40" className={reduced ? "" : "ds-shimmer"} style={{ animationDelay: `${-i * 0.7}s` }} />;
          })}
        </Layer>

        <Layer depth={0.9} px={px} py={py}>
          {[...left, ...right].map((b) => (
            <g key={b.seed}>
              <rect x={b.x} y={b.y} width={b.w} height={H - b.y + 40} fill="url(#ds-bldg)" />
              <rect x={b.x} y={b.y} width={b.w} height="4" fill="#ffb98a" opacity="0.5" />
              <rect x={b.x} y={b.y} width={b.w} height={H - b.y + 40} fill="#c9b6e4" opacity={b.haze * 0.55} />
              {windows(b).map((w, i) => (
                <rect key={i} x={w.x} y={w.y} width={w.w} height="12" rx="1.5" fill={w.lit ? lit : "#4a3a8a"} opacity={w.lit ? 0.9 : 0.6}
                  className={w.twinkle && !reduced ? "ds-twinkle" : ""} style={{ transition: "fill 0.7s" }} />
              ))}
            </g>
          ))}
        </Layer>

        <Layer depth={1.2} px={px} py={py}>
          {[[W / 2 - 300, H - 20, 70], [W / 2 - 180, H + 10, 55], [W / 2 + 200, H - 10, 80], [W / 2 + 320, H + 15, 60], [W / 2 - 40, H + 25, 50]].map(([cx, cy, r], i) => (
            <ellipse key={i} cx={cx} cy={cy} rx={r} ry={r * 0.45} fill="#4b3790" />
          ))}
        </Layer>

        <rect width={W} height={H} fill="#ff2d6f" opacity={alert * 0.18} style={{ transition: "opacity 0.7s" }} />
      </svg>
    </div>
  );
}
