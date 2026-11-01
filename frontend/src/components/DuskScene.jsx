import { motion, useAnimationFrame, useMotionValue, useReducedMotion, useScroll, useSpring, useTransform } from "framer-motion";
import { useEffect, useRef, useState } from "react";

// An illustrated dusk canyon: a river runs to a waterfall between two lit city banks, low-poly
// mountains and cloud banks behind. The city is real one-point perspective (every building is
// projected from 3D), and the scene is split into depth planes that drift with the pointer and
// fly forward as the page scrolls. Each plane is its own composited layer, so motion stays smooth.
// `alert` (0..1) turns the windows red.

const W = 1600, H = 900, VX = 800, VY = 520; // canvas and vanishing point (horizon)
const F = 900, GY = 1.1, B = GY + 0.6;       // focal length, ground below eye level, building feet
const BLEED = 6;                              // % each plane overhangs the frame, so parallax never shows an edge

function rng(seed) { // mulberry32: the same scene on every render
  let a = seed >>> 0;
  return () => { a = (a + 0x6d2b79f5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
const P = (X, Y, z) => [VX + (X * F) / z, VY + (Y * F) / z];
const lerp = (a, b, t) => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t];
const r1 = (n) => Math.round(n * 10) / 10;
const poly = (...ps) => "M" + ps.map(([x, y]) => `${r1(x)} ${r1(y)}`).join("L") + "Z";

// ---------- mountains: a silhouette in the shadow colour, a lit facet and a ridge sliver per peak ----------
function range(seed, { n, top, bottom, base, dip = 0, snowAbove = 1e9 }) {
  const r = rng(seed), peaks = [], valleys = [];
  for (let i = 0; i <= n; i++) {
    const x = -160 + i * (1920 / n) + (r() - 0.5) * 70;
    peaks.push([x, dip && Math.abs(x - VX) < dip ? base - 40 - r() * 30 : top + r() * (bottom - top)]);
  }
  for (let i = 0; i < n; i++) {
    const [a, b] = [peaks[i], peaks[i + 1]], low = Math.max(a[1], b[1]);
    valleys.push([a[0] + (b[0] - a[0]) * (0.35 + r() * 0.3), low + (base - low) * (0.3 + r() * 0.35)]);
  }
  const outline = [[-220, base + 140]];
  peaks.forEach((p, i) => { outline.push(p); if (valleys[i]) outline.push(valleys[i]); });
  outline.push([1820, base + 140]);
  const facets = peaks.map((p, i) => {
    const L = valleys[i - 1] || [p[0] - 240, base], R = valleys[i] || [p[0] + 240, base];
    const foot = [p[0] + (R[0] - p[0]) * 0.3, base + 30], h = base - p[1];
    return {
      lit: poly(L, p, foot),
      sliver: poly(p, lerp(p, L, 0.5), lerp(p, foot, 0.3)),
      snow: h > snowAbove ? poly(p, lerp(p, L, 0.22), [p[0] - (p[0] - L[0]) * 0.07, p[1] + h * 0.2], lerp(p, foot, 0.16)) : null,
    };
  });
  return { outline: poly(...outline), facets };
}
const FAR = range(3, { n: 9, top: 140, bottom: 290, base: VY + 20, snowAbove: 250 });
const MID = range(11, { n: 8, top: 260, bottom: 380, base: VY + 30, snowAbove: 200 });
const NEAR = range(19, { n: 7, top: 365, bottom: 450, base: VY + 40, dip: 170 });

function puffs(seed, n, y0, y1, size) {
  const r = rng(seed);
  return Array.from({ length: n }, () => { const rx = size * (0.6 + r() * 0.9); return { cx: -120 + r() * 1840, cy: y0 + r() * (y1 - y0), rx, ry: rx * 0.42 }; });
}
const CLOUDS_BACK = puffs(5, 26, 280, 360, 150);
const CLOUDS_MID = [...puffs(9, 22, 420, 480, 170), ...puffs(13, 8, 455, 500, 120).map((p) => ({ ...p, cx: VX - 260 + (p.cx / 1600) * 520 }))];

// ---------- city: buildings on both banks, walls, windows and lamps, sorted into three depth bands ----------
function cityBands() {
  const r = rng(7);
  const band = () => ({ walls: [], win: { dark: "", a: "", b: "", c: "" }, lamps: [] });
  const bands = { far: band(), mid: band(), near: band() };
  const pick = (z) => bands[z < 5.2 ? "near" : z < 10 ? "mid" : "far"];
  const blds = [];
  for (const s of [-1, 1]) {
    let z = 3.0 + r() * 0.5;
    while (z < 24) {
      const d = 0.8 + r() * 1.5, xi = s * (2.1 + r() * 0.5), w = 0.9 + r() * 1.7;
      const ht = 1.0 + r() * 2.1 + (z < 7 ? 0.6 : 0);
      blds.push({ s, z0: z, z1: z + d, xi, xo: xi + s * w, top: GY - ht, ht, w, d });
      z += d + 0.15 + r() * 0.55;
    }
  }
  blds.sort((a, b) => b.z0 - a.z0); // paint far ones first
  blds.forEach((b, i) => {
    const bd = pick(b.z0);
    const inner = poly(P(b.xi, B, b.z0), P(b.xi, B, b.z1), P(b.xi, b.top, b.z1), P(b.xi, b.top, b.z0));
    const [fx0] = P(Math.min(b.xo, b.xi), 0, b.z0), [fx1] = P(Math.max(b.xo, b.xi), 0, b.z0);
    const [, fy0] = P(0, b.top, b.z0), [, fy1] = P(0, B, b.z0);
    const ant = r() < 0.35 ? poly([(fx0 + fx1) / 2 - 1, fy0], [(fx0 + fx1) / 2 + 1, fy0], [(fx0 + fx1) / 2, fy0 - (0.5 * F) / b.z0]) : null;
    bd.walls.push({ key: i, s: b.s, inner, front: { x: fx0, y: fy0, w: fx1 - fx0, h: fy1 - fy0 }, rim: poly(P(b.xi, b.top, b.z0), P(b.xi, b.top, b.z1), P(b.xi, b.top + 0.04, b.z1), P(b.xi, b.top + 0.04, b.z0)), haze: Math.min(0.72, Math.max(0, (b.z0 - 4) / 20)), ant });

    const add = (d) => { const k = r(); if (k < 0.22) return; bd.win[k < 0.6 ? "dark" : k < 0.84 ? "a" : k < 0.95 ? "b" : "c"] += d; };
    const rows = Math.floor((b.ht - 0.3) / 0.25);
    const fcols = Math.max(1, Math.floor(b.w / 0.2)), cw = b.w / fcols, xa = Math.min(b.xo, b.xi);
    if ((cw * 0.42 * F) / b.z0 > 1.5) for (let row = 0; row < rows; row++) for (let c = 0; c < fcols; c++) {
      const wx = xa + c * cw + cw * 0.29, wy = b.top + 0.2 + row * 0.25;
      const [x0, y0] = P(wx, wy, b.z0), [x1, y1] = P(wx + cw * 0.42, wy + 0.12, b.z0);
      add(`M${r1(x0)} ${r1(y0)}H${r1(x1)}V${r1(y1)}H${r1(x0)}Z`);
    }
    const icols = Math.max(1, Math.floor(b.d / 0.24)), cz = b.d / icols;
    for (let row = 0; row < rows; row++) for (let c = 0; c < icols; c++) {
      const za = b.z0 + c * cz + cz * 0.25, zb = za + cz * 0.45, wy = b.top + 0.2 + row * 0.25;
      if (Math.abs(P(b.xi, wy, za)[0] - P(b.xi, wy, zb)[0]) < 1.2) continue;
      add(poly(P(b.xi, wy, za), P(b.xi, wy, zb), P(b.xi, wy + 0.12, zb), P(b.xi, wy + 0.12, za)));
    }
  });
  for (const s of [-1, 1]) for (let z = 2.6; z < 22; z += 1.3) {
    const X = s * 1.65, head = P(X, GY - 0.55, z), foot = P(X, GY, z), u = F / z;
    pick(z).lamps.push({ key: `${s}${z}`, head, foot, u, cone: poly(head, P(X - 0.35, GY, z), P(X + 0.35, GY, z)) });
  }
  return bands;
}
const CITY = cityBands();

// ---------- ground: banks, river, reflections, shimmer ----------
const RW = 1.35; // river half-width
const RIVER = poly(P(-RW, GY, 90), P(RW, GY, 90), P(RW, GY, 1.4), P(-RW, GY, 1.4));
const BANKS = [-1, 1].map((s) => poly(P(s * RW, GY, 90), P(s * 9, GY, 90), P(s * 9, GY, 1.4), P(s * RW, GY, 1.4)));
const EDGES = [-1, 1].map((s) => poly(P(s * RW, GY, 60), P(s * RW, GY, 1.5), P(s * (RW + 0.05), GY, 1.5), P(s * (RW + 0.05), GY, 60)));
const RAILS = [-1, 1].map((s) => poly(P(s * 1.5, GY - 0.3, 40), P(s * 1.5, GY - 0.3, 1.8), P(s * 1.5, GY - 0.27, 1.8), P(s * 1.5, GY - 0.27, 40)));
const GLINTS = Array.from({ length: 70 }, (_, i) => {
  const r = rng(500 + i), z = 2.3 + Math.pow(r(), 1.8) * 22, X = (r() * 2 - 1) * (RW - 0.15), len = 0.12 + r() * 0.35;
  const [x0, y] = P(X - len / 2, GY, z), [x1] = P(X + len / 2, GY, z);
  return { x0, x1, y, w: Math.max(0.7, (0.022 * F) / z), dur: 2 + r() * 3, delay: -r() * 5 };
});
const WALL_REFL = [-1, 1].map((s) => poly(P(s * (RW - 0.55), GY, 60), P(s * RW, GY, 60), P(s * RW, GY, 1.4), P(s * (RW - 0.55), GY, 1.4)));
const REFLECT = [-1, 1].flatMap((s) => Array.from({ length: 12 }, (_, i) => { const z = 2.6 + i * 1.3, [x, y] = P(s * (RW - 0.12), GY, z), u = F / z; return { key: `${s}${i}`, x, y: y + u * 0.3, rx: u * 0.045, ry: u * 0.32 }; }));

// ---------- foreground rocks, faceted ----------
const ROCKS = [[-1.2, 2.45, 0.6], [-0.75, 2.85, 0.32], [-1.55, 3.3, 0.45], [-0.38, 2.3, 0.26], [1.1, 2.4, 0.62], [0.68, 2.95, 0.3], [1.5, 3.5, 0.42], [0.28, 2.6, 0.2], [-2.0, 2.2, 0.75], [2.05, 2.2, 0.8]].map(([X, z, sz], i) => {
  const r = rng(40 + i), [cx, cy] = P(X, GY - sz * 0.22, z), rx = (sz * F) / z / 2, ry = rx * 0.62;
  const ring = Array.from({ length: 8 }, (_, k) => { const a = Math.PI + (k / 7) * Math.PI, m = 0.8 + r() * 0.35; return [cx + Math.cos(a) * rx * m, cy - Math.sin(a) * ry * m * (k === 0 || k === 7 ? 0.2 : 1)]; });
  const peak = [cx - rx * (0.1 + r() * 0.3), cy - ry * (0.85 + r() * 0.2)];
  const outline = poly([cx - rx * 1.05, cy + ry * 0.5], ...ring.slice(1, 4), peak, ...ring.slice(4, 7), [cx + rx * 1.05, cy + ry * 0.5]);
  const facets = ring.slice(1, 7).map((p, k) => ({ d: poly(peak, p, ring[k + 2] || [cx + rx, cy + ry * 0.5]), lit: p[0] < peak[0] }));
  return { key: i, outline, facets, foam: { cx, cy: cy + ry * 0.55, rx: rx * 1.25, ry: ry * 0.22 } };
});

const STARS = Array.from({ length: 46 }, (_, i) => { const r = rng(200 + i); return { cx: r() * W, cy: r() * 330, r: 0.6 + r() * 1.3, o: 0.25 + r() * 0.6 }; });
const RAYS = Array.from({ length: 11 }, (_, i) => { const a = ((-75 + i * 15 + (i % 2) * 4) * Math.PI) / 180, w = ((1.5 + (i % 3)) * Math.PI) / 180, R = 1300, o = [VX, VY - 50]; return poly(o, [o[0] + Math.sin(a - w) * R, o[1] - Math.cos(a - w) * R], [o[0] + Math.sin(a + w) * R, o[1] - Math.cos(a + w) * R]); });
const MOTES = Array.from({ length: 30 }, (_, i) => { const r = rng(300 + i); return { left: r() * 100, top: 30 + r() * 65, size: 2 + r() * 4, dur: 9 + r() * 11, delay: -r() * 18, o: 0.35 + r() * 0.55 }; });

function Svg({ children, className = "" }) {
  return <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="xMidYMax slice" className={`absolute inset-0 size-full ${className}`}>{children}</svg>;
}

function Plane({ depth, zoom, cam, origin, fade = 0, children }) {
  const x = useTransform(cam.x, (v) => -v * depth * 70);
  const y = useTransform(cam.y, (v) => -v * depth * 30);
  const scale = useTransform(cam.z, (v) => 1 + v * zoom);
  const opacity = useTransform(cam.z, (v) => 1 - v * fade);
  return <motion.div className="absolute will-change-transform" style={{ inset: `-${BLEED}%`, x, y, scale, opacity, transformOrigin: origin }}>{children}</motion.div>;
}

function CityBand({ band }) {
  return (
    <Svg>
      {band.walls.map((w) => (
        <g key={w.key}>
          <path d={w.inner} fill={w.s < 0 ? "url(#ds-wallL)" : "url(#ds-wallR)"} />
          <path d={w.inner} fill="url(#ds-wallTop)" />
          <rect x={w.front.x} y={w.front.y} width={w.front.w} height={w.front.h} fill="url(#ds-front)" />
          <path d={w.rim} fill="#ffcfa3" opacity="0.85" />
          {w.ant && <path d={w.ant} fill="#2a1d5c" />}
          {w.haze > 0 && <><path d={w.inner} fill="#e9c6db" opacity={w.haze} /><rect x={w.front.x} y={w.front.y} width={w.front.w} height={w.front.h} fill="#e9c6db" opacity={w.haze} /></>}
        </g>
      ))}
      <path d={band.win.dark} fill="#2b2068" opacity="0.6" />
      <g style={{ fill: "var(--ds-lit)", transition: "fill 0.7s" }}>
        <path d={band.win.a} opacity="0.95" />
        <path d={band.win.c} opacity="0.5" />
      </g>
      <path d={band.win.b} fill="#fff1d9" opacity="0.85" />
      {band.lamps.map((l) => (
        <g key={l.key}>
          <path d={l.cone} fill="url(#ds-cone)" />
          <line x1={l.foot[0]} y1={l.foot[1]} x2={l.head[0]} y2={l.head[1]} stroke="#2a1d5c" strokeWidth={Math.max(1, l.u * 0.022)} />
          <circle cx={l.head[0]} cy={l.head[1]} r={l.u * 0.16} fill="url(#ds-glow)" />
          <circle cx={l.head[0]} cy={l.head[1]} r={Math.max(1, l.u * 0.025)} fill="#fff6e0" />
        </g>
      ))}
    </Svg>
  );
}

function Range({ r, shadow, lit, sliver, snow }) {
  return (
    <>
      <path d={r.outline} fill={shadow} />
      {r.facets.map((f, i) => (
        <g key={i}>
          <path d={f.lit} fill={lit} />
          <path d={f.sliver} fill={sliver} opacity="0.55" />
          {f.snow && <path d={f.snow} fill={snow} opacity="0.9" />}
        </g>
      ))}
    </>
  );
}

export default function DuskScene({ onPhase, alert = 0, className = "" }) {
  const reduced = useReducedMotion();
  const root = useRef(null);
  const [origin, setOrigin] = useState("50% 60%");

  // camera: pointer, a slow idle sway (so it is alive on phones and projectors), and scroll as a dolly forward
  const mx = useMotionValue(0), my = useMotionValue(0), sx = useMotionValue(0), sy = useMotionValue(0);
  const px = useSpring(mx, { stiffness: 35, damping: 20 }), py = useSpring(my, { stiffness: 35, damping: 20 });
  const { scrollY } = useScroll();
  const zp = useSpring(useTransform(scrollY, [0, 900], [0, 1], { clamp: true }), { stiffness: 60, damping: 22 });
  const cam = { x: useTransform([px, sx], ([a, b]) => a + b), y: useTransform([py, sy], ([a, b]) => a + b), z: zp };
  const still = useMotionValue(0);

  useAnimationFrame((t) => {
    if (reduced) return;
    sx.set(Math.sin(t / 5200) * 0.22);
    sy.set(Math.cos(t / 7300) * 0.12);
  });

  useEffect(() => {
    if (reduced) return;
    const move = (e) => { mx.set(e.clientX / window.innerWidth - 0.5); my.set(e.clientY / window.innerHeight - 0.5); };
    window.addEventListener("pointermove", move);
    return () => window.removeEventListener("pointermove", move);
  }, [reduced, mx, my]);

  // zoom about the vanishing point, wherever xMidYMax slice puts it at this size
  useEffect(() => {
    const el = root.current;
    if (!el) return;
    const ro = new ResizeObserver(([e]) => {
      const w = e.contentRect.width * (1 + BLEED / 50), h = e.contentRect.height * (1 + BLEED / 50), s = Math.max(w / W, h / H);
      setOrigin(`${r1(w / 2)}px ${r1(h - (H - VY) * s)}px`);
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

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

  const k = { cam: reduced ? { x: still, y: still, z: still } : cam, origin };

  return (
    <div ref={root} className={className} style={{ overflow: "hidden", "--ds-lit": alert > 0.3 ? "#ff6b8f" : "#ffd27a" }} aria-hidden>
      <Plane depth={0} zoom={0} {...k}>
        <Svg>
          <defs>
            <linearGradient id="ds-sky" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0" stopColor="#6f68c9" /><stop offset="0.3" stopColor="#9d90dc" /><stop offset="0.48" stopColor="#d9addb" />
              <stop offset="0.58" stopColor="#ffc9ad" /><stop offset="1" stopColor="#f6b9b4" />
            </linearGradient>
            <radialGradient id="ds-sun" cx="0.5" cy="0.5" r="0.5">
              <stop offset="0" stopColor="#fff6e6" stopOpacity="1" /><stop offset="0.25" stopColor="#ffdcbc" stopOpacity="0.7" /><stop offset="1" stopColor="#ffb8a8" stopOpacity="0" />
            </radialGradient>
            <radialGradient id="ds-ray" cx={VX} cy={VY - 50} r="1200" gradientUnits="userSpaceOnUse">
              <stop offset="0" stopColor="#fff4e4" stopOpacity="0.3" /><stop offset="1" stopColor="#fff4e4" stopOpacity="0" />
            </radialGradient>
            <radialGradient id="ds-puff" cx="0.5" cy="0.5" r="0.5">
              <stop offset="0" stopColor="#fffafa" stopOpacity="0.95" /><stop offset="0.55" stopColor="#ffe3ea" stopOpacity="0.55" /><stop offset="1" stopColor="#f4c6d8" stopOpacity="0" />
            </radialGradient>
            <linearGradient id="ds-farLit" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#f6dcea" /><stop offset="1" stopColor="#e4c6e2" /></linearGradient>
            <linearGradient id="ds-midLit" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#dcb3dd" /><stop offset="1" stopColor="#b796d4" /></linearGradient>
            <linearGradient id="ds-nearLit" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#ad84c9" /><stop offset="1" stopColor="#7f64b8" /></linearGradient>
            <linearGradient id="ds-mist" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0" stopColor="#ffe2d6" stopOpacity="0" /><stop offset="0.6" stopColor="#ffe2d6" stopOpacity="0.85" /><stop offset="1" stopColor="#ffe2d6" stopOpacity="0" />
            </linearGradient>
            <linearGradient id="ds-fall" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#ffffff" stopOpacity="0.35" /><stop offset="1" stopColor="#ffffff" stopOpacity="0.95" /></linearGradient>
            <linearGradient id="ds-river" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0" stopColor="#fff2e6" /><stop offset="0.08" stopColor="#f3d0e0" /><stop offset="0.35" stopColor="#a99be6" /><stop offset="1" stopColor="#3f3593" />
            </linearGradient>
            <linearGradient id="ds-bank" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#8b6fb8" /><stop offset="0.3" stopColor="#4a3786" /><stop offset="1" stopColor="#24194f" /></linearGradient>
            <linearGradient id="ds-wallL" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stopColor="#3b2a7c" /><stop offset="1" stopColor="#b8608f" /></linearGradient>
            <linearGradient id="ds-wallR" x1="1" y1="0" x2="0" y2="0"><stop offset="0" stopColor="#3b2a7c" /><stop offset="1" stopColor="#b8608f" /></linearGradient>
            <linearGradient id="ds-wallTop" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0" stopColor="#ffb27a" stopOpacity="0.75" /><stop offset="0.45" stopColor="#ff8fa3" stopOpacity="0.18" /><stop offset="1" stopColor="#ff8fa3" stopOpacity="0" />
            </linearGradient>
            <linearGradient id="ds-front" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#30216a" /><stop offset="1" stopColor="#170f37" /></linearGradient>
            <linearGradient id="ds-cone" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#ffd59a" stopOpacity="0.5" /><stop offset="1" stopColor="#ffd59a" stopOpacity="0" /></linearGradient>
            <radialGradient id="ds-glow" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stopColor="#ffe4b0" stopOpacity="0.95" /><stop offset="1" stopColor="#ffb878" stopOpacity="0" /></radialGradient>
            <linearGradient id="ds-refl" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#ffd59a" stopOpacity="0.6" /><stop offset="1" stopColor="#ffd59a" stopOpacity="0" /></linearGradient>
            <linearGradient id="ds-rock" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#7d5fae" /><stop offset="1" stopColor="#2a1d5c" /></linearGradient>
          </defs>
          <rect width={W} height={H} fill="url(#ds-sky)" />
          {STARS.map((s, i) => <circle key={i} cx={s.cx} cy={s.cy} r={s.r} fill="#ffffff" opacity={s.o} />)}
          <circle cx={VX} cy={VY - 50} r="520" fill="url(#ds-sun)" />
          <circle cx={VX} cy={VY - 50} r="58" fill="#fff6e8" opacity="0.95" />
        </Svg>
      </Plane>

      <Plane depth={0.04} zoom={0.02} {...k}>
        <Svg><g className={reduced ? "" : "ds-rays"} style={{ mixBlendMode: "screen" }}>{RAYS.map((d, i) => <path key={i} d={d} fill="url(#ds-ray)" />)}</g></Svg>
      </Plane>

      <Plane depth={0.08} zoom={0.04} {...k}>
        <Svg><Range r={FAR} shadow="#c6b4e4" lit="url(#ds-farLit)" sliver="#fff0f4" snow="#fffafc" /></Svg>
      </Plane>

      <Plane depth={0.14} zoom={0.07} {...k}>
        <Svg className={reduced ? "" : "ds-drift will-change-transform"}>{CLOUDS_BACK.map((c, i) => <ellipse key={i} {...c} fill="url(#ds-puff)" />)}</Svg>
      </Plane>

      <Plane depth={0.2} zoom={0.1} {...k}>
        <Svg>
          <Range r={MID} shadow="#977fcc" lit="url(#ds-midLit)" sliver="#f6d4e6" snow="#fdf0f6" />
          <path d={`M${VX - 7} 400 L${VX + 7} 400 L${VX + 16} ${VY + 10} L${VX - 16} ${VY + 10} Z`} fill="url(#ds-fall)" />
        </Svg>
      </Plane>

      <Plane depth={0.28} zoom={0.16} {...k}>
        <Svg className={reduced ? "" : "ds-drift-r will-change-transform"}>{CLOUDS_MID.map((c, i) => <ellipse key={i} {...c} fill="url(#ds-puff)" />)}</Svg>
      </Plane>

      <Plane depth={0.36} zoom={0.2} {...k}>
        <Svg>
          <Range r={NEAR} shadow="#6c56ab" lit="url(#ds-nearLit)" sliver="#c9a3d8" snow="none" />
          {[[-60, 0, 110], [40, 8, 90], [0, -10, 70]].map(([dx, dy, rx], i) => <ellipse key={i} cx={VX + dx} cy={VY - 14 + dy} rx={rx} ry={rx * 0.38} fill="url(#ds-puff)" />)}
        </Svg>
      </Plane>

      <Plane depth={0.5} zoom={0.35} {...k}>
        <Svg>
          {BANKS.map((d, i) => <path key={i} d={d} fill="url(#ds-bank)" />)}
          <path d={RIVER} fill="url(#ds-river)" />
          <ellipse cx={VX} cy={VY + 40} rx="70" ry="110" fill="url(#ds-glow)" opacity="0.7" />
          {WALL_REFL.map((d, i) => <path key={i} d={d} fill="#2e2170" opacity="0.32" />)}
          {REFLECT.map((r) => <ellipse key={r.key} cx={r.x} cy={r.y} rx={r.rx} ry={r.ry} fill="url(#ds-refl)" />)}
          {GLINTS.map((g, i) => (
            <line key={i} x1={g.x0} x2={g.x1} y1={g.y} y2={g.y} stroke="#fffaf2" strokeWidth={g.w} strokeLinecap="round"
              className={reduced ? "" : "ds-glint"} opacity={reduced ? 0.5 : undefined} style={{ animationDuration: `${g.dur}s`, animationDelay: `${g.delay}s` }} />
          ))}
          {EDGES.map((d, i) => <path key={i} d={d} fill="#ffd9c4" opacity="0.6" />)}
          {RAILS.map((d, i) => <path key={i} d={d} fill="#2a1d5c" opacity="0.7" />)}
          <rect x="0" y={VY - 70} width={W} height="110" fill="url(#ds-mist)" />
        </Svg>
      </Plane>

      <Plane depth={0.5} zoom={0.3} {...k}><CityBand band={CITY.far} /></Plane>
      <Plane depth={0.7} zoom={0.5} {...k}><CityBand band={CITY.mid} /></Plane>
      <Plane depth={0.95} zoom={0.8} fade={0.3} {...k}><CityBand band={CITY.near} /></Plane>

      <Plane depth={1.3} zoom={1.2} fade={0.6} {...k}>
        <Svg>
          {ROCKS.map((r) => (
            <g key={r.key}>
              <ellipse {...r.foam} fill="#ffffff" opacity="0.35" />
              <path d={r.outline} fill="url(#ds-rock)" />
              {r.facets.map((f, i) => <path key={i} d={f.d} fill={f.lit ? "#e3b0d4" : "#1d1446"} opacity={f.lit ? 0.45 : 0.3} />)}
            </g>
          ))}
        </Svg>
      </Plane>

      {!reduced && (
        <Plane depth={1.6} zoom={1.4} fade={0.8} {...k}>
          {MOTES.map((m, i) => (
            <span key={i} className="ds-mote absolute rounded-full" style={{ left: `${m.left}%`, top: `${m.top}%`, width: m.size, height: m.size, "--o": m.o, animationDuration: `${m.dur}s`, animationDelay: `${m.delay}s`,
              background: "radial-gradient(circle, #fffaf0 0%, #ffd2a0 55%, transparent 72%)", boxShadow: "0 0 10px 2px rgb(255 205 160 / 0.55)" }} />
          ))}
        </Plane>
      )}

      <div className="absolute inset-0" style={{ background: "#ff2d6f", opacity: alert * 0.18, transition: "opacity 0.7s" }} />
    </div>
  );
}
