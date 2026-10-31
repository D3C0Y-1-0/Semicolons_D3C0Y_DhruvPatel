import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import Verdict, { BAND_TEXT } from "../components/Verdict.jsx";
import { api } from "../lib/api.js";

const STATUS = { open: "Open", verifying: "Verifying", verified: "Verified genuine", confirmed_attack: "Confirmed attack" };

export default function Cases() {
  const [cases, setCases] = useState([]);
  const [stats, setStats] = useState(null);
  const [open, setOpen] = useState(null);
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    const load = () => { api("/cases").then(setCases).catch(() => {}); api("/stats").then(setStats).catch(() => {}); };
    load();
    const t = setInterval(load, 3000); // updates live when someone answers on Telegram
    return () => clearInterval(t);
  }, []);

  if (open) return (
    <div className="space-y-6">
      <button onClick={() => setOpen(null)} className="underline underline-offset-4">Back to the queue</button>
      <Verdict result={open.result} caseId={open.id} initialStatus={open.status} />
    </div>
  );

  const shown = cases.filter((c) => filter === "all" || c.band === filter || c.status === filter);
  const b = stats?.bands || {};
  const tiles = [
    ["HIGH", b.HIGH || 0, "high-risk checks", "text-high"],
    ["MEDIUM", b.MEDIUM || 0, "need a second look", "text-medium"],
    ["confirmed_attack", stats?.status?.confirmed_attack || 0, "confirmed attacks", "text-ink"],
    ["campaign", stats?.campaigns?.length || 0, "voice campaigns", "text-ink"],
  ];

  return (
    <div className="space-y-10">
      <div>
        <h2 className="wide text-4xl font-extrabold">Security queue</h2>
        <p className="text-ink-soft mt-2">Every check lands here. It refreshes every few seconds, so a NO on Telegram shows up while you watch.</p>
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-4 border-y-2 border-ink divide-x divide-rule">
        {tiles.map(([k, n, label, color]) => (
          <button key={k} onClick={() => setFilter(filter === k ? "all" : k)} aria-pressed={filter === k}
            className={`text-left px-5 py-5 ${filter === k ? "bg-sheet" : "hover:bg-sheet/60"}`}>
            <motion.span key={n} initial={{ opacity: 0.3 }} animate={{ opacity: 1 }} className={`wide block text-4xl font-extrabold tnum ${color}`}>{n}</motion.span>
            <span className="text-sm text-ink-soft">{label}</span>
          </button>
        ))}
      </div>

      {!shown.length ? <p className="text-ink-soft">{cases.length ? "Nothing matches this filter." : "No checks yet. Run one from Check a message."}</p> : (
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead><tr className="text-sm text-ink-soft border-b border-ink/40">
              <th className="py-2 pr-6 font-medium">When</th><th className="pr-6 font-medium">Verdict</th><th className="pr-6 font-medium">Status</th><th className="font-medium">What happened</th>
            </tr></thead>
            <tbody>{shown.map((c) => (
              <tr key={c.id} tabIndex={0} onKeyDown={async (e) => e.key === "Enter" && setOpen(await api(`/cases/${c.id}`))}
                onClick={async () => setOpen(await api(`/cases/${c.id}`))} className="border-b border-rule hover:bg-sheet cursor-pointer align-top">
                <td className="py-4 pr-6 text-sm whitespace-nowrap tnum">{new Date(c.created * 1000).toLocaleString([], { dateStyle: "short", timeStyle: "short" })}</td>
                <td className={`pr-6 py-4 whitespace-nowrap narrow text-xl font-extrabold ${BAND_TEXT[c.band]}`}>{c.band} {Math.round(c.risk)}</td>
                <td className={`pr-6 py-4 text-sm whitespace-nowrap ${c.status === "confirmed_attack" ? "text-high font-bold" : ""}`}>{STATUS[c.status]}</td>
                <td className="py-4 text-sm max-w-2xl">
                  <span className="line-clamp-2">{c.summary}</span>
                  {c.campaign && <span className="text-high font-semibold">Part of voice campaign {c.campaign.slice(0, 6)}</span>}
                </td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      )}
    </div>
  );
}
