import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useState } from "react";
import { API, api, form } from "../lib/api.js";
import Icon from "./Icons.jsx";

const mmss = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

// Cooling-off lock: a HIGH payment can't go out for 30 minutes unless the real person taps YES.
export function HoldLock({ until, status }) {
  const [now, setNow] = useState(Date.now() / 1000);
  useEffect(() => { const t = setInterval(() => setNow(Date.now() / 1000), 1000); return () => clearInterval(t); }, []);
  const left = Math.max(0, until - now);
  const [tone, head, body] =
    status === "verified" ? ["bg-low", "Released", "The real person confirmed it was them, so the lock lifted early."]
    : status === "confirmed_attack" ? ["bg-high", "Payment blocked", "The real person says they didn't send it. Don't pay, ever."]
    : left > 0 ? ["bg-night", mmss(left), "Payment locked. Scammers rely on urgency; this lock takes it away. Only the real person's YES lifts it early."]
    : ["bg-medium", "Lock ended, still unverified", "Get a second approver before paying anything."];
  return (
    <div className={`${tone} text-white rounded-[1.5rem] p-5 flex items-center gap-5`}>
      <span className="orb size-14 bg-white/15 shrink-0"><Icon name="lock" className="size-7" /></span>
      <div>
        <p className="text-3xl font-extrabold tracking-tight tnum leading-none">{head}</p>
        <p className="mt-1.5 text-white/85 text-sm max-w-md">{body}</p>
      </div>
    </div>
  );
}

// Email (sent by itself when SMTP is set up, else one tap) and a QR for someone in the room.
export function SendLinks({ delivery, who, qr, qrLabel }) {
  if (!delivery) return null;
  const { sent = [], errors = [], links = {} } = delivery;
  const btn = "bg-white border border-white rounded-full px-4 py-2 text-sm font-semibold hover:bg-white/70";
  return (
    <div className="rounded-[1.5rem] bg-white/70 border border-white p-5 flex flex-wrap gap-5 items-center">
      <div className="flex-1 min-w-56 space-y-3">
        {sent.length > 0 && <p className="font-semibold text-low">Sent to {who} by {sent.join(" and ")}.</p>}
        {!sent.length && <p className="text-sm text-ink-soft">{links.email ? `Email it to ${who}'s registered address, or let ${who} scan the code:` : `${who} has no email in the Trust Graph. Let ${who} scan the code:`}</p>}
        {links.email && !sent.includes("email") && <a href={links.email} className={btn}>Email</a>}
        {delivery.family_after && <p className="text-sm font-semibold text-high">No answer from {who} within {delivery.family_after} s and the family gets an email that this is a scam.</p>}
        {errors.map((e) => <p key={e} className="text-xs text-high">{e}</p>)}
      </div>
      {qr && <figure className="text-center"><img src={`${API}/qr?data=${encodeURIComponent(qr)}`} alt={qrLabel} className="size-36 rounded-xl" />
        <figcaption className="text-xs text-ink-soft mt-1 max-w-36">{qrLabel}</figcaption></figure>}
    </div>
  );
}

// Human 2FA: the real person reads their rotating code word from their TrustCheck page (or /code on Telegram); you type what the caller said.
export function CodeWordCheck({ person, compact = false }) {
  const [said, setSaid] = useState("");
  const [res, setRes] = useState(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => { setRes(null); setSaid(""); }, [person?.id]);
  if (!person) return null;
  const first = person.name.split(" ")[0];
  const check = async (e) => {
    e.preventDefault();
    if (!said.trim()) return;
    setBusy(true);
    try { setRes(await api(`/people/${person.id}/code`, { method: "POST", body: form({ said }) })); }
    catch (err) { setRes({ error: err.message }); }
    finally { setBusy(false); }
  };
  return (
    <form onSubmit={check} className={`rounded-[1.5rem] ${compact ? "glass" : "bg-white/80 border border-white"} p-5 space-y-3`}>
      <p className="font-bold text-lg">Ask for {first}'s code word</p>
      <p className="text-sm text-ink-soft">The real {first} opens their TrustCheck page (sent once by email or QR from <a href="#/app/people" className="underline font-semibold text-ink">Trust Graph</a>) and reads two words that change every 30 seconds. A cloned voice can't know them. Never say them first.</p>
      <div className="flex flex-wrap gap-2">
        <input value={said} onChange={(e) => { setSaid(e.target.value); setRes(null); }} placeholder="What did they say? e.g. mango river"
          className="flex-1 min-w-48 bg-white border border-rule rounded-xl px-4 py-2.5 outline-none focus:border-night/40" />
        <button disabled={busy} className="bg-night text-white rounded-full px-5 py-2.5 font-semibold disabled:opacity-60">{busy ? "Checking…" : "Check"}</button>
      </div>
      <AnimatePresence mode="wait">
        {res && (
          <motion.p key={String(res.match)} initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} role="status"
            className={`rounded-xl px-4 py-3 font-bold ${res.error ? "text-high" : res.match ? "bg-low text-white" : "bg-high text-white"}`}>
            {res.error || (res.match ? `Correct. This is really ${res.person}.` : `Wrong code word. Treat the caller as an impostor and hang up.`)}
          </motion.p>
        )}
      </AnimatePresence>
    </form>
  );
}

