import { motion, useMotionValue, useReducedMotion, useSpring, useTransform } from "framer-motion";
import { useRef } from "react";
import Icon from "./Icons.jsx";

// Mac-style dock: fixed at the bottom of every page, icons magnify towards the pointer.
const ITEMS = [
  ["home", "Home", "#/", "home"],
  ["check", "Check a message", "#/app/check", "check"],
  ["live", "Live call", "#/app/live", "live"],
  ["cases", "Security queue", "#/app/cases", "queue"],
  ["people", "Trust Graph", "#/app/people", "people"],
];

function Item({ mouseX, label, href, icon, active, still }) {
  const ref = useRef(null);
  const dist = useTransform(mouseX, (x) => {
    const b = ref.current?.getBoundingClientRect();
    return b ? x - b.x - b.width / 2 : Infinity;
  });
  const size = useSpring(useTransform(dist, [-150, 0, 150], [50, still ? 50 : 78, 50]), { stiffness: 320, damping: 24, mass: 0.3 });
  return (
    <a ref={ref} href={href} aria-label={label} aria-current={active ? "page" : undefined} className="group relative flex flex-col items-center outline-none">
      <span className="pointer-events-none absolute -top-11 glass-strong rounded-full px-3 py-1 text-xs font-bold whitespace-nowrap opacity-0 translate-y-1 transition group-hover:opacity-100 group-hover:translate-y-0 group-focus-visible:opacity-100 group-focus-visible:translate-y-0">{label}</span>
      <motion.span style={{ width: size, height: size }}
        className={`orb shadow-[0_10px_25px_-12px_rgb(35_22_94/0.6)] group-focus-visible:ring-4 group-focus-visible:ring-night/40 ${active ? "bg-night text-white" : "bg-white/85 text-ink"}`}>
        <Icon name={icon} className="size-[44%]" />
      </motion.span>
      <span className={`mt-1 size-1.5 rounded-full ${active ? "bg-night" : "bg-transparent"}`} />
    </a>
  );
}

export default function Dock({ current }) {
  const mouseX = useMotionValue(Infinity);
  const still = useReducedMotion();
  return (
    <nav aria-label="Pages" className="fixed z-50 bottom-3 left-1/2 -translate-x-1/2">
      <div onMouseMove={(e) => mouseX.set(e.clientX)} onMouseLeave={() => mouseX.set(Infinity)}
        className="flex items-end gap-2.5 sm:gap-3 rounded-[1.75rem] px-3 pt-2.5 pb-1 h-[4.6rem] bg-white/60 backdrop-blur-2xl border border-white shadow-[0_25px_60px_-20px_rgb(35_22_94/0.55),inset_0_1px_0_rgb(255_255_255/0.9)]">
        {ITEMS.map(([key, label, href, icon], i) => (
          <div key={key} className="flex items-end gap-2.5 sm:gap-3">
            {i === 1 && <span className="self-center w-px h-9 bg-ink/15 mb-1.5" aria-hidden />}
            <Item mouseX={mouseX} label={label} href={href} icon={icon} active={current === key} still={still} />
          </div>
        ))}
      </div>
    </nav>
  );
}
