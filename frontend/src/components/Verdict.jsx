import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { useEffect, useState } from "react";
import { api, form } from "../lib/api.js";
import { CodeWordCheck, DecoyPanel, HoldLock, SendLinks } from "./Defense.jsx";
import Icon from "./Icons.jsx";

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
    <motion.div key={band + r} className={`glass-strong rounded-[2rem] px-6 pt-4 pb-6 inline-flex flex-col min-w-[13rem] ${className}`}
      initial={reduce ? false : { scale: 0.92, opacity: 0, y: 10 }} animate={{ scale: 1, opacity: 1, y: 0 }}
      transition={{ type: "spring", stiffness: 380, damping: 26 }}>
      <span className={`text-base font-bold ${BAND_TEXT[band]}`}>{band}</span>
      <span className={`${size} font-extrabold leading-[0.95] tracking-tight tnum ${BAND_TEXT[band]}`}>
        {r}<span className="text-[0.28em] font-semibold text-ink-soft"> risk / 100</span>
      </span>
      <span className="relative mt-4 h-2.5 rounded-full heat-scale" aria-hidden>
        <motion.span className="absolute top-1/2 size-5 -translate-y-1/2 -translate-x-1/2 rounded-full bg-white ring-[5px] ring-night shadow"
          initial={reduce ? false : { left: "0%" }} animate={{ left: `${Math.min(97, Math.max(3, r))}%` }}
          transition={{ type: "spring", stiffness: 90, damping: 18 }} />
      </span>
    </motion.div>
  );
}

