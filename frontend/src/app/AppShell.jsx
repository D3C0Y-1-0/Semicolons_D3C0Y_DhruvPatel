import { motion, useReducedMotion } from "framer-motion";
import { useEffect, useState } from "react";
import Dock from "../components/Dock.jsx";
import Icon from "../components/Icons.jsx";
import { api } from "../lib/api.js";
import Cases from "./Cases.jsx";
import Check from "./Check.jsx";
import Live from "./Live.jsx";
import People from "./People.jsx";

export const PAGES = {
  check: ["Check a message", Check, "check"],
  live: ["Live call", Live, "live"],
  cases: ["Security queue", Cases, "queue"],
  people: ["Trust Graph", People, "people"],
};
const KEYS = Object.keys(PAGES);
const mod = typeof navigator !== "undefined" && /Mac|iPhone|iPad/.test(navigator.platform) ? "⌘" : "Ctrl ";

function Clock() {
  const [now, setNow] = useState(new Date());
  useEffect(() => { const t = setInterval(() => setNow(new Date()), 15000); return () => clearInterval(t); }, []);
  return <span className="tnum">{now.toLocaleDateString([], { weekday: "short", day: "numeric", month: "short" })}&nbsp;&nbsp;{now.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}</span>;
}

const Dot = ({ on }) => <span className={`size-2 rounded-full ${on ? "bg-[#28c840]" : on === false ? "bg-high" : "bg-ink-soft/30"}`} />;

// The console is one macOS-style app window on the dusk wallpaper: menu bar, traffic lights, sidebar, content pane.
export default function AppShell({ page }) {
  const [health, setHealth] = useState(null);
  const [stats, setStats] = useState(null);
  const still = useReducedMotion();
  useEffect(() => {
    const ping = () => {
      api("/health").then(setHealth).catch(() => setHealth(false));
      api("/stats").then(setStats).catch(() => {});
    };
    ping();
    const t = setInterval(ping, 10000);
    return () => clearInterval(t);
  }, []);
  useEffect(() => { // Ctrl/Cmd + 1..4 switches pages, like a Mac app's sidebar
    const on = (e) => {
      const i = Number(e.key) - 1;
      if ((e.metaKey || e.ctrlKey) && i >= 0 && i < KEYS.length) { e.preventDefault(); location.hash = `#/app/${KEYS[i]}`; }
    };
    addEventListener("keydown", on);
    return () => removeEventListener("keydown", on);
  }, []);

  const [title, Page] = PAGES[page] || PAGES.check;
  const open = stats?.status?.open ?? 0;
  const highOpen = Math.min(stats?.bands?.HIGH ?? 0, open + (stats?.status?.verifying ?? 0));
  const status = [
    ["Backend", health ? true : health === false ? false : null, health ? "online" : health === false ? "offline" : "…"],
    ["Models", health ? (health.models === "ready" ? true : null) : null, health?.models === "ready" ? "ready" : health?.models === "warming" ? "warming up…" : health ? "load on first use" : "…"],
    ["Email", health ? !!health.email : null, health?.email ? "sends itself" : "off"],
    ["Telegram", health ? !!health.telegram : null, health?.telegram ? "on" : "off"],
  ];

  return (
    <div className="mac wallpaper min-h-dvh text-ink sm:h-dvh sm:overflow-hidden">
      <header className="menubar fixed inset-x-0 top-0 z-40 h-7 flex items-center gap-4 px-4 text-ink">
        <a href="#/" aria-label="TrustCheck home" className="orb size-[18px] bg-night text-white text-[10px] font-extrabold">T</a>
        <span className="font-bold">TrustCheck</span>
        <span className="hidden sm:inline text-ink/70">{title}</span>
        <span className="ml-auto flex items-center gap-4 text-ink/85" aria-live="polite">
          <span className="hidden sm:flex items-center gap-1.5"><Dot on={health ? true : health === false ? false : null} />{health ? "Protected" : health === false ? "Backend offline" : "Connecting"}</span>
          <Clock />
        </span>
      </header>

      <div className="pt-7 sm:pt-9 pb-24 sm:px-4 lg:px-6">
        <motion.div initial={still ? false : { opacity: 0, scale: 0.965, y: 14 }} animate={{ opacity: 1, scale: 1, y: 0 }}
          transition={{ type: "spring", stiffness: 260, damping: 26 }}
          className="window mx-auto max-w-[1600px] overflow-hidden sm:h-[calc(100dvh-7.9rem)] flex flex-col max-sm:rounded-none max-sm:shadow-none">
          <div className="titlebar hidden sm:flex h-12 shrink-0 items-center px-4 relative">
            <div className="group flex gap-2" aria-label="Window controls">
              <a href="#/" aria-label="Close console, back to home" className="light bg-[#ff5f57]"><span className="opacity-0 group-hover:opacity-100 text-[9px] leading-none text-black/55 font-bold">×</span></a>
              <span className="light bg-[#febc2e]" aria-hidden><span className="opacity-0 group-hover:opacity-100 text-[9px] leading-none text-black/55 font-bold">−</span></span>
              <span className="light bg-[#28c840]" aria-hidden><span className="opacity-0 group-hover:opacity-100 text-[8px] leading-none text-black/55 font-bold">+</span></span>
            </div>
            <p className="absolute left-1/2 -translate-x-1/2 text-[13px] font-semibold text-ink/80">{title}</p>
          </div>

          <div className="flex-1 min-h-0 flex">
            <aside className="sidebar hidden md:flex w-56 shrink-0 flex-col p-3 gap-0.5">
              <p className="label px-2.5 pb-1.5 pt-1">TrustCheck</p>
              {KEYS.map((k, i) => (
                <a key={k} href={`#/app/${k}`} aria-current={page === k ? "page" : undefined} className="side-item">
                  <Icon name={PAGES[k][2]} className="size-[17px] shrink-0" />
                  <span className="flex-1 truncate">{PAGES[k][0]}</span>
                  {k === "cases" && highOpen > 0
                    ? <span className="min-w-5 h-5 px-1.5 rounded-full bg-high text-white text-[11px] font-bold grid place-items-center tnum">{highOpen}</span>
                    : <kbd>{mod}{i + 1}</kbd>}
                </a>
              ))}
              <div className="mt-auto rounded-lg bg-white/55 p-2.5 space-y-1.5 text-[12.5px]">
                {status.map(([name, on, text]) => (
                  <p key={name} className="flex items-center gap-2"><Dot on={on} /><span className="font-medium">{name}</span><span className="ml-auto text-ink-soft">{text}</span></p>
                ))}
                {health === false && <p className="text-high text-[12px] pt-1">Start it: uvicorn app:app --port 8000</p>}
              </div>
            </aside>

            <main className="pane flex-1 min-w-0 overflow-y-auto scroll-quiet">
              {/* swap at once and fade in: waiting for an exit fade made page switches feel slow */}
              <motion.div key={page} initial={still ? false : { opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.18, ease: "easeOut" }}
                className="px-4 py-5 sm:px-8 sm:py-7">
                <Page />
              </motion.div>
            </main>
          </div>
        </motion.div>
      </div>
      <Dock current={page} />
    </div>
  );
}
