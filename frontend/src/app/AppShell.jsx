import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useState } from "react";
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
    <div className="min-h-screen lg:grid lg:grid-cols-[15rem_1fr]">
      <aside className="bg-night text-paper lg:min-h-screen lg:sticky lg:top-0 lg:h-screen flex lg:flex-col gap-x-6 gap-y-1 px-4 py-3 lg:p-5 flex-wrap items-center lg:items-stretch">
        <a href="#/" className="wide text-xl font-extrabold lg:mb-8">TrustCheck</a>
        <nav className="flex lg:flex-col gap-1 flex-wrap" aria-label="Console">
          {Object.entries(PAGES).map(([key, [label]]) => (
            <a key={key} href={`#/app/${key}`} aria-current={page === key ? "page" : undefined}
              className={`relative px-3 py-2 rounded ${page === key ? "text-night" : "text-paper/75 hover:text-paper"}`}>
              {page === key && <motion.span layoutId="nav" className="absolute inset-0 bg-mint rounded" transition={{ type: "spring", stiffness: 400, damping: 34 }} />}
              <span className="relative font-semibold">{label}</span>
            </a>
          ))}
        </nav>
        <p className="lg:mt-auto text-xs text-paper/60 flex items-center gap-2" aria-live="polite">
          <span className={`size-2 rounded-full ${health ? "bg-mint" : health === false ? "bg-[#ff7a5c]" : "bg-paper/40"}`} />
          {health ? `Backend online${health.telegram ? ", Telegram on" : ""}${health.llm ? ", LLM on" : ""}` : health === false ? "Backend offline: run uvicorn on port 8000" : "Connecting…"}
        </p>
      </aside>
      <main className="paper-grain min-w-0">
        <AnimatePresence mode="wait">
          <motion.div key={page} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.18 }}
            className="max-w-6xl mx-auto px-5 sm:px-8 py-10">
            <Page />
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  );
}
