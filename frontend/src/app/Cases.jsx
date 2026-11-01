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
      <button onClick={() => setOpen(null)} className="btn btn-plain">‹ Back to the queue</button>
      <Verdict result={open.result} caseId={open.id} initialStatus={open.status} simple={false} />
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
    <div className="space-y-6">
      <div>
        <h2 className="text-[28px] font-bold tracking-tight">Security queue</h2>
        <p className="text-ink-soft mt-1 text-[13.5px]">Every check lands here. It refreshes every few seconds, so a NO from the real person (email, QR or Telegram) shows up while you watch.</p>
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {tiles.map(([k, n, label, color]) => (
          <button key={k} onClick={() => setFilter(filter === k ? "all" : k)} aria-pressed={filter === k}
            className={`text-left px-4 py-3.5 rounded-[12px] transition-colors ${filter === k ? "bg-night text-white shadow-[0_10px_30px_-14px_rgb(35_22_94/0.8)]" : "glass hover:bg-[#f8f6fc]"}`}>
            <motion.span key={n} initial={{ opacity: 0.3 }} animate={{ opacity: 1 }} className={`display block text-[34px] font-extrabold tracking-tight tnum leading-none ${filter === k ? "text-white" : color}`}>{n}</motion.span>
            <span className={`block mt-1.5 text-[12.5px] font-medium ${filter === k ? "text-white/75" : "text-ink-soft"}`}>{label}</span>
          </button>
        ))}
      </div>

      {stats && (stats.money_held > 0 || stats.scam_types?.length > 0) && (
        <section className="grid lg:grid-cols-[22rem_1fr] gap-3">
          <div className="rounded-[12px] bg-night text-white px-4 py-3.5 shadow-[0_10px_30px_-14px_rgb(35_22_94/0.8)]">
            <span className="block text-[12.5px] font-medium text-white/70">Money held back from risky requests</span>
            <span className="display block text-[30px] font-extrabold tracking-tight tnum mt-1 leading-none">₹{Math.round(stats.money_held).toLocaleString("en-IN")}</span>
            <span className="block text-[11.5px] text-white/60 mt-1.5">Payments asked for in MEDIUM and HIGH cases that nobody verified as genuine</span>
          </div>
          <div className="glass px-4 py-3.5">
            <p className="label mb-2.5">Scam types caught</p>
            <ul className="space-y-1.5">{stats.scam_types.slice(0, 6).map(([label, n]) => (
              <li key={label} className="grid grid-cols-[minmax(0,14rem)_1fr_2rem] items-center gap-3 text-[13px]">
                <span className="truncate font-medium" title={label}>{label}</span>
                <span className="h-1.5 rounded-full heat-scale" style={{ width: `${(n / stats.scam_types[0][1]) * 100}%` }} />
                <span className="tnum font-bold text-right">{n}</span>
              </li>))}
            </ul>
          </div>
        </section>
      )}

      <MuleList />

      {!shown.length ?<p className="text-ink-soft">{cases.length ? "Nothing matches this filter." : "No checks yet. Run one from Check a message."}</p> : (
        <div className="overflow-x-auto glass">
          <table className="w-full text-left border-collapse">
            <thead><tr className="text-[12px] text-ink-soft border-b border-ink/10 bg-[#faf9fd]">
              <th className="py-2 px-4 font-semibold">When</th><th className="pr-6 font-medium">Verdict</th><th className="pr-6 font-medium">Status</th><th className="font-medium">What happened</th>
            </tr></thead>
            <tbody>{shown.map((c) => (
              <tr key={c.id} tabIndex={0} onKeyDown={async (e) => e.key === "Enter" && setOpen(await api(`/cases/${c.id}`))}
                onClick={async () => setOpen(await api(`/cases/${c.id}`))} className="border-b border-ink/[0.06] last:border-0 hover:bg-night/[0.04] cursor-pointer align-top">
                <td className="py-3 px-4 text-[13px] whitespace-nowrap tnum text-ink-soft">{new Date(c.created * 1000).toLocaleString([], { dateStyle: "short", timeStyle: "short" })}</td>
                <td className={`pr-6 py-3 whitespace-nowrap text-[15px] font-bold tnum ${BAND_TEXT[c.band]}`}>{c.band} {Math.round(c.risk)}</td>
                <td className={`pr-6 py-3 text-[13px] whitespace-nowrap ${c.status === "confirmed_attack" ? "text-high font-bold" : ""}`}>{STATUS[c.status]}</td>
                <td className="py-3 pr-4 text-[13px] max-w-2xl">
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
