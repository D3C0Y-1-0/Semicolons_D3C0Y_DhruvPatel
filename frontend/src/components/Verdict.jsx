import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { useEffect, useState } from "react";
import { api, form } from "../lib/api.js";
import { CodeWordCheck, DecoyPanel, HoldLock, SendLinks } from "./Defense.jsx";
// ponytail: simple vs full is a prop per page (Check = simple, Security queue = full); a per-user role setting when logins exist

export const BAND_TEXT = { LOW: "text-low", MEDIUM: "text-medium", HIGH: "text-high" };
export const BAND_BORDER = { LOW: "border-low", MEDIUM: "border-medium", HIGH: "border-high" };
const TACTIC = {
  urgency: "urgency", secrecy: "secrecy", authority: "authority claim", payment_request: "payment request",
  credential_request: "credential or OTP request", channel_switch: "channel switch", new_beneficiary: "new beneficiary",
  fear_threat: "fear or legal threat", reward: "reward bait",
};
const HEADLINE = { HIGH: "Don't act on this yet.", MEDIUM: "Pause and verify first.", LOW: "Looks normal." };
const STATUS = {
  open: "Not verified yet",
  verifying: "Waiting for the real person to answer YES or NO…",
  verified: "The real person confirmed they sent it.",
  confirmed_attack: "The real person says they did not send it. Treat this as an attack.",
};

// The verdict as a heat gauge: the number, its band, and where it sits on the cold-to-hot scale.
export function Stamp({ band, risk, size = "text-7xl", className = "" }) {
  const reduce = useReducedMotion();
  const r = Math.floor(risk);
  return (
    <motion.div key={band + r} className={`glass-strong px-5 pt-3.5 pb-5 inline-flex flex-col min-w-[12.5rem] ${className}`}
      initial={reduce ? false : { scale: 0.92, opacity: 0, y: 10 }} animate={{ scale: 1, opacity: 1, y: 0 }}
      transition={{ type: "spring", stiffness: 380, damping: 26 }}>
      <span className={`text-[13px] font-semibold ${BAND_TEXT[band]}`}>{band} risk</span>
      <span className={`display ${size} font-extrabold leading-[0.95] tracking-tight tnum ${BAND_TEXT[band]}`}>
        {r}<span className="text-[0.26em] font-semibold text-ink-soft"> / 100</span>
      </span>
      <span className="relative mt-4 h-2 rounded-full heat-scale" aria-hidden>
        <motion.span className="absolute top-1/2 size-4 -translate-y-1/2 -translate-x-1/2 rounded-full bg-white ring-[4px] ring-night shadow"
          initial={reduce ? false : { left: "0%" }} animate={{ left: `${Math.min(97, Math.max(3, r))}%` }}
          transition={{ type: "spring", stiffness: 90, damping: 18 }} />
      </span>
    </motion.div>
  );
}

// Read the verdict and what to do out loud, for anyone who'd rather listen.
function Share({ r }) {
  const [speaking, setSpeaking] = useState(false);
  if (r.band === "LOW") return null;
  const say = () => {
    const s = window.speechSynthesis;
    if (!s) return;
    if (speaking) { s.cancel(); setSpeaking(false); return; }
    const u = new SpeechSynthesisUtterance(`${HEADLINE[r.band]} ${r.recommended_actions.join(". ")}`);
    u.onend = () => setSpeaking(false);
    s.speak(u); setSpeaking(true);
  };
  return <button type="button" onClick={say} className="btn btn-plain self-start">{speaking ? "Stop" : "Read it out loud"}</button>;
}

