import { motion, useReducedMotion, useScroll, useTransform } from "framer-motion";
import { useRef } from "react";

// One continuous illustrated world for the landing page. Each chapter is a full-bleed section whose
// art is stacked in depth layers; scrolling moves far layers slowly and near layers fast, and each
// chapter's "lip" (rocks, grass, the lake's edge) hangs over the next one, so the page reads as a
// single descent from a sunset mountain, down a waterfall, through a night forest, to dawn.

export function rng(seed) { // mulberry32: the same world on every render
  let a = seed >>> 0;
  return () => { a = (a + 0x6d2b79f5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
const r1 = (n) => Math.round(n * 10) / 10;
const pts = (a) => a.map(([x, y]) => `${r1(x)} ${r1(y)}`).join(" L");
const poly = (...a) => `M${pts(a)}Z`;

// ---------- engine ----------
const PAD = 13; // vh each layer overhangs its chapter, more than the largest parallax shift (0.55 × 20vh)

function Layer({ p, speed, children }) {
  const reduced = useReducedMotion();
  const y = useTransform(p, [0, 1], [`${-speed * 20}vh`, `${speed * 20}vh`]);
  return <motion.div className="absolute inset-x-0 will-change-transform" style={{ top: `-${PAD}vh`, bottom: `-${PAD}vh`, ...(reduced ? {} : { y }) }}>{children}</motion.div>;
}

function Lip({ p, speed, h, children }) {
  const reduced = useReducedMotion();
  const y = useTransform(p, [0, 1], [`${-speed * 20}vh`, `${speed * 20}vh`]);
  return (
    <motion.div aria-hidden className="absolute inset-x-0 z-[5] pointer-events-none will-change-transform" style={{ bottom: `-${h * (h > 30 ? 0.32 : 0.55)}vw`, height: `${h}vw`, ...(reduced ? {} : { y }) }}>
      {children}
    </motion.div>
  );
}

export function Chapter({ id, layers, lip, bg, z, className = "", children }) {
  const ref = useRef(null);
  const { scrollYProgress: p } = useScroll({ target: ref, offset: ["start end", "end start"] });
  return (
    <section id={id} ref={ref} className={`relative ${className}`} style={{ background: bg, zIndex: z }}>
      <div aria-hidden className="absolute inset-0 overflow-hidden">
        {layers.map((l, i) => <Layer key={i} p={p} speed={l.speed}>{l.art}</Layer>)}
      </div>
      {lip && <Lip p={p} speed={lip.speed} h={lip.h}>{lip.art}</Lip>}
      <div className="relative z-10">{children}</div>
    </section>
  );
}

// Art keeps its proportions (sized by width, at least 80vh tall on phones), sits on the chapter's bottom
// edge, and may paint above its viewBox: `top` fills the sky upward for chapters taller than the art.
const Art = ({ h = 1000, top, children }) => (
  <svg viewBox={`0 0 1600 ${h}`} preserveAspectRatio="xMidYMax slice" overflow="visible" className="absolute inset-x-0 w-full"
    style={{ bottom: `${PAD}vh`, height: `max(${r1(h / 16)}vw, 80vh)` }}>
    {top && <rect x="-1600" y="-4000" width="4800" height="4000" fill={top} />}
    {children}
  </svg>
);
const LipArt = ({ h, children }) => (
  <svg viewBox={`0 0 1600 ${h}`} preserveAspectRatio="xMidYMax slice" className="absolute inset-0 size-full">{children}</svg>
);

// ---------- drawing primitives ----------
function ridge(seed, y, amp, n, bottom = 1200) {
  const r = rng(seed), p = Array.from({ length: n + 1 }, (_, i) => [-120 + (i * 1840) / n, y - r() * amp]);
  let d = `M-120 ${bottom} L${r1(p[0][0])} ${r1(p[0][1])}`;
  for (let i = 0; i < n; i++) { const [x0, y0] = p[i], [x1, y1] = p[i + 1]; d += ` Q${r1(x0)} ${r1(y0)} ${r1((x0 + x1) / 2)} ${r1((y0 + y1) / 2)}`; }
  return d + ` L1720 ${r1(p[n][1])} L1720 ${bottom} Z`;
}

function pines(seed, { x0 = -60, x1 = 1660, base, hMin, hMax, n }) {
  const r = rng(seed);
  let d = "";
  for (let i = 0; i < n; i++) {
    const x = x0 + r() * (x1 - x0), h = hMin + r() * (hMax - hMin), w = h * (0.3 + r() * 0.12);
    for (let t = 0; t < 4; t++) {
      const ty = base - h + (h * 0.72 * t) / 4, tw = w * (0.4 + (0.6 * (t + 1)) / 4), th = h * 0.36;
      d += `M${r1(x)} ${r1(ty)}L${r1(x + tw / 2)} ${r1(ty + th)}L${r1(x + tw * 0.12)} ${r1(ty + th * 0.9)}L${r1(x - tw * 0.12)} ${r1(ty + th * 0.92)}L${r1(x - tw / 2)} ${r1(ty + th)}Z`;
    }
    d += `M${r1(x - w * 0.05)} ${r1(base - h * 0.12)}h${r1(w * 0.1)}V${base + 60}h${r1(-w * 0.1)}Z`;
  }
  return d;
}

function grass(seed, { x0, x1, base, hMin, hMax, n, lean = 0.25 }) {
  const r = rng(seed);
  let d = "";
  for (let i = 0; i < n; i++) {
    const x = x0 + r() * (x1 - x0), h = hMin + r() * (hMax - hMin), w = 2 + r() * 4.5, b = (r() - 0.35) * lean * h;
    d += `M${r1(x - w)} ${base} Q${r1(x + b * 0.3)} ${r1(base - h * 0.55)} ${r1(x + b)} ${r1(base - h)} Q${r1(x + b * 0.3 + w * 0.6)} ${r1(base - h * 0.5)} ${r1(x + w)} ${base}Z`;
  }
  return d;
}

function fern(seed, x, y, len, ang) { // a frond of paired leaflets along a curving stem
  const r = rng(seed);
  let d = "", px = x, py = y, a = ang;
  const n = 13;
  for (let i = 1; i <= n; i++) {
    const t = i / n, step = len / n;
    a += 0.035 + r() * 0.02;
    px += Math.cos(a) * step; py += Math.sin(a) * step;
    const l = len * 0.2 * (1 - t * 0.75);
    for (const s of [-1, 1]) {
      const nx = Math.cos(a + s * 1.25), ny = Math.sin(a + s * 1.25);
      const tip = [px + nx * l, py + ny * l], back = [px - Math.cos(a) * step * 0.6, py - Math.sin(a) * step * 0.6];
      d += `M${r1(px)} ${r1(py)} Q${r1(tip[0] + Math.cos(a) * l * 0.25)} ${r1(tip[1] + Math.sin(a) * l * 0.25)} ${r1(tip[0])} ${r1(tip[1])} Q${r1(back[0] + nx * l * 0.4)} ${r1(back[1] + ny * l * 0.4)} ${r1(back[0])} ${r1(back[1])}Z`;
    }
  }
  return d;
}

function leaf(x, y, len, ang, wide = 0.38) { // a broad leaf with a pointed tip
  const c = Math.cos(ang), s = Math.sin(ang), tip = [x + c * len, y + s * len], w = len * wide;
  const m = (t, side) => [x + c * len * t - s * w * side, y + s * len * t + c * w * side];
  const [a, b] = [m(0.45, 1), m(0.45, -1)];
  return `M${r1(x)} ${r1(y)} Q${r1(a[0])} ${r1(a[1])} ${r1(tip[0])} ${r1(tip[1])} Q${r1(b[0])} ${r1(b[1])} ${r1(x)} ${r1(y)}Z`;
}

function rocks(seed, list) { // list of [cx, cy, rx]: faceted stones, a lit top and a dark base
  const r = rng(seed);
  return list.map(([cx, cy, rx], i) => {
    const ry = rx * 0.6, top = [cx - rx * (0.1 + r() * 0.3), cy - ry];
    const L = [cx - rx, cy + ry * 0.35], R = [cx + rx, cy + ry * 0.35], ml = [cx - rx * 0.75, cy - ry * 0.45], mr = [cx + rx * 0.7, cy - ry * 0.4], low = [cx + rx * 0.1, cy + ry * 0.55];
    return { key: i, base: poly(L, ml, top, mr, R, low), lit: poly(ml, top, [cx + rx * 0.05, cy - ry * 0.15], [cx - rx * 0.55, cy + ry * 0.05]), side: poly(top, mr, R, [cx + rx * 0.05, cy - ry * 0.15]) };
  });
}

function stars(seed, n, yMax) { const r = rng(seed); return Array.from({ length: n }, () => ({ cx: r() * 1600, cy: r() * yMax, r: 0.6 + r() * 1.4, o: 0.25 + r() * 0.65 })); }

const Stars = ({ list }) => list.map((s, i) => <circle key={i} cx={s.cx} cy={s.cy} r={s.r} fill="#fff" opacity={s.o} className={i % 7 === 0 ? "w-twinkle" : undefined} style={{ animationDelay: `${-i * 0.37}s` }} />);
const Rocks = ({ list, lit = "#a983cf", side = "#2d2468", base = "url(#w-rock)" }) => list.map((k) => (
  <g key={k.key}><path d={k.base} fill={base} /><path d={k.side} fill={side} opacity="0.6" /><path d={k.lit} fill={lit} opacity="0.75" /></g>
));
const Glow = ({ cx, cy, r, color = "url(#w-glowWarm)", className }) => <circle cx={cx} cy={cy} r={r} fill={color} className={className} />;

function Falls({ x, y, w, h, mist = true }) {
  return (
    <g>
      <path d={`M${x} ${y} L${x + w} ${y} L${x + w * 1.08} ${y + h} L${x - w * 0.08} ${y + h} Z`} fill="url(#w-fall)" />
      {Array.from({ length: 9 }, (_, i) => {
        const lx = x + (w * (i + 0.5)) / 9;
        return <line key={i} x1={lx} y1={y} x2={lx + (i - 4) * 1.5} y2={y + h} stroke="#ffffff" strokeOpacity={0.25 + (i % 3) * 0.15} strokeWidth={2 + (i % 2) * 2}
          strokeDasharray={`${40 + (i % 4) * 18} ${22 + (i % 3) * 14}`} className="w-fall" style={{ animationDuration: `${0.9 + (i % 4) * 0.25}s` }} />;
      })}
      {mist && [[-0.3, 0, 1.1], [0.5, -10, 0.9], [1.2, 6, 1.0]].map(([dx, dy, k], i) => <ellipse key={i} cx={x + w * dx + w / 2 - w * 0.2} cy={y + h + dy} rx={w * 1.1 * k} ry={w * 0.45 * k} fill="url(#w-puff)" className="w-breathe" style={{ animationDelay: `${-i}s` }} />)}
    </g>
  );
}

function Rays({ x, y, angles, len = 1700, width = 3, className = "w-rays" }) {
  return (
    <g className={className} style={{ mixBlendMode: "screen" }}>
      {angles.map((a, i) => {
        const w = ((width + (i % 3)) * Math.PI) / 180, t = (a * Math.PI) / 180;
        return <path key={i} d={poly([x, y], [x + Math.cos(t - w) * len, y + Math.sin(t - w) * len], [x + Math.cos(t + w) * len, y + Math.sin(t + w) * len])} fill="url(#w-ray)" style={{ animationDelay: `${-i * 1.3}s` }} />;
      })}
    </g>
  );
}

function Birds({ y, n = 11, seed = 1 }) {
  const r = rng(seed);
  return (
    <g className="w-birds">
      {Array.from({ length: n }, (_, i) => {
        const x = 1700 + i * 34 + r() * 40, by = y + (i % 2 ? 1 : -1) * (i * 6) + r() * 20, s = 0.7 + r() * 0.6;
        return (
          <g key={i} transform={`translate(${r1(x)} ${r1(by)}) scale(${r1(s)})`}>
            <path d="M-11 0 Q-5 -7 0 0 Q5 -7 11 0" fill="none" stroke="#fff6ee" strokeWidth="2.2" strokeLinecap="round" className="w-flap" style={{ animationDelay: `${-r() * 0.8}s` }} />
          </g>
        );
      })}
    </g>
  );
}

function Fireflies({ n = 18, seed = 1, warm = true, top = 10, height = 80 }) {
  const r = rng(seed);
  return (
    <div className="absolute inset-0">
      {Array.from({ length: n }, (_, i) => (
        <span key={i} className="ds-mote absolute rounded-full" style={{
          left: `${r() * 100}%`, top: `${top + r() * height}%`, width: 3 + r() * 4, height: 3 + r() * 4, "--o": 0.5 + r() * 0.5,
          animationDuration: `${8 + r() * 10}s`, animationDelay: `${-r() * 16}s`,
          background: warm ? "radial-gradient(circle, #fffbe8 0%, #ffd27a 55%, transparent 72%)" : "radial-gradient(circle, #f4fffe 0%, #7ff0ff 55%, transparent 72%)",
          boxShadow: warm ? "0 0 12px 3px rgb(255 210 130 / 0.55)" : "0 0 12px 3px rgb(120 235 255 / 0.5)",
        }} />
      ))}
    </div>
  );
}

// shared gradients, rendered once on the page
export function WorldDefs() {
  return (
    <svg width="0" height="0" className="absolute" aria-hidden focusable="false">
      <defs>
        <linearGradient id="w-heroSky" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#1d1656" /><stop offset="0.28" stopColor="#3a2a8c" /><stop offset="0.52" stopColor="#8b4fa8" />
          <stop offset="0.68" stopColor="#ff8a62" /><stop offset="0.8" stopColor="#ffc27e" /><stop offset="1" stopColor="#ffb08a" />
        </linearGradient>
        <radialGradient id="w-sun" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stopColor="#fff3d6" stopOpacity="0.95" /><stop offset="0.3" stopColor="#ffc98a" stopOpacity="0.6" /><stop offset="1" stopColor="#ff8a62" stopOpacity="0" /></radialGradient>
        <linearGradient id="w-mtLit" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#ffd88a" /><stop offset="0.5" stopColor="#ff9a5a" /><stop offset="1" stopColor="#e2577a" /></linearGradient>
        <linearGradient id="w-mtMid" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#ef7aa0" /><stop offset="1" stopColor="#9b4c9f" /></linearGradient>
        <linearGradient id="w-mtShade" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#5a45a8" /><stop offset="1" stopColor="#2f2674" /></linearGradient>
        <linearGradient id="w-haze" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#8a62bf" stopOpacity="0" /><stop offset="1" stopColor="#8a62bf" stopOpacity="0.9" /></linearGradient>
        <linearGradient id="w-lake" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#ffc28c" /><stop offset="0.25" stopColor="#e9839a" /><stop offset="0.6" stopColor="#7b5cc0" /><stop offset="1" stopColor="#2e2578" /></linearGradient>
        <radialGradient id="w-puff" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stopColor="#fff8f6" stopOpacity="0.9" /><stop offset="0.55" stopColor="#ffd9d4" stopOpacity="0.5" /><stop offset="1" stopColor="#f2bccd" stopOpacity="0" /></radialGradient>
        <radialGradient id="w-puffWarm" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stopColor="#ffe9d2" stopOpacity="0.95" /><stop offset="0.55" stopColor="#ffbfa0" stopOpacity="0.55" /><stop offset="1" stopColor="#e88aa8" stopOpacity="0" /></radialGradient>
        <linearGradient id="w-grassLit" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#ffc46b" /><stop offset="0.35" stopColor="#c45a7c" /><stop offset="1" stopColor="#21184f" /></linearGradient>
        <linearGradient id="w-grassMoon" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#b9a8ff" /><stop offset="0.4" stopColor="#3a2f86" /><stop offset="1" stopColor="#120d33" /></linearGradient>
        <linearGradient id="w-fall" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#ffe7d6" stopOpacity="0.9" /><stop offset="0.4" stopColor="#c9d8ff" stopOpacity="0.85" /><stop offset="1" stopColor="#8fb6ff" stopOpacity="0.95" /></linearGradient>
        <linearGradient id="w-ray" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#fff2d8" stopOpacity="0.2" /><stop offset="1" stopColor="#fff2d8" stopOpacity="0" /></linearGradient>
        <radialGradient id="w-glowWarm" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stopColor="#fff1c4" stopOpacity="1" /><stop offset="0.25" stopColor="#ffc96b" stopOpacity="0.55" /><stop offset="1" stopColor="#ff9a4a" stopOpacity="0" /></radialGradient>
        <radialGradient id="w-glowPink" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stopColor="#ffe3f0" stopOpacity="1" /><stop offset="0.3" stopColor="#ff6fae" stopOpacity="0.55" /><stop offset="1" stopColor="#ff3d8b" stopOpacity="0" /></radialGradient>
        <radialGradient id="w-glowCyan" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stopColor="#eaffff" stopOpacity="1" /><stop offset="0.3" stopColor="#5fe3f2" stopOpacity="0.45" /><stop offset="1" stopColor="#2bb5d8" stopOpacity="0" /></radialGradient>
        <radialGradient id="w-moon" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stopColor="#f6f1ff" stopOpacity="0.9" /><stop offset="0.2" stopColor="#c9bcff" stopOpacity="0.35" /><stop offset="1" stopColor="#7d6bd8" stopOpacity="0" /></radialGradient>
        <linearGradient id="w-rock" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#6c55b0" /><stop offset="1" stopColor="#1e1650" /></linearGradient>
        <linearGradient id="w-forest" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#1b1550" /><stop offset="0.6" stopColor="#130f3a" /><stop offset="1" stopColor="#0e0a2a" /></linearGradient>
        <linearGradient id="w-pool" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#0e0a2a" /><stop offset="0.55" stopColor="#141a4a" /><stop offset="1" stopColor="#0f0b2c" /></linearGradient>
        <linearGradient id="w-water" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#3dc7de" stopOpacity="0.55" /><stop offset="1" stopColor="#1b2d6e" stopOpacity="0.9" /></linearGradient>
        <linearGradient id="w-night" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#0f0b2c" /><stop offset="0.55" stopColor="#231c63" /><stop offset="1" stopColor="#3d2f8f" /></linearGradient>
        <linearGradient id="w-predawn" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#1a1446" /><stop offset="0.45" stopColor="#4a338f" /><stop offset="0.75" stopColor="#b25c9e" /><stop offset="1" stopColor="#ff9a7e" /></linearGradient>
        <linearGradient id="w-dawn" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#1e1850" /><stop offset="0.35" stopColor="#6b4fb0" /><stop offset="0.65" stopColor="#ff9a7a" /><stop offset="0.85" stopColor="#ffd59a" /><stop offset="1" stopColor="#ffe6c4" /></linearGradient>
        <linearGradient id="w-river" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#ffb08e" /><stop offset="0.4" stopColor="#9a5aa8" /><stop offset="1" stopColor="#231c5c" /></linearGradient>
        <linearGradient id="w-cliff" x1="0" y1="-500" x2="0" y2="250" gradientUnits="userSpaceOnUse"><stop offset="0" stopColor="#1b1550" /><stop offset="1" stopColor="#2b2470" /></linearGradient>
        <clipPath id="w-lakeClip"><rect x="0" y="760" width="1600" height="200" /></clipPath>
      </defs>
    </svg>
  );
}

// ================= chapter 1: sunset mountain over a lake =================
const MOUNTAIN = {
  shade: poly([380, 800], [600, 580], [740, 480], [840, 430], [905, 470], [985, 375], [1060, 250], [1130, 160], [1175, 208], [1240, 250], [1305, 330], [1385, 380], [1475, 455], [1580, 520], [1720, 610], [1720, 820], [380, 820]),
  lit: [
    poly([1130, 160], [1060, 250], [985, 375], [1045, 420], [1100, 300]),
    poly([840, 430], [740, 480], [600, 580], [690, 600], [800, 515]),
    poly([600, 580], [380, 800], [600, 800], [690, 600]),
    poly([985, 375], [905, 470], [930, 520], [1045, 420]),
  ],
  mid: [
    poly([1130, 160], [1100, 300], [1150, 360], [1175, 208]),
    poly([1045, 420], [930, 520], [990, 650], [1100, 560], [1150, 360], [1100, 300]),
    poly([800, 515], [690, 600], [740, 720], [860, 640], [905, 470], [840, 430]),
  ],
  dark: [
    poly([1175, 208], [1240, 250], [1305, 330], [1230, 420], [1150, 360]),
    poly([1305, 330], [1385, 380], [1475, 455], [1380, 540], [1230, 420]),
  ],
  snow: [poly([1130, 160], [1098, 206], [1116, 200], [1128, 232], [1148, 200], [1175, 208]), poly([840, 430], [812, 452], [836, 450], [850, 466], [868, 446], [905, 470])],
};
const HERO_STARS = stars(11, 70, 300);
const HERO_GRASS = grass(21, { x0: 820, x1: 1700, base: 560, hMin: 90, hMax: 330, n: 170, lean: 0.35 });
const HERO_GRASS_BACK = grass(23, { x0: 760, x1: 1700, base: 300, hMin: 40, hMax: 150, n: 120, lean: 0.3 });
const HERO_LAKE_ROCKS = rocks(31, [[540, 845, 46], [700, 870, 30], [1010, 860, 38], [330, 880, 60]]);

export const HERO_LAYERS = [
  { speed: 0.55, art: <Art top="#1d1656"><rect width="1600" height="1000" fill="url(#w-heroSky)" /><Stars list={HERO_STARS} /><Glow cx={1180} cy={560} r={520} color="url(#w-sun)" /></Art> },
  { speed: 0.48, art: <Art><path d={ridge(3, 690, 110, 9)} fill="#7a4fa6" opacity="0.55" /><path d={ridge(5, 730, 80, 11)} fill="#5c3f98" opacity="0.6" /></Art> },
  { speed: 0.4, art: (
    <Art>
      <g className="w-breathe-slow">
        <path d={MOUNTAIN.shade} fill="url(#w-mtShade)" />
        {MOUNTAIN.lit.map((d, i) => <path key={`l${i}`} d={d} fill="url(#w-mtLit)" />)}
        {MOUNTAIN.mid.map((d, i) => <path key={`m${i}`} d={d} fill="url(#w-mtMid)" opacity="0.85" />)}
        {MOUNTAIN.dark.map((d, i) => <path key={`d${i}`} d={d} fill="#3b2f88" opacity="0.7" />)}
        {MOUNTAIN.snow.map((d, i) => <path key={`s${i}`} d={d} fill="#ffeede" />)}
      </g>
      <rect x="0" y="620" width="1600" height="200" fill="url(#w-haze)" />
    </Art>
  ) },
  { speed: 0.33, art: (
    <Art>
      <g className="w-drift">{[[640, 540, 150], [800, 560, 120], [1450, 470, 170], [1560, 520, 140], [1300, 560, 110], [940, 590, 130], [1150, 610, 160]].map(([cx, cy, rx], i) => <ellipse key={i} cx={cx} cy={cy} rx={rx} ry={rx * 0.38} fill="url(#w-puffWarm)" />)}</g>
      <Birds y={330} n={12} seed={4} />
    </Art>
  ) },
  { speed: 0.22, art: (
    <Art>
      <path d="M-120 1100 L-120 700 Q120 640 300 690 Q460 730 560 760 L620 800 L-120 1100 Z" fill="#3b2c82" />
      <path d="M-120 1100 L-120 760 Q180 720 380 760 L520 790 L-120 1100 Z" fill="#2a2068" />
      <rect x="0" y="760" width="1600" height="200" fill="url(#w-lake)" />
      <g clipPath="url(#w-lakeClip)" opacity="0.28" transform="translate(0 1560) scale(1 -1)"><path d={MOUNTAIN.shade} fill="#2f2674" />{MOUNTAIN.lit.map((d, i) => <path key={i} d={d} fill="#ffb07a" />)}</g>
      {Array.from({ length: 16 }, (_, i) => { const r = rng(90 + i), y = 775 + r() * 170, x = r() * 1500, w = 30 + r() * 120; return <line key={i} x1={x} x2={x + w} y1={y} y2={y} stroke="#fff3e6" strokeOpacity={0.25 + r() * 0.4} strokeWidth="2" strokeLinecap="round" className="w-glint" style={{ animationDelay: `${-r() * 4}s` }} />; })}
      <Rocks list={HERO_LAKE_ROCKS} lit="#c58fc9" />
    </Art>
  ) },
];

// someone taking the call, seen from behind: head, neck, shoulders, a jacket, the phone held to the right ear
const FIGURE = [
  "M1240 634 C1256 634 1265 647 1264 664 C1263 680 1253 692 1240 692 C1227 692 1217 680 1216 664 C1215 647 1224 634 1240 634 Z",
  "M1231 688 L1249 688 L1251 702 L1229 702 Z",
  "M1229 698 L1251 698 Q1266 704 1291 711 Q1311 718 1315 742 L1320 832 Q1322 858 1312 878 L1318 1010 L1162 1010 L1168 878 Q1158 858 1160 832 L1165 742 Q1169 718 1189 711 Q1214 704 1229 698 Z",
  "M1298 716 Q1330 714 1336 690 Q1336 668 1270 662 L1266 676 Q1312 682 1316 694 Q1312 704 1294 712 Z",
  "M1167 742 Q1150 800 1154 872 L1170 870 Q1168 806 1180 750 Z",
];

// the lake's front edge spills into the waterfall of chapter 2; grass and the figure hang over it
export const HERO_LIP = { speed: -0.3, h: 34, art: (
  <LipArt h={540}>
    <path d="M-60 540 L-60 250 Q140 215 250 228 L268 236 L430 236 L452 226 Q700 205 900 240 Q1150 280 1300 250 Q1480 225 1660 250 L1660 540 Z" fill="#1d1650" />
    <path d="M-60 260 Q140 222 250 232 L268 240 L430 240 L452 232 Q700 212 900 246" fill="none" stroke="#ffb98a" strokeOpacity="0.5" strokeWidth="3" />
    <Falls x={272} y={236} w={156} h={330} mist={false} />
    <g className="w-sway"><path d={HERO_GRASS_BACK} fill="#2a1f5e" /></g>
    {/* the person taking the call, seen from behind, rim-lit by the sunset */}
    <g transform="translate(1300 600) scale(1.45) translate(-1240 -1010)">
      <g fill="#ffb36b" transform="translate(-4 -1)">{FIGURE.map((d, i) => <path key={i} d={d} />)}</g>
      <circle cx="1262" cy="664" r="64" fill="url(#w-glowPink)" className="w-pulse" />
      <g fill="#1f1850">{FIGURE.map((d, i) => <path key={i} d={d} />)}</g>
      <rect x="1255" y="652" width="10" height="21" rx="2.5" fill="#ff86b0" transform="rotate(-12 1260 662)" />
    </g>
    <g className="w-sway-2"><path d={HERO_GRASS} fill="url(#w-grassLit)" /></g>
  </LipArt>
) };

// ================= chapter 2: the waterfall drops into a night forest =================
const C2_PINES_A = pines(41, { base: 520, hMin: 120, hMax: 230, n: 46, x0: 380 });
const C2_PINES_B = pines(43, { base: 660, hMin: 140, hMax: 280, n: 34, x0: 420 });
const C2_FERNS = [fern(51, 40, 1000, 320, -1.1), fern(52, 160, 1010, 280, -1.6), fern(53, 300, 1000, 300, -2.2), fern(54, 520, 1020, 260, -1.3), fern(55, 640, 1000, 220, -2.0), fern(56, 1460, 1010, 300, -1.9), fern(57, 1560, 1000, 260, -2.4)];
const C2_LEAVES = [leaf(-20, 900, 260, -0.55), leaf(30, 960, 300, -0.15), leaf(120, 1000, 240, -0.9), leaf(1620, 920, 280, -2.6), leaf(1580, 990, 240, -3.0)];

export const PROBLEM_LAYERS = [
  { speed: 0.5, art: <Art top="#1b1550"><rect width="1600" height="1000" fill="url(#w-forest)" /><Stars list={stars(61, 40, 260)} /><Glow cx={1350} cy={120} r={320} color="url(#w-moon)" /></Art> },
  { speed: 0.4, art: <Art><path d={C2_PINES_A} fill="#2a2468" opacity="0.8" /><rect x="0" y="420" width="1600" height="160" fill="url(#w-haze)" opacity="0.35" /><path d={C2_PINES_B} fill="#1c1850" /></Art> },
  { speed: 0.26, art: (
    <Art>
      <path d="M-80 -2000 L560 -2000 L560 -60 L530 110 L575 250 L505 410 L548 560 L478 700 L520 860 L430 1080 L-80 1080 Z" fill="url(#w-cliff)" />
      {[[[560, -60], [530, 110], [470, 60]], [[575, 250], [505, 410], [470, 300]], [[548, 560], [478, 700], [440, 600]], [[520, 860], [430, 1080], [400, 900]], [[530, 110], [575, 250], [490, 200]]].map((p, i) => <path key={i} d={poly(...p)} fill="#4d3f9c" opacity="0.75" />)}
      <Falls x={268} y={-2000} w={164} h={2840} />
    </Art>
  ) },
  { speed: 0.16, art: <Art><Rays x={1520} y={-120} angles={[118, 125, 133, 141, 149]} len={1900} width={3.2} /></Art> },
  { speed: 0.02, art: <Fireflies n={22} seed={7} top={25} height={65} /> },
  { speed: -0.12, art: (
    <Art>
      {C2_LEAVES.map((d, i) => <path key={i} d={d} fill={i % 2 ? "#2f2a78" : "#3f3592"} />)}
      <g className="w-sway">{C2_FERNS.map((d, i) => <path key={i} d={d} fill={i % 3 === 0 ? "#4a3f9e" : "#2c2670"} />)}</g>
      {[[230, 900], [420, 930], [560, 880], [1500, 900], [1380, 940]].map(([x, y], i) => <g key={i} className="w-pulse" style={{ animationDelay: `${-i * 0.7}s` }}><Glow cx={x} cy={y} r={34} color="url(#w-glowPink)" /><circle cx={x} cy={y} r="5" fill="#ffd1e6" /></g>)}
    </Art>
  ) },
];
const C2_LIP_ROCKS = rocks(71, [[120, 330, 150], [380, 360, 120], [640, 380, 90], [1260, 360, 110], [1500, 330, 160]]);
export const PROBLEM_LIP = { speed: -0.25, h: 26, art: (
  <LipArt h={420}>
    <path d="M-60 420 L-60 300 Q300 250 700 300 Q1100 340 1660 290 L1660 420 Z" fill="#0e0a2a" />
    <Rocks list={C2_LIP_ROCKS} lit="#7a63c4" side="#140f38" />
    <g className="w-sway">{[fern(81, 260, 400, 200, -1.4), fern(82, 900, 410, 170, -1.9), fern(83, 1380, 400, 220, -1.2)].map((d, i) => <path key={i} d={d} fill="#241f60" />)}</g>
  </LipArt>
) };

// ================= chapter 3: the pool at the foot of the falls =================
export const MATHS_LAYERS = [
  { speed: 0.45, art: <Art h={1100} top="#0e0a2a"><rect width="1600" height="1100" fill="url(#w-pool)" /><Rays x={800} y={-200} angles={[84, 90, 96]} len={1500} width={3} /></Art> },
  { speed: 0.3, art: (
    <Art h={1100}>
      <path d="M-40 -2000 L150 -2000 L170 1140 L-40 1140 Z" fill="#0b0824" /><path d="M150 -2000 L170 1140 L190 1140 L168 -2000 Z" fill="#3a3290" opacity="0.6" />
      <path d="M1440 -2000 L1640 -2000 L1640 1140 L1420 1140 Z" fill="#0b0824" /><path d="M1440 -2000 L1420 1140 L1402 1140 L1424 -2000 Z" fill="#3a3290" opacity="0.6" />
      <path d="M1180 -2000 L1260 -2000 L1270 1140 L1170 1140 Z" fill="#110d33" opacity="0.8" />
    </Art>
  ) },
  { speed: 0.12, art: (
    <Art h={1100}>
      <ellipse cx="800" cy="1010" rx="900" ry="150" fill="url(#w-water)" />
      <ellipse cx="800" cy="980" rx="420" ry="60" fill="url(#w-glowCyan)" className="w-breathe" />
      {Array.from({ length: 14 }, (_, i) => { const r = rng(120 + i), y = 930 + r() * 130, x = 120 + r() * 1300, w = 40 + r() * 140; return <line key={i} x1={x} x2={x + w} y1={y} y2={y} stroke="#bff6ff" strokeOpacity={0.2 + r() * 0.35} strokeWidth="2" strokeLinecap="round" className="w-glint" style={{ animationDelay: `${-r() * 4}s` }} />; })}
      {[[260, 940], [330, 960], [1300, 950], [1360, 930], [1240, 975]].map(([x, y], i) => (
        <g key={i} className="w-pulse" style={{ animationDelay: `${-i * 0.6}s` }}>
          <Glow cx={x} cy={y - 18} r={40} color="url(#w-glowCyan)" />
          <path d={`M${x - 16} ${y - 14} Q${x} ${y - 34} ${x + 16} ${y - 14} Z`} fill="#7ff0ff" opacity="0.85" /><rect x={x - 3} y={y - 15} width="6" height="18" fill="#bdf7ff" opacity="0.7" />
        </g>
      ))}
    </Art>
  ) },
  { speed: 0.02, art: <Fireflies n={20} seed={13} warm={false} top={20} height={70} /> },
];
export const MATHS_LIP = { speed: -0.22, h: 22, art: (
  <LipArt h={360}>
    <path d="M-60 360 L-60 250 Q240 200 520 260 Q800 300 1060 250 Q1350 200 1660 260 L1660 360 Z" fill="#0f0b2c" />
    <g className="w-sway"><path d={grass(91, { x0: -40, x1: 1640, base: 360, hMin: 50, hMax: 150, n: 260, lean: 0.3 })} fill="url(#w-grassMoon)" /></g>
  </LipArt>
) };

// ================= chapter 4: a moonlit path of five lanterns =================
const C4_LANTERNS = [[330, 900, 1], [600, 790, 0.82], [820, 700, 0.66], [960, 630, 0.52], [1060, 580, 0.42]];
export const HOW_LAYERS = [
  { speed: 0.55, art: <Art top="#0f0b2c"><rect width="1600" height="1000" fill="url(#w-night)" /><Stars list={stars(141, 110, 520)} /><Glow cx={1400} cy={470} r={220} color="url(#w-moon)" /><circle cx="1400" cy="470" r="44" fill="#f4efff" /></Art> },
  { speed: 0.42, art: <Art><path d={ridge(143, 560, 90, 8)} fill="#3a2f88" /><path d={pines(145, { base: 600, hMin: 50, hMax: 110, n: 60 })} fill="#2a2170" /></Art> },
  { speed: 0.25, art: (
    <Art>
      <path d={ridge(147, 640, 50, 6)} fill="#1f1858" />
      <path d="M180 1100 Q520 900 700 790 Q900 680 1000 620 Q1070 580 1100 560 L1130 560 Q1100 590 1040 640 Q930 720 780 820 Q600 940 520 1100 Z" fill="#4b3d9c" opacity="0.55" />
      {C4_LANTERNS.map(([x, y, s], i) => (
        <g key={i} className="w-pulse" style={{ animationDelay: `${-i * 0.5}s` }}>
          <Glow cx={x} cy={y - 70 * s} r={120 * s} />
          <rect x={x - 3 * s} y={y - 60 * s} width={6 * s} height={60 * s} fill="#1a1446" />
          <rect x={x - 14 * s} y={y - 92 * s} width={28 * s} height={34 * s} rx={6 * s} fill="#ffd27a" />
          <text x={x} y={y - 68 * s} textAnchor="middle" fontSize={20 * s} fontWeight="800" fill="#3a2010" fontFamily="Urbanist">{i + 1}</text>
        </g>
      ))}
    </Art>
  ) },
  { speed: 0.02, art: <Fireflies n={16} seed={17} top={40} height={50} /> },
  { speed: -0.15, art: <Art><g className="w-sway-2"><path d={grass(151, { x0: -40, x1: 1640, base: 1010, hMin: 60, hMax: 230, n: 300, lean: 0.35 })} fill="url(#w-grassMoon)" /></g></Art> },
];
export const HOW_LIP = { speed: -0.2, h: 18, art: (
  <LipArt h={290}><path d="M-60 290 L-60 200 Q400 150 800 210 Q1200 260 1660 190 L1660 290 Z" fill="#130e38" /><path d={pines(155, { base: 300, hMin: 120, hMax: 260, n: 14, x0: -60, x1: 260 })} fill="#130e38" /><path d={pines(156, { base: 300, hMin: 120, hMax: 260, n: 14, x0: 1340, x1: 1660 })} fill="#130e38" /></LipArt>
) };

// ================= chapter 5: a clearing under the moon =================
export const VERIFY_LAYERS = [
  { speed: 0.5, art: <Art top="#130e38"><rect width="1600" height="1000" fill="#130e38" /><Stars list={stars(161, 80, 600)} /><Glow cx={1290} cy={130} r={420} color="url(#w-moon)" /><circle cx="1290" cy="130" r="62" fill="#efe9ff" opacity="0.9" /></Art> },
  { speed: 0.35, art: <Art><path d={pines(163, { base: 760, hMin: 260, hMax: 560, n: 16, x0: -80, x1: 420 })} fill="#1d1652" /><path d={pines(164, { base: 760, hMin: 260, hMax: 560, n: 16, x0: 1180, x1: 1680 })} fill="#1d1652" /><path d={ridge(165, 780, 40, 6)} fill="#1a1446" /></Art> },
  { speed: 0.2, art: <Art><ellipse cx="800" cy="800" rx="900" ry="120" fill="url(#w-puff)" opacity="0.35" className="w-breathe" /></Art> },
  { speed: 0.02, art: <Fireflies n={14} seed={19} top={30} height={60} /> },
  { speed: -0.18, art: <Art><path d={pines(167, { base: 1100, hMin: 500, hMax: 900, n: 5, x0: -120, x1: 140 })} fill="#0c0826" /><path d={pines(168, { base: 1100, hMin: 500, hMax: 900, n: 5, x0: 1460, x1: 1720 })} fill="#0c0826" /></Art> },
];
export const VERIFY_LIP = { speed: -0.2, h: 18, art: (
  <LipArt h={290}><path d="M-60 290 L-60 210 Q500 160 900 220 Q1250 260 1660 200 L1660 290 Z" fill="#1a1446" /><ellipse cx="800" cy="215" rx="900" ry="40" fill="url(#w-puff)" opacity="0.35" /></LipArt>
) };

// ================= chapter 6: pre-dawn over an Indian city on the river =================
function skyline(seed) {
  const r = rng(seed);
  let d = "", win = "", x = -40;
  while (x < 1640) {
    const w = 26 + r() * 60, h = 30 + r() * 120 * (0.4 + Math.sin((x / 1600) * Math.PI) * 0.8), top = 760 - h;
    if (r() < 0.12) { // a dome or temple spire
      d += `M${r1(x)} 760 L${r1(x)} ${r1(top + 20)} Q${r1(x + w / 2)} ${r1(top - 30)} ${r1(x + w)} ${r1(top + 20)} L${r1(x + w)} 760Z`;
    } else d += `M${r1(x)} 760 V${r1(top)} H${r1(x + w)} V760Z`;
    for (let wy = top + 10; wy < 750; wy += 14) for (let wx = x + 5; wx < x + w - 6; wx += 10) if (r() < 0.16) win += `M${r1(wx)} ${r1(wy)}h4v6h-4Z`;
    x += w + r() * 6;
  }
  return { d, win };
}
const CITY = skyline(171);
export const INDIA_LAYERS = [
  { speed: 0.5, art: <Art top="#1a1446"><rect width="1600" height="1000" fill="url(#w-predawn)" /><Stars list={stars(173, 60, 300)} /></Art> },
  { speed: 0.36, art: <Art><path d={ridge(175, 700, 90, 7)} fill="#5a3f98" opacity="0.6" /><path d={CITY.d} fill="#2a1f66" /><path d={CITY.win} fill="#ffd27a" className="w-twinkle-slow" /></Art> },
  { speed: 0.2, art: (
    <Art>
      <rect x="0" y="760" width="1600" height="300" fill="url(#w-river)" />
      {Array.from({ length: 18 }, (_, i) => { const r = rng(180 + i), y = 775 + r() * 200, x = r() * 1500, w = 30 + r() * 150; return <line key={i} x1={x} x2={x + w} y1={y} y2={y} stroke="#ffd9c4" strokeOpacity={0.2 + r() * 0.4} strokeWidth="2" strokeLinecap="round" className="w-glint" style={{ animationDelay: `${-r() * 4}s` }} />; })}
      {[[260, 860], [620, 900], [980, 870], [1320, 910]].map(([x, y], i) => <g key={i} className="w-pulse" style={{ animationDelay: `${-i}s` }}><Glow cx={x} cy={y} r={36} /><path d={`M${x - 10} ${y + 4} Q${x} ${y - 14} ${x + 10} ${y + 4} Z`} fill="#ffcf7a" /></g>)}
    </Art>
  ) },
  { speed: -0.15, art: <Art><path d="M-120 1100 L-120 900 Q200 860 420 930 L520 1100 Z" fill="#1a1446" /><path d="M1720 1100 L1720 880 Q1400 850 1200 940 L1120 1100 Z" fill="#1a1446" /><g className="w-sway"><path d={grass(185, { x0: -60, x1: 460, base: 1010, hMin: 60, hMax: 180, n: 80 })} fill="url(#w-grassLit)" /><path d={grass(186, { x0: 1160, x1: 1660, base: 1010, hMin: 60, hMax: 180, n: 80 })} fill="url(#w-grassLit)" /></g></Art> },
];
export const INDIA_LIP = { speed: -0.2, h: 16, art: <LipArt h={260}><path d="M-60 260 L-60 190 Q400 150 800 200 Q1200 240 1660 180 L1660 260 Z" fill="#1e1850" /></LipArt> };

// ================= chapter 7: dawn =================
export const DAWN_LAYERS = [
  { speed: 0.5, art: <Art top="#1e1850"><rect width="1600" height="1000" fill="url(#w-dawn)" /><Glow cx={800} cy={760} r={560} color="url(#w-sun)" /><circle cx="800" cy="760" r="90" fill="#fff4dc" /></Art> },
  { speed: 0.4, art: <Art><g className="w-drift">{[[300, 520, 160], [520, 560, 120], [1150, 500, 170], [1350, 540, 130]].map(([cx, cy, rx], i) => <ellipse key={i} cx={cx} cy={cy} rx={rx} ry={rx * 0.36} fill="url(#w-puffWarm)" />)}</g><Birds y={420} n={9} seed={9} /></Art> },
  { speed: 0.3, art: <Art><path d={ridge(191, 760, 160, 7)} fill="#b2689f" opacity="0.7" /><path d={ridge(193, 820, 120, 8)} fill="#7a4fa6" opacity="0.85" /></Art> },
  { speed: 0.15, art: <Art><path d={ridge(195, 900, 100, 6)} fill="#4a3586" /><path d={ridge(197, 980, 60, 5)} fill="#2a1f66" /></Art> },
];