// Decoy Mode: reply as a cooperative, slightly confused victim so the scammer reveals their mule accounts.
export function DecoyPanel({ caseId, initial }) {
  const [state, setState] = useState(initial || null);
  const [reply, setReply] = useState("");
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  const [err, setErr] = useState("");
  const step = async (scammer = "") => {
    setBusy(true); setErr("");
    try { setState(await api(`/cases/${caseId}/decoy`, { method: "POST", body: form({ scammer }) })); setReply(""); setCopied(false); }
    catch (e) { setErr(e.message); }
    finally { setBusy(false); }
  };
  const last = state?.turns?.at(-1);
  const copy = async () => { try { await navigator.clipboard.writeText(last.text); setCopied(true); } catch { /* clipboard blocked: the text is on screen */ } };

  return (
    <section className="rounded-[2rem] bg-night text-white p-6 sm:p-7 space-y-5 relative overflow-hidden">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="max-w-xl">
          <h3 className="text-2xl font-bold">Decoy Mode</h3>
          <p className="mt-1 text-white/75">Don't just block it. Reply as a confused victim and make the scammer reveal the bank accounts, UPI ids and numbers they use. Every one goes on the blocklist, so the next attack using them is caught instantly.</p>
        </div>
        {!state && <button onClick={() => step()} disabled={busy} className="bg-white text-night rounded-full pl-5 pr-2 py-2 font-bold inline-flex items-center gap-3 disabled:opacity-60">
          {busy ? "Starting…" : "Start Decoy Mode"}<span className="orb size-8 bg-night text-white"><Icon name="arrow" className="size-4" /></span></button>}
      </div>

      {state && (
        <>
          <ol className="space-y-2.5 max-h-80 overflow-y-auto pr-1" aria-label="Decoy conversation">
            {state.turns.map((t, i) => (
              <motion.li key={i} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
                className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm ${t.who === "decoy" ? "ml-auto bg-white text-ink rounded-br-md" : "bg-white/10 rounded-bl-md"}`}>
                <span className={`block text-xs font-bold mb-0.5 ${t.who === "decoy" ? "text-medium" : "text-white/60"}`}>{t.who === "decoy" ? "Send this as the victim" : "Scammer"}</span>
                {t.text}
              </motion.li>
            ))}
          </ol>
          {last?.who === "decoy" && (
            <button onClick={copy} className="bg-white/15 hover:bg-white/25 rounded-full px-4 py-2 text-sm font-semibold">{copied ? "Copied. Paste it into the chat with the scammer" : "Copy the reply"}</button>
          )}
          <form onSubmit={(e) => { e.preventDefault(); reply.trim() && step(reply); }} className="flex flex-wrap gap-2">
            <textarea value={reply} onChange={(e) => setReply(e.target.value)} rows={2} placeholder="Paste what the scammer answered"
              className="flex-1 min-w-56 bg-white/10 border border-white/20 rounded-xl px-4 py-2.5 text-white placeholder:text-white/45 outline-none focus:border-white/60" />
            <button disabled={busy || !reply.trim()} className="bg-white text-night rounded-full px-5 py-2.5 font-bold self-end disabled:opacity-50">{busy ? "Reading…" : "Extract and reply"}</button>
          </form>
          <div>
            <p className="text-sm font-bold text-white/80 mb-2">Caught so far, now on the blocklist</p>
            <ul className="flex flex-wrap gap-2">
              {state.harvested.map((h) => (
                <motion.li key={h.kind + h.value} initial={{ scale: 0.8, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
                  className={`rounded-full px-3.5 py-1.5 text-sm font-semibold ${state.new?.some((n) => n.value === h.value) ? "bg-heat-4 text-ink" : "bg-white/15"}`}>
                  {h.label}: <span className="tnum">{h.value}</span>
                </motion.li>
              ))}
              {!state.harvested.length && <li className="text-white/60 text-sm">Nothing yet. Their next reply usually gives something away.</li>}
            </ul>
          </div>
          <p className="text-xs text-white/55">The decoy only asks questions. Never send money, OTPs or real company details.</p>
        </>
      )}
      {err && <p className="text-heat-4 text-sm">{err}</p>}
    </section>
  );
}

// The shared blocklist, for the security queue
export function MuleList() {
  const [mules, setMules] = useState([]);
  useEffect(() => {
    const load = () => api("/mules").then(setMules).catch(() => {});
    load();
    const t = setInterval(load, 4000);
    return () => clearInterval(t);
  }, []);
  return (
    <section className="glass rounded-[2rem] p-5 sm:p-6">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-2xl font-bold">Mule blocklist</h3>
        <p className="text-sm text-ink-soft">Any new message naming one of these is HIGH, whoever it claims to be from.</p>
      </div>
      {!mules.length ? <p className="mt-3 text-ink-soft">Empty. Confirmed attacks and Decoy Mode conversations fill it.</p> : (
        <ul className="mt-4 flex flex-wrap gap-2">
          {mules.map((m) => (
            <li key={m.kind + m.value} className="bg-white/80 border border-white rounded-full pl-4 pr-2 py-1.5 text-sm flex items-center gap-2">
              <span className="font-semibold">{m.label}</span><span className="tnum">{m.value}</span>
              <span className="text-xs text-ink-soft">{m.source}</span>
              {m.hits > 1 && <span className="orb size-6 bg-high text-white text-xs font-bold">{m.hits}</span>}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