export function Waterfall({ rows, max }) {
  const top = max ?? Math.max(3, ...rows.map((r) => Math.abs(r.contribution)));
  const pct = (v) => `${(Math.min(Math.abs(v), top) / top) * 50}%`;
  return (
    <ul className="divide-y divide-rule border-y border-rule">
      {rows.map((r) => (
        <motion.li layout key={r.signal + r.label} transition={{ type: "spring", stiffness: 300, damping: 30 }}>
          <details className="group py-2.5">
            <summary className="grid grid-cols-[minmax(0,12rem)_1fr_3.75rem] items-center gap-3 cursor-pointer list-none">
              <span className="text-sm font-medium truncate" title={r.label}>{r.label}</span>
              <span className="relative h-3.5" aria-hidden>
                <span className="absolute inset-y-0 left-1/2 w-px bg-ink/30" />
                <motion.span className={`absolute inset-y-0 rounded-sm ${r.contribution > 0 ? "bg-high" : "bg-low"}`}
                  style={r.contribution > 0 ? { left: "50%" } : { right: "50%" }}
                  initial={{ width: 0 }} animate={{ width: pct(r.contribution) }} transition={{ type: "spring", stiffness: 160, damping: 24 }} />
              </span>
              <span className={`text-sm tnum text-right font-semibold ${r.contribution > 0 ? "text-high" : "text-low"}`}>
                {r.contribution > 0 ? "+" : ""}{r.contribution.toFixed(2)}
              </span>
            </summary>
            {r.why && (
              <div className="mt-2 text-sm text-ink-soft space-y-1">
                <p>{r.why} <span className="tnum">(score {r.score.toFixed(2)} × weight {r.weight})</span></p>
                {r.evidence?.some((e) => e.img) && (
                  <div className="flex gap-2 pt-1">{r.evidence.filter((e) => e.img).map((e) => (
                    <figure key={e.t}><img src={e.img} alt={`Face at ${e.t}s`} className="w-20 h-20 rounded object-cover ring-2 ring-high/60" />
                      <figcaption className="text-xs tnum mt-0.5">{e.t}s</figcaption></figure>))}
                  </div>
                )}
                {r.evidence?.filter((e) => e.type !== "span" && !e.img).slice(0, 6).map((e, j) => (
                  <p key={j} className="pl-3 border-l-2 border-rule break-words">{e.field ? `${e.field}: ` : ""}{e.text}{e.verdict ? `: ${e.verdict}` : ""}{e.final ? ` (goes to ${e.final})` : ""}</p>
                ))}
              </div>
            )}
          </details>
        </motion.li>
      ))}
    </ul>
  );
}

export function Highlighted({ text, spans = [] }) {
  if (!text) return null;
  const parts = [];
  let at = 0;
  for (const s of [...spans].sort((a, b) => a.start - b.start)) {
    if (s.start < at) continue;
    parts.push(text.slice(at, s.start));
    parts.push(
      <mark key={s.start} title={TACTIC[s.tactic]} className="bg-transparent text-ink font-semibold underline decoration-high decoration-[3px] underline-offset-[5px]">
        {text.slice(s.start, s.end)}
      </mark>,
    );
    at = s.end;
  }
  parts.push(text.slice(at));
  return <p className="whitespace-pre-wrap leading-[1.8] text-[16px] max-w-prose">{parts}</p>;
}

export function Waveform({ peaks = [], timeline = [], frames = [], duration }) {
  if (!peaks.length && !timeline.length && !frames.length) return null;
  const n = peaks.length || 200;
  return (
    <figure>
      <svg viewBox={`0 0 ${n} 100`} preserveAspectRatio="none" className="w-full h-24 block" role="img" aria-label="Voice waveform with synthetic segments marked">
        {timeline.filter((w) => w.p_fake >= 0.5).map((w, i) => (
          <rect key={i} x={(w.start / duration) * n} width={((w.end - w.start) / duration) * n} y="0" height="100" fill="var(--color-high)" opacity={0.12 + 0.3 * w.p_fake} />
        ))}
        {peaks.map((p, i) => <line key={i} x1={i + 0.5} x2={i + 0.5} y1={50 - p * 46} y2={50 + p * 46} stroke="var(--color-ink)" strokeWidth="0.6" vectorEffect="non-scaling-stroke" />)}
        {frames.map((f, i) => <circle key={"f" + i} cx={(f.t / duration) * n} cy="96" r="1.6" fill={f.p_fake >= 0.5 ? "var(--color-high)" : "var(--color-low)"} />)}
      </svg>
      <figcaption className="flex justify-between text-xs text-ink-soft mt-1 tnum">
        <span>0s</span><span>Shaded red: voice sounds synthetic. Dots: face frames checked.</span><span>{Math.round(duration)}s</span>
      </figcaption>
    </figure>
  );
}

// The answer first, for someone who only wants to know whether to act: the band, one reason, Accept or Reject.
// Everything else waits behind "Show details". Accepting a MEDIUM or HIGH result asks the real person first.
const BAND_BG = { LOW: "bg-low", MEDIUM: "bg-medium", HIGH: "bg-high" };
const ANSWER = { HIGH: "Don't act on this.", MEDIUM: "Pause and verify first.", LOW: "Looks safe to go ahead." };

