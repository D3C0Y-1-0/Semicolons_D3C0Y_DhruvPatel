import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useState } from "react";
import Icon from "../components/Icons.jsx";
import { api } from "../lib/api.js";
import Cases from "./Cases.jsx";
import Check from "./Check.jsx";
import Live from "./Live.jsx";
import People from "./People.jsx";

export const PAGES = { check: ["Check a message", Check, "check"], live: ["Live call", Live, "live"], cases: ["Security queue", Cases, "queue"], people: ["Trust Graph", People, "people"] };

export default function AppShell({ page }) {
  const [health, setHealth] = useState(null);
  useEffect(() => {
    const ping = () => api("/health").then(setHealth).catch(() => setHealth(false));
    ping();
    const t = setInterval(ping, 10000);
    return () => clearInterval(t);
  }, []);
  const Page = PAGES[page]?.[1] || Check;

  return (
    <div className="min-h-screen p-2 sm:p-4">
      <div className="frame bg-white/45 backdrop-blur-xl min-h-[calc(100vh-1rem)] sm:min-h-[calc(100vh-2rem)] lg:grid lg:grid-cols-[5.75rem_1fr]">
        <aside className="flex lg:flex-col items-center gap-3 p-3 lg:py-6 lg:sticky lg:top-0 lg:h-screen lg:max-h-[calc(100vh-2rem)]">
          <a href="#/" aria-label="TrustCheck home" title="Home" className="orb size-12 bg-night text-white font-extrabold text-xl">T</a>
          <nav aria-label="Console" className="glass rounded-full p-1.5 flex lg:flex-col gap-1.5 lg:my-auto">
            {Object.entries(PAGES).map(([key, [label, , icon]]) => (
              <a key={key} href={`#/app/${key}`} aria-current={page === key ? "page" : undefined} title={label}
                className={`relative orb size-11 ${page === key ? "text-white" : "text-ink hover:bg-white"}`}>
                {page === key && <motion.span layoutId="nav" className="absolute inset-0 bg-night rounded-full" transition={{ type: "spring", stiffness: 400, damping: 34 }} />}
                <span className="relative"><Icon name={icon} /></span>
                <span className="sr-only">{label}</span>
              </a>
            ))}
          </nav>
          <span title={health ? "Backend online" : "Backend offline"} className={`ml-auto lg:ml-0 size-3 rounded-full ring-4 ring-white/80 ${health ? "bg-low" : health === false ? "bg-high" : "bg-ink-soft/40"}`} />
        </aside>

        <main className="min-w-0 px-3 pb-8 sm:px-6 lg:pl-2 lg:pr-8 lg:py-6">
          <div className="flex flex-wrap items-center justify-between gap-3 mb-6 lg:mb-8">
            <p className="glass-strong rounded-full px-5 py-2.5 font-bold">{PAGES[page]?.[0] || "Check a message"}</p>
            <p className="glass-strong rounded-full px-4 py-2.5 text-sm font-semibold flex items-center gap-2" aria-live="polite">
              <span className={`size-2 rounded-full ${health ? "bg-low" : health === false ? "bg-high" : "bg-ink-soft/40"}`} />
              {health ? `Backend online${health.telegram ? ", Telegram on" : ""}${health.llm ? ", LLM on" : ""}` : health === false ? "Backend offline: run uvicorn on port 8000" : "Connecting…"}
            </p>
          </div>
          <AnimatePresence mode="wait">
            <motion.div key={page} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.2 }}>
              <Page />
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  );
}
