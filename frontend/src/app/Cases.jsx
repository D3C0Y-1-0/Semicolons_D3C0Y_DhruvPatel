import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import Verdict, { BAND_TEXT } from "../components/Verdict.jsx";
import { MuleList } from "../components/Defense.jsx";
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
    const t = setInterval(load, 3000); // updates live when the real person answers
    return () => clearInterval(t);
  }, []);

  if (open) return (
    <div className="space-y-6">
      <button onClick={() => setOpen(null)} className="glass-strong rounded-full px-5 py-2.5 font-semibold">Back to the queue</button>
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
        <h2 className="text-5xl font-bold tracking-[-0.04em]">Security queue</h2>
        <p className="text-ink-soft mt-2">Every check lands here. It refreshes every few seconds, so a NO from the real person (SMS, email, QR or Telegram) shows up while you watch.</p>
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {tiles.map(([k, n, label, color]) => (
          <button key={k} onClick={() => setFilter(filter === k ? "all" : k)} aria-pressed={filter === k}
            className={`text-left px-6 py-5 rounded-[1.75rem] transition-colors ${filter === k ? "bg-night text-white" : "glass hover:bg-white/80"}`}>
            <motion.span key={n} initial={{ opacity: 0.3 }} animate={{ opacity: 1 }} className={`block text-5xl font-extrabold tracking-tight tnum ${filter === k ? "text-white" : color}`}>{n}</motion.span>
            <span className={`text-sm font-semibold ${filter === k ? "text-white/75" : "text-ink-soft"}`}>{label}</span>
          </button>
        ))}
      </div>

      {stats && (stats.money_held > 0 || stats.scam_types?.length > 0) && (
        <section className="grid lg:grid-cols-[22rem_1fr] gap-3">
          <div className="rounded-[1.75rem] bg-night text-white px-6 py-5">
            <span className="block text-sm font-semibold text-white/70">Money held back from risky requests</span>
            <span className="block text-4xl font-extrabold tracking-tight tnum mt-1">₹{Math.round(stats.money_held).toLocaleString("en-IN")}</span>
            <span className="block text-xs text-white/60 mt-1">Payments asked for in MEDIUM and HIGH cases that nobody verified as genuine</span>
          </div>
          <div className="glass rounded-[1.75rem] px-6 py-5">
            <p className="text-sm font-semibold text-ink-soft mb-3">Scam types caught</p>
            <ul className="space-y-1.5">{stats.scam_types.slice(0, 6).map(([label, n]) => (
              <li key={label} className="grid grid-cols-[minmax(0,14rem)_1fr_2rem] items-center gap-3 text-sm">
                <span className="truncate font-medium" title={label}>{label}</span>
                <span className="h-2.5 rounded-full heat-scale" style={{ width: `${(n / stats.scam_types[0][1]) * 100}%` }} />
                <span className="tnum font-bold text-right">{n}</span>
              </li>))}
            </ul>
          </div>
        </section>
      )}

      <MuleList />

      {!shown.length ?<p className="text-ink-soft">{cases.length ? "Nothing matches this filter." : "No checks yet. Run one from Check a message."}</p> : (
        <div className="overflow-x-auto glass rounded-[2rem] p-2 sm:p-4">
          <table className="w-full text-left border-collapse">
            <thead><tr className="text-sm text-ink-soft border-b border-ink/40">
              <th className="py-2 px-3 font-medium">When</th><th className="pr-6 font-medium">Verdict</th><th className="pr-6 font-medium">Status</th><th className="font-medium">What happened</th>
            </tr></thead>
            <tbody>{shown.map((c) => (
              <tr key={c.id} tabIndex={0} onKeyDown={async (e) => e.key === "Enter" && setOpen(await api(`/cases/${c.id}`))}
                onClick={async () => setOpen(await api(`/cases/${c.id}`))} className="border-b border-white/70 hover:bg-white/70 cursor-pointer align-top">
                <td className="py-4 px-3 text-sm whitespace-nowrap tnum">{new Date(c.created * 1000).toLocaleString([], { dateStyle: "short", timeStyle: "short" })}</td>
                <td className={`pr-6 py-4 whitespace-nowrap text-xl font-extrabold tnum ${BAND_TEXT[c.band]}`}>{c.band} {Math.round(c.risk)}</td>
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
