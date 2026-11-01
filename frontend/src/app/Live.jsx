import { AnimatePresence, motion } from "framer-motion";
import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { CodeWordCheck } from "../components/Defense.jsx";
import { Stamp } from "../components/Verdict.jsx";
import { api, WS } from "../lib/api.js";

const Spectrogram3D = lazy(() => import("../components/Spectrogram3D.jsx"));
const TACTIC = { urgency: "urgency", secrecy: "secrecy", authority: "authority claim", payment_request: "payment request", credential_request: "OTP or password request", channel_switch: "channel switch", new_beneficiary: "new account", fear_threat: "threat", reward: "reward bait" };

// Same backend stream as the Chrome extension. Chrome asks which tab to share; tick "Also share tab audio".
export default function Live() {
  const [people, setPeople] = useState([]);
  const [claimed, setClaimed] = useState("");
  const [state, setState] = useState(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const stop = useRef(() => {});

  useEffect(() => { api("/people").then(setPeople).catch(() => {}); return () => stop.current(); }, []);

  async function start() {
    setError(""); setState(null);
    try {
      const stream = await navigator.mediaDevices.getDisplayMedia({ video: true, audio: true });
      const audio = new MediaStream(stream.getAudioTracks());
      if (!audio.getAudioTracks().length) { stream.getTracks().forEach((t) => t.stop()); throw new Error('No audio came through. Choose the call tab and tick "Also share tab audio".'); }
      const ws = new WebSocket(`${WS}/live/${crypto.randomUUID()}?channel=meet${claimed ? `&claimed_person_id=${claimed}` : ""}`);
      ws.onmessage = (e) => setState(JSON.parse(e.data));
      ws.onerror = () => setError("Lost the connection to the backend on port 8000.");
      const rec = new MediaRecorder(audio, { mimeType: "audio/webm;codecs=opus" });
      rec.ondataavailable = (e) => ws.readyState === 1 && e.data.size && ws.send(e.data);
      ws.onopen = () => rec.start(3000);
      stop.current = () => { rec.state !== "inactive" && rec.stop(); stream.getTracks().forEach((t) => t.stop()); ws.close(); setRunning(false); };
      stream.getVideoTracks()[0].onended = () => stop.current();
      setRunning(true);
    } catch (e) { setError(e.message); }
  }

  const alert = state ? { LOW: 0, MEDIUM: 0.5, HIGH: 1 }[state.band] : 0;
  return (
    <div className="space-y-6">
      <div className="relative frame dusk overflow-hidden h-80">
        <Suspense fallback={null}><Spectrogram3D alert={alert} className={`absolute inset-x-0 bottom-0 top-[25%] transition-opacity duration-700 ${running ? "opacity-100" : "opacity-70"}`} /></Suspense>
        <div className="relative z-10 p-6 sm:p-8 h-full flex flex-col">
          <h2 className="text-4xl font-bold tracking-[-0.03em] text-white drop-shadow-[0_2px_24px_rgb(35_22_94/0.25)]">Live call guard</h2>
          <p className="mt-2 max-w-md font-semibold">{running ? "Listening alongside you. A reading lands every 3 seconds." : "Open the Meet, Zoom or Teams call in another tab, then share that tab here."}</p>
          <div className="mt-auto flex flex-wrap items-end gap-3 rounded-[12px] bg-white/80 backdrop-blur-xl p-3 self-start shadow-[0_10px_30px_-14px_rgb(35_22_94/0.5)]">
            <label className="label pl-1">The caller claims to be
              <select value={claimed} onChange={(e) => setClaimed(e.target.value)} disabled={running} className="field block mt-1 min-w-56">
                <option value="">Unknown</option>
                {people.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            </label>
            {running
              ? <button onClick={() => stop.current()} className="btn btn-plain h-9">Stop listening</button>
              : <button onClick={start} className="btn btn-primary h-9">Listen to a call tab</button>}
          </div>
        </div>
      </div>
      {error && <p className="text-high" role="alert">{error}</p>}
      {!state && !running && (
        <ol className="glass grid sm:grid-cols-3 divide-y sm:divide-y-0 sm:divide-x divide-ink/[0.07]">
          {[["Open the call", "Join the Meet, Zoom or Teams call in another Chrome tab."],
            ["Share that tab", "Press Listen, pick the call tab and tick \"Also share tab audio\"."],
            ["Watch the reading", "Every 3 seconds: cloned voice, voiceprint, what's being asked, and a challenge to try."]].map(([h, t], i) => (
            <li key={h} className="p-4 flex gap-3">
              <span className="orb size-6 shrink-0 bg-night/10 text-night text-[12px] font-bold tnum">{i + 1}</span>
              <span><span className="block font-semibold">{h}</span><span className="block text-[13px] text-ink-soft mt-0.5">{t}</span></span>
            </li>))}
        </ol>
      )}
      {claimed && <CodeWordCheck person={people.find((p) => p.id === claimed)} compact />}

      <AnimatePresence>
        {state && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="grid lg:grid-cols-[auto_1fr] gap-10 items-start">
            <Stamp band={state.band} risk={state.risk} />
            <div className="space-y-4 min-w-0 glass p-5">
              <p className="text-[17px] leading-snug max-w-prose">{state.summary}</p>
              <AnimatePresence mode="wait">
                {state.challenge && (
                  <motion.p key={state.challenge} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0 }}
                    className="font-semibold rounded-[10px] bg-night text-white px-4 py-3">Try this now: {state.challenge}</motion.p>
                )}
              </AnimatePresence>
              {state.tactics.length > 0 && <p className="text-ink-soft">Heard: {state.tactics.map((t) => TACTIC[t]).join(", ")}</p>}
              <div className="flex gap-[2px] h-8 items-end" aria-label="Voice segments, newest on the right">
                {state.timeline.map((w, i) => (
                  <motion.span key={w.start + "-" + i} initial={{ scaleY: 0 }} animate={{ scaleY: 1 }} style={{ originY: 1, height: `${30 + w.p_fake * 70}%` }}
                    title={`${w.start}s: p(fake) ${w.p_fake}`} className={`flex-1 rounded-sm ${w.p_fake >= 0.5 ? "bg-high" : "bg-low"}`} />
                ))}
              </div>
              {state.timeline.length > 0 && (
                <p className="text-xs text-ink-soft -mt-2">
                  Each block is a slice of the caller's voice, newest on the right: <span className="text-high font-semibold">red sounds AI-generated</span>, <span className="text-low font-semibold">teal sounds human</span>. Taller means more sure.
                </p>
              )}
              <p className="text-ink-soft whitespace-pre-wrap max-w-prose">{state.transcript || "No speech recognised yet."}</p>
              <p className="text-xs text-ink-soft tnum">{state.seconds}s analysed</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
