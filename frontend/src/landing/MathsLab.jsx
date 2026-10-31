import { useMemo, useState } from "react";
import { Stamp, Waterfall } from "../components/Verdict.jsx";
import { fuse, IMPACT, IMPACT_LABEL } from "../lib/fusion.js";

const SIGNALS = [
  ["audio_spoof", "Voice sounds synthetic"],
  ["voice_mismatch", "Voice ≠ enrolled CFO"],
  ["face_video", "Face looks swapped"],
  ["message_tactics", "Manipulative wording"],
  ["context_anomaly", "Out-of-pattern request"],
  ["lookalike_domain", "Lookalike sender domain"],
];

const PRESETS = {
  "Fake CFO wire": { s: { audio_spoof: .88, voice_mismatch: .85, face_video: .74, message_tactics: .92, context_anomaly: .9, lookalike_domain: .95 }, action: "payment_high", unreg: true },
  "Same fake, birthday wish": { s: { audio_spoof: .88, voice_mismatch: .85, face_video: .74, message_tactics: .10, context_anomaly: .5, lookalike_domain: .5 }, action: "none", unreg: false },
  "A perfect fake": { s: { audio_spoof: .30, voice_mismatch: .20, face_video: .40, message_tactics: .92, context_anomaly: .9, lookalike_domain: .5 }, action: "payment_high", unreg: true },
};

export default function MathsLab() {
  const [preset, setPreset] = useState("Fake CFO wire");
  const [s, setS] = useState(PRESETS[preset].s);
  const [action, setAction] = useState(PRESETS[preset].action);
  const [unreg, setUnreg] = useState(PRESETS[preset].unreg);
  const pick = (k) => { setPreset(k); setS(PRESETS[k].s); setAction(PRESETS[k].action); setUnreg(PRESETS[k].unreg); };

  const r = useMemo(() => fuse(SIGNALS.map(([k, label]) => ({ signal: k, label, score: s[k] })), action, { unregistered_channel: unreg }), [s, action, unreg]);
  const evidence = r.signals.reduce((a, x) => a + x.contribution, 0);
  const raw = 100 * r.threat * r.impact;

  return (
    <div className="grid lg:grid-cols-[1fr_1.1fr] gap-12 items-start">
      <div className="space-y-6 glass rounded-[2rem] p-6 sm:p-7">
        <div className="flex flex-wrap gap-2" role="group" aria-label="Scenarios">
          {Object.keys(PRESETS).map((k) => (
            <button key={k} onClick={() => pick(k)} aria-pressed={preset === k}
              className={`px-4 py-2 rounded-full border text-sm font-semibold ${preset === k ? "bg-night text-white border-night" : "bg-white/70 border-white hover:bg-white"}`}>{k}</button>
          ))}
        </div>
        <div className="space-y-3">
          {SIGNALS.map(([k, label]) => (
            <label key={k} className="grid grid-cols-[11rem_1fr_2.5rem] items-center gap-3 text-sm">
              <span className="font-medium">{label}</span>
              <input type="range" min="0.01" max="0.99" step="0.01" value={s[k]} onChange={(e) => { setPreset(""); setS({ ...s, [k]: +e.target.value }); }} />
              <span className="tnum text-right">{s[k].toFixed(2)}</span>
            </label>
          ))}
        </div>
        <fieldset>
          <legend className="text-sm font-medium mb-2">What it asks you to do</legend>
          <div className="flex flex-wrap gap-1.5">
            {Object.keys(IMPACT).map((k) => (
              <button key={k} onClick={() => { setPreset(""); setAction(k); }} aria-pressed={action === k}
                className={`px-3.5 py-1.5 rounded-full text-sm border font-semibold ${action === k ? "bg-night text-white border-night" : "border-white bg-white/70 hover:bg-white"}`}>{IMPACT_LABEL[k]}</button>
            ))}
          </div>
        </fieldset>
        <label className="flex items-center gap-3 text-sm font-medium cursor-pointer">
          <input type="checkbox" checked={unreg} onChange={(e) => { setPreset(""); setUnreg(e.target.checked); }} className="size-4 accent-night" />
          Arrives from a number or app the person doesn't normally use
        </label>
      </div>

      <div className="glass-strong rounded-[2rem] p-6 sm:p-8 space-y-6 lg:sticky lg:top-8">
        <div className="flex items-center gap-6 flex-wrap">
          <Stamp band={r.band} risk={r.risk} size="text-6xl" className="!bg-white" />
          <p className="text-sm text-ink-soft tnum leading-relaxed">
            Evidence {evidence >= 0 ? "+" : ""}{evidence.toFixed(2)} and prior {r.prior_logodds} give a threat probability of {(r.threat * 100).toFixed(1)}%.
            <br />× impact {r.impact} = <b className="text-ink">{raw.toFixed(1)}</b>
            {r.rules_fired.length > 0 && raw < 60 && <><br /><b className="text-high">A policy rule lifts it to 60: verify before paying.</b></>}
          </p>
        </div>
        <Waterfall rows={r.signals} max={3.5} />
      </div>
    </div>
  );
}