function ResultCard({ r, status, delivery, dismissed, open, onAccept, onReject, onVerify, onToggle }) {
  const [confirming, setConfirming] = useState(false);
  const who = r.claimed_person?.name.split(" ")[0];
  // plain words only: what it looks like and what to do; the technical evidence lives under "Show details"
  const t = r.scam_types?.[0];
  const reason = r.band === "LOW" ? (r.synthetic_media ? "The media looks synthetic, but nothing risky is being asked." : "No warning signs in the voice, face, words or request.")
    : t ? `Looks like ${t.label.replace(/\s*\(.*\)$/, "").toLowerCase()}. ${t.advice}`
    : r.synthetic_media ? `The voice or face looks fake. ${r.recommended_actions[0] || ""}`
    : r.recommended_actions[0] || "Check with the real person on a number you already know.";
  const done = status === "verified" ? ["text-low", "Accepted. The case is closed as verified."]
    : status === "confirmed_attack" ? ["text-high", "Rejected and reported as a scam. Don't reply, pay or share anything."]
    : dismissed ? ["text-ink-soft", "Rejected. Nothing was reported."] : null;
  const big = "btn h-12 text-[15px] w-full";

  return (
    <section className="glass-strong overflow-hidden !p-0" aria-live="polite">
      <div className={`${BAND_BG[r.band]} text-white px-6 py-5 flex items-center justify-between gap-4`}>
        <div className="min-w-0">
          <p className="text-[12.5px] font-bold uppercase tracking-[0.16em] opacity-90">{r.band} risk</p>
          <p className="display text-[30px] sm:text-[36px] font-extrabold leading-[1.05] tracking-tight">{ANSWER[r.band]}</p>
        </div>
        <p className="display text-[44px] font-extrabold leading-none tnum shrink-0">{Math.floor(r.risk)}<span className="text-[15px] font-semibold opacity-80">/100</span></p>
      </div>
      <div className="p-6 space-y-5">
        <p className="text-[17px] leading-relaxed max-w-prose">{reason}</p>
        {r.hold_until && !done && r.band === "HIGH" && <p className="text-[14px] font-semibold text-high">The payment is on hold for 30 minutes.</p>}
        {done ? <p className={`text-[16px] font-bold ${done[0]}`}>{done[1]}</p>
          : status === "verifying" ? (
            <div className="space-y-3">
              <p className="text-[16px] font-semibold">Waiting for {who || "the real person"} to answer YES or NO on their own phone…</p>
              <SendLinks delivery={delivery} who={who || "them"} qr={delivery?.link} qrLabel="In the room? Scan to answer" />
            </div>
          ) : confirming ? (
            <div className="rounded-xl border border-rule p-4 space-y-3">
              <p className="text-[15px]">TrustCheck rates this <b className={BAND_TEXT[r.band]}>{r.band}</b>. Only accept once the real person confirms it was them.</p>
              <div className="flex flex-wrap gap-2">
                {r.claimed_person && <button type="button" onClick={onVerify} className="btn btn-primary">Ask {who} to confirm</button>}
                <button type="button" onClick={onAccept} className="btn btn-plain">Accept anyway</button>
                <button type="button" onClick={() => setConfirming(false)} className="btn btn-plain">Back</button>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-3">
              <button type="button" onClick={r.band === "LOW" ? onAccept : () => setConfirming(true)} className={`${big} ${r.band === "LOW" ? "btn-primary" : "btn-plain"}`}>Accept</button>
              <button type="button" onClick={onReject} className={`${big} ${r.band === "LOW" ? "btn-plain" : "text-white bg-high hover:brightness-110"}`}>Reject</button>
            </div>
          )}
        <button type="button" onClick={onToggle} aria-expanded={open} className="text-[14px] font-semibold text-night underline-offset-4 hover:underline">
          {open ? "Hide details" : "Show details: why, evidence and next steps"}
        </button>
      </div>
    </section>
  );
}

