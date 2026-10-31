import { AnimatePresence, motion } from "framer-motion";
import { lazy, Suspense, useEffect, useRef, useState } from "react";
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
    <div className="space-y-8">
      <div className="relative rounded-xl bg-night text-paper overflow-hidden h-72">
        {running && <Suspense fallback={null}><Spectrogram3D alert={alert} className="absolute inset-0" /></Suspense>}
        <div className="relative z-10 p-6 h-full flex flex-col">
          <h2 className="wide text-3xl font-extrabold">Live call guard</h2>
          <p className="text-paper/70 mt-1 max-w-md">{running ? "Listening alongside you. A reading lands every 3 seconds." : "Open the Meet, Zoom or Teams call in another tab, then share that tab here."}</p>
          <div className="mt-auto flex flex-wrap items-end gap-3">
            <label className="text-sm">The caller claims to be
              <select value={claimed} onChange={(e) => setClaimed(e.target.value)} disabled={running} className="block mt-1 bg-night-2 border border-paper/25 rounded px-3 py-2 min-w-56">
                <option value="">Unknown</option>
                {people.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            </label>
            {running
              ? <button onClick={() => stop.current()} className="border border-paper/60 px-5 py-2.5 rounded font-semibold">Stop listening</button>
              : <button onClick={start} className="bg-mint text-night px-5 py-2.5 rounded font-bold">Listen to a call tab</button>}
          </div>
        </div>
      </div>
      {error && <p className="text-high" role="alert">{error}</p>}

      <AnimatePresence>
        {state && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="grid lg:grid-cols-[auto_1fr] gap-10 items-start">
            <Stamp band={state.band} risk={state.risk} />
            <div className="space-y-5 min-w-0">
              <p className="text-2xl max-w-prose">{state.summary}</p>
              <AnimatePresence mode="wait">
                {state.challenge && (
                  <motion.p key={state.challenge} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0 }}
                    className="text-xl font-bold border-l-4 border-stamp pl-4">Try this now: {state.challenge}</motion.p>
                )}
              </AnimatePresence>
              {state.tactics.length > 0 && <p className="text-ink-soft">Heard: {state.tactics.map((t) => TACTIC[t]).join(", ")}</p>}
              <div className="flex gap-[2px] h-8 items-end" aria-label="Voice segments, newest on the right">
                {state.timeline.map((w, i) => (
                  <motion.span key={w.start + "-" + i} initial={{ scaleY: 0 }} animate={{ scaleY: 1 }} style={{ originY: 1, height: `${30 + w.p_fake * 70}%` }}
                    title={`${w.start}s: p(fake) ${w.p_fake}`} className={`flex-1 rounded-sm ${w.p_fake >= 0.5 ? "bg-high" : "bg-low"}`} />
                ))}
              </div>
              <p className="text-ink-soft whitespace-pre-wrap max-w-prose">{state.transcript || "No speech recognised yet."}</p>
              <p className="text-xs text-ink-soft tnum">{state.seconds}s analysed</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