// Scams spread by forward, so should the warning. Plus read-aloud for anyone who'd rather listen.
function Share({ r }) {
  const [speaking, setSpeaking] = useState(false);
  const [shared, setShared] = useState("");
  const scam = r.scam_types?.[0];
  if (r.band === "LOW" || !scam) return null;
  const warning = `Scam alert: "${scam.label}" messages are going around. ${scam.advice} Never act on a message like this without checking. Report: 1930 / cybercrime.gov.in`;
  const share = async () => {
    try {
      if (navigator.share) { await navigator.share({ title: "Scam alert", text: warning }); setShared("Shared"); }
      else { await navigator.clipboard.writeText(warning); setShared("Copied: paste it in any chat"); }
    } catch { /* share sheet closed */ }
  };
  const say = () => {
    const s = window.speechSynthesis;
    if (!s) return;
    if (speaking) { s.cancel(); setSpeaking(false); return; }
    const u = new SpeechSynthesisUtterance(`${HEADLINE[r.band]} ${r.recommended_actions.join(". ")}`);
    u.onend = () => setSpeaking(false);
    s.speak(u); setSpeaking(true);
  };
  return (
    <div className="flex flex-wrap gap-2">
      <button type="button" onClick={share} className="bg-night text-white rounded-full px-4 py-2 text-sm font-semibold">{shared || "Share warning with family"}</button>
      <button type="button" onClick={say} className="bg-white/80 border border-white rounded-full px-4 py-2 text-sm font-semibold">{speaking ? "Stop" : "Read it out loud"}</button>
    </div>
  );
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
  return <p className="whitespace-pre-wrap leading-[1.8] text-lg max-w-prose">{parts}</p>;
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

export default function Verdict({ result: r, caseId, initialStatus = "open" }) {
  const [status, setStatus] = useState(initialStatus);
  const [msg, setMsg] = useState("");
  const [delivery, setDelivery] = useState(null);

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

  return (
    <article className="space-y-10">
      <header className="grid sm:grid-cols-[auto_1fr] gap-8 items-center">
        <Stamp band={r.band} risk={r.risk} />
        <div>
          <p className="wide text-3xl font-extrabold leading-tight">{r.band === "LOW" && r.synthetic_media ? "Synthetic media, but nothing risky is asked." : HEADLINE[r.band]}</p>
          {r.synthetic_media && <p className="inline-block mt-2 text-sm font-bold text-white bg-high rounded-full px-3 py-1">Synthetic media detected</p>}
          {r.scam_types?.length > 0 && <p className="mt-2 flex flex-wrap gap-2">{r.scam_types.map((t) => <span key={t.type} className="text-sm font-bold text-white bg-night rounded-full px-3 py-1">Looks like: {t.label}</span>)}</p>}
          <ul className="mt-3 space-y-1.5 max-w-prose">
            {[...r.signals.filter((x) => x.contribution > 0).slice(0, 4).map((x) => x.why), ...r.rules_fired.map((x) => "Policy: " + x)].map((w) => (
              <li key={w} className="flex gap-2.5"><span aria-hidden className={`${BAND_TEXT[r.band]} font-bold`}>!</span><span>{w[0].toUpperCase() + w.slice(1)}</span></li>
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

      <section className="glass-strong rounded-[2rem] p-6 sm:p-7 space-y-5">
        {r.hold_until && caseId && <HoldLock until={r.hold_until} status={status} />}
        <h3 className="text-xl font-bold">What to do now</h3>
        <ul className="space-y-2">{r.recommended_actions.map((a) => <li key={a} className="flex gap-3 items-start"><span aria-hidden className={`mt-2 size-2 rounded-full shrink-0 ${r.band === "LOW" ? "bg-low" : r.band === "MEDIUM" ? "bg-medium" : "bg-high"}`} />{a}</li>)}</ul>
        <Share r={r} />
        {r.challenge && <p className="text-lg font-semibold rounded-2xl bg-night text-white px-5 py-4">On the call, try this: {r.challenge}</p>}
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
                {r.band !== "LOW" && r.claimed_person && <button onClick={verify} className="bg-night text-white pl-5 pr-2 py-2 rounded-full font-semibold hover:bg-night-2 inline-flex items-center gap-3">{status === "verifying" ? "Ask again" : "Ask the real person"}<span className="orb size-8 bg-white text-night"><Icon name="arrow" className="size-4" /></span></button>}
                <div className="flex flex-wrap items-center gap-2 text-sm">
                  <span className="text-ink-soft mr-1">Checked another way, like a call to their registered number? Record their answer:</span>
                  <button onClick={() => decide("yes")} className="bg-white/80 border border-white px-4 py-2 rounded-full font-semibold hover:bg-white">It was them</button>
                  <button onClick={() => decide("no")} className="bg-white/80 border border-white text-high px-4 py-2 rounded-full font-semibold hover:bg-white">It wasn't them</button>
                </div>
              </div>
            )}
            {status !== "verified" && r.band !== "LOW" && (
              <div className={`flex flex-wrap items-center gap-3 ${status === "confirmed_attack" ? "" : "text-sm"}`}>
                <button onClick={download} className={status === "confirmed_attack"
                  ? "bg-high text-white pl-5 pr-2 py-2 rounded-full font-semibold inline-flex items-center gap-3"
                  : "font-semibold underline underline-offset-4"}>
                  Download CERT-In incident report{status === "confirmed_attack" && <span className="orb size-8 bg-white text-high"><Icon name="arrow" className="size-4" /></span>}
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
          <h3 className="text-lg font-bold">Policy rules that set a minimum</h3>
          <ul className="mt-2 space-y-1">{r.rules_fired.map((x) => <li key={x}>{x}</li>)}</ul>
        </section>
      )}

      <section>
        <h3 className="text-lg font-bold">Why this score</h3>
        <p className="text-sm text-ink-soft mb-3 max-w-prose">
          Right of the line pushes towards an attack; left is evidence it's genuine. Click a row for its evidence. The total is multiplied by the
          impact of what's being asked ({r.impact} × for {r.action.replace("_high", " (high value)").replace("_", " ")}).
        </p>
        <Waterfall rows={r.signals.map((s) => ({ ...s }))} />
      </section>

      {(r.peaks?.length > 0 || r.frames?.length > 0) && (
        <section>
          <h3 className="text-lg font-bold mb-2">The recording</h3>
          <Waveform peaks={r.peaks} timeline={r.timeline} frames={r.frames} duration={duration} />
          {r.transcript?.text && <p className="mt-3 text-ink-soft max-w-prose"><span className="font-semibold text-ink">Heard ({r.transcript.language}):</span> {r.transcript.text}</p>}
        </section>
      )}

      {r.message?.text && (
        <section>
          <h3 className="text-lg font-bold">The words, with manipulation underlined</h3>
          {r.message.tactics?.length > 0 && <p className="text-sm text-ink-soft mb-3">Found {r.message.tactics.map((t) => TACTIC[t]).join(", ")}. Hover an underline to see which.</p>}
          <div className="glass-strong rounded-[2rem] p-6"><Highlighted text={r.message.text} spans={r.message.highlights} /></div>
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