export default function Verdict({ result: r, caseId, initialStatus = "open", simple = true }) {
  const [status, setStatus] = useState(initialStatus);
  const [msg, setMsg] = useState("");
  const [delivery, setDelivery] = useState(null);
  const [open, setOpen] = useState(!simple);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    if (status !== "verifying") return;
    const t = setInterval(async () => { const c = await api(`/cases/${caseId}`); if (c.status !== "verifying") setStatus(c.status); }, 2000);
    return () => clearInterval(t);
  }, [status, caseId]);

  const run = async (fn) => { setMsg(""); try { await fn(); } catch (e) { setMsg(e.message); } };
  const verify = () => run(async () => { const c = await api(`/verify/${caseId}`, { method: "POST" }); setDelivery(c.delivery); setStatus(c.status); });
  const decide = (answer) => run(async () => setStatus((await api(`/cases/${caseId}/decision`, { method: "POST", body: form({ answer }) })).status));
  const download = () => run(async () => {
    const text = await api(`/cases/${caseId}/report`);
    Object.assign(document.createElement("a"), { href: URL.createObjectURL(new Blob([text], { type: "text/markdown" })), download: `cert-in-${caseId}.md` }).click();
  });
  const duration = r.duration || 1;
  // Reject on LOW only dismisses: a harmless sender must never land on the mule blocklist.
  const reject = () => (r.band === "LOW" ? setDismissed(true) : decide("no"));

  const card = simple && (
    <ResultCard r={r} status={status} delivery={delivery} dismissed={dismissed} open={open}
      onAccept={() => decide("yes")} onReject={reject} onVerify={verify} onToggle={() => setOpen(!open)} />
  );
  if (simple && !open) return <article className="space-y-3">{card}{msg && <p className="text-sm text-high">{msg}</p>}</article>;

  return (
    <article className="space-y-6">
      {card}
      <header className="grid sm:grid-cols-[auto_1fr] gap-6 items-start">
        <Stamp band={r.band} risk={r.risk} />
        <div>
          <p className="display text-[28px] font-bold tracking-tight leading-tight">{r.band === "LOW" && r.synthetic_media ? "Synthetic media, but nothing risky is asked." : HEADLINE[r.band]}</p>
          {r.synthetic_media && <p className="inline-block mt-2 text-[12.5px] font-semibold text-white bg-high rounded-md px-2 py-0.5">Synthetic media detected</p>}
          {r.scam_types?.length > 0 && <p className="mt-2 flex flex-wrap gap-2">{r.scam_types.map((t) => <span key={t.type} className="text-[12.5px] font-semibold text-night bg-night/10 rounded-md px-2 py-0.5">Looks like: {t.label}</span>)}</p>}
          <ul className="mt-3 space-y-1 max-w-prose text-[14px]">
            {r.signals.filter((x) => x.contribution > 0).slice(0, 3).map((x) => x.why).map((w) => (
              <li key={w} className="flex gap-2.5"><span aria-hidden className={`mt-[0.55em] size-1.5 shrink-0 rounded-full ${r.band === "LOW" ? "bg-low" : r.band === "MEDIUM" ? "bg-medium" : "bg-high"}`} /><span>{w[0].toUpperCase() + w.slice(1)}</span></li>
            ))}
            {!r.signals.some((x) => x.contribution > 0) && <li>No strong warning signs in the voice, face, words or request.</li>}
          </ul>
          <p className="text-sm text-ink-soft mt-3">
            {r.claimed_person ? `Claims to be ${r.claimed_person.name}${r.claimed_person.role ? `, ${r.claimed_person.role}` : ""}. ` : ""}
            Asks for: {r.action.replace("_high", " (high value)").replace("_", " ")}.
            {r.campaign && <span className="text-high font-semibold"> Same voice seen in {r.campaign.size - 1} earlier case{r.campaign.size > 2 ? "s" : ""}: likely a campaign.</span>}
          </p>
        </div>
      </header>

      <section className="glass-strong p-5 space-y-4">
        {r.hold_until && caseId && <HoldLock until={r.hold_until} status={status} />}
        <h3 className="text-[17px] font-bold">What to do now</h3>
        <ul className="space-y-2">{r.recommended_actions.map((a) => <li key={a} className="flex gap-3 items-start"><span aria-hidden className={`mt-2 size-2 rounded-full shrink-0 ${r.band === "LOW" ? "bg-low" : r.band === "MEDIUM" ? "bg-medium" : "bg-high"}`} />{a}</li>)}</ul>
        <Share r={r} />
        {r.challenge && <p className="font-semibold rounded-[10px] bg-night text-white px-4 py-3">On the call, try this: {r.challenge}</p>}
        {r.band !== "LOW" && r.claimed_person && (status === "open" || status === "verifying") && <CodeWordCheck person={r.claimed_person} />}
        {caseId && (
          <>
            <AnimatePresence mode="wait">
              <motion.p key={status} initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} aria-live="polite"
                className={`font-semibold ${status === "confirmed_attack" ? "text-high" : status === "verified" ? "text-low" : "text-ink-soft"}`}>{STATUS[status]}</motion.p>
            </AnimatePresence>
            {(status === "open" || status === "verifying") && (
              <div className="space-y-4">
                {status === "verifying" && delivery && <SendLinks delivery={delivery} who={r.claimed_person?.name.split(" ")[0] || "them"} qr={delivery.link} qrLabel="In the room? Scan to answer" />}
                {r.band !== "LOW" && r.claimed_person && <button onClick={verify} className="btn btn-primary">{status === "verifying" ? "Ask again" : "Ask the real person"}</button>}
                <div className="flex flex-wrap items-center gap-2 text-sm">
                  <span className="text-ink-soft mr-1">Checked another way, like a call to their registered number? Record their answer:</span>
                  <button onClick={() => decide("yes")} className="btn btn-plain h-8">It was them</button>
                  <button onClick={() => decide("no")} className="btn btn-plain h-8 text-high">It wasn't them</button>
                </div>
              </div>
            )}
            {status !== "verified" && r.band !== "LOW" && (
              <div className={`flex flex-wrap items-center gap-3 ${status === "confirmed_attack" ? "" : "text-sm"}`}>
                <button onClick={download} className={status === "confirmed_attack" ? "btn text-white bg-high hover:brightness-110" : "btn btn-plain"}>
                  Download CERT-In incident report
                </button>
                <span className="text-ink-soft text-sm max-w-sm">A pre-filled draft for India's cyber-security agency, which needs incidents reported within 6 hours.</span>
              </div>
            )}
            {msg && <p className="text-sm text-high">{msg}</p>}
          </>
        )}
      </section>

      {r.band === "HIGH" && caseId && <DecoyPanel caseId={caseId} initial={r.decoy} />}

      {r.rules_fired.length > 0 && (
        <section>
          <h3 className="label mb-1.5 px-1">Policy rules that set a minimum</h3>
          <ul className="glass divide-y divide-ink/[0.07]">{r.rules_fired.map((x) => <li key={x} className="px-4 py-2.5">{x}</li>)}</ul>
        </section>
      )}

      <section>
        <h3 className="label mb-1.5 px-1">Why this score</h3>
        <div className="glass p-4">
        <p className="text-[12.5px] text-ink-soft mb-3 max-w-prose">
          Right of the line pushes towards an attack; left is evidence it's genuine. Click a row for its evidence. The total is multiplied by the
          impact of what's being asked ({r.impact} × for {r.action.replace("_high", " (high value)").replace("_", " ")}).
        </p>
        <Waterfall rows={r.signals.map((s) => ({ ...s }))} />
        </div>
      </section>

      {(r.peaks?.length > 0 || r.frames?.length > 0) && (
        <section>
          <h3 className="label mb-1.5 px-1">The recording</h3>
          <div className="glass p-4">
          <Waveform peaks={r.peaks} timeline={r.timeline} frames={r.frames} duration={duration} />
          {r.transcript?.text && <p className="mt-3 text-ink-soft max-w-prose"><span className="font-semibold text-ink">Heard ({r.transcript.language}):</span> {r.transcript.text}</p>}
          </div>
        </section>
      )}

      {r.message?.text && (
        <section>
          <h3 className="label mb-1.5 px-1">The words, with manipulation underlined</h3>
          {r.message.tactics?.length > 0 && <p className="text-[12.5px] text-ink-soft mb-2 px-1">Found {r.message.tactics.map((t) => TACTIC[t]).join(", ")}. Hover an underline to see which.</p>}
          <div className="glass p-5"><Highlighted text={r.message.text} spans={r.message.highlights} /></div>
        </section>
      )}

      {r.errors?.length > 0 && (
        <details className="text-sm text-ink-soft">
          <summary className="cursor-pointer">{r.errors.length} check{r.errors.length > 1 ? "s" : ""} couldn't run on this input</summary>
          <ul className="list-disc pl-5 mt-1">{r.errors.map((e) => <li key={e}>{e}</li>)}</ul>
        </details>
      )}
    </article>
  );
}
