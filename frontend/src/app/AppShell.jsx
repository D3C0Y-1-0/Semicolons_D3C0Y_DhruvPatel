import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useState } from "react";
import Dock from "../components/Dock.jsx";
import { api } from "../lib/api.js";
import Cases from "./Cases.jsx";
import Check from "./Check.jsx";
import Live from "./Live.jsx";
import People from "./People.jsx";

export const PAGES = { check: ["Check a message", Check], live: ["Live call", Live], cases: ["Security queue", Cases], people: ["Trust Graph", People] };

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
    <div className="min-h-screen p-2 sm:p-4 pb-28 sm:pb-28">
      <div className="frame bg-white/45 backdrop-blur-xl min-h-[calc(100vh-8rem)]">
        <main className="min-w-0 px-3 py-4 sm:px-8 sm:py-6">
          <div className="flex flex-wrap items-center gap-3 mb-6 lg:mb-8">
            <a href="#/" aria-label="TrustCheck home" className="orb size-11 bg-night text-white font-extrabold text-lg">T</a>
            <p className="glass-strong rounded-full px-5 py-2.5 font-bold">{PAGES[page]?.[0] || "Check a message"}</p>
            <p className="ml-auto glass-strong rounded-full px-4 py-2.5 text-sm font-semibold flex items-center gap-2" aria-live="polite">
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
      <Dock current={page} />
    </div>
  );
}
