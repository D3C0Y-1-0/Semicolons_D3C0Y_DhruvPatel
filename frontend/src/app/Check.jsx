import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import Verdict from "../components/Verdict.jsx";
import { api, form } from "../lib/api.js";
import { SAMPLES } from "../lib/samples.js";

import DuskScene from "../components/DuskScene.jsx";
const CHANNELS = ["email", "whatsapp", "phone", "sms", "meet", "teams", "zoom"];
const mod = typeof navigator !== "undefined" && /Mac|iPhone|iPad/.test(navigator.platform) ? "⌘" : "Ctrl";

function DropZone({ file, setFile }) {
  const [over, setOver] = useState(false);
  const input = useRef();
  const url = file ? URL.createObjectURL(file) : null;
  const kind = file?.type.split("/")[0];
  return (
    <div onDragOver={(e) => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)}
      onDrop={(e) => { e.preventDefault(); setOver(false); e.dataTransfer.files[0] && setFile(e.dataTransfer.files[0]); }}
      className={`rounded-[10px] border border-dashed px-4 py-3.5 transition-colors ${over ? "border-night bg-night/5" : "border-ink/20 bg-[#faf9fd]"}`}>
      {!file ? (
        <button type="button" onClick={() => input.current.click()} className="w-full text-left">
          <span className="font-semibold block">Add a screenshot, voice note or video</span>
          <span className="text-[12.5px] text-ink-soft">Drop it here or click. A screenshot of the chat is read as text; .opus, .mp3, .mp4, .jpg all work.</span>
        </button>
      ) : (
        <div className="space-y-2">
          {kind === "audio" && <audio src={url} controls className="w-full h-9" />}
          {kind === "video" && <video src={url} controls className="w-full rounded-lg max-h-44" />}
          {kind === "image" && <img src={url} alt="Uploaded" className="max-h-36 rounded-lg" />}
          <div className="flex justify-between text-[12.5px]"><span className="truncate">{file.name}</span>
            <button type="button" onClick={() => setFile(null)} className="text-night font-semibold shrink-0 ml-3">Remove</button></div>
        </div>
      )}
      <input ref={input} type="file" accept="audio/*,video/*,image/*" hidden onChange={(e) => e.target.files[0] && setFile(e.target.files[0])} />
    </div>
  );
}

export default function Check() {
  const [people, setPeople] = useState([]);
  const [v, setV] = useState({ text: "", channel: "email", sender: "", claimed_person_id: "" });
  const [sample, setSample] = useState("");
  const [file, setFile] = useState(null);
  const [eml, setEml] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const formRef = useRef();
  const set = (k) => (e) => { setV({ ...v, [k]: e.target.value }); if (k === "text") setSample(""); };

  useEffect(() => { api("/people").then(setPeople).catch(() => {}); }, []);
  // on a phone the result sits under the form: take the person straight to the answer
  const resultRef = useRef();
  useEffect(() => {
    if (!result || innerWidth >= 1024) return;
    // wait for the "checking" panel to leave and the card to mount, or the layout shift cuts the scroll short
    const t = setTimeout(() => resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 450);
    return () => clearTimeout(t);
  }, [result]);

  async function submit(e) {
    e?.preventDefault();
    if (!v.text.trim() && !file && !eml) return setError("Paste a message or add a file to check.");
    setBusy(true); setError(""); setResult(null);
    try {
      setResult(await api("/analyze", { method: "POST", body: form({ ...v, media: file, eml }) }));
    } catch (err) {
      setError(err instanceof TypeError ? "Can't reach the backend on port 8000. Is it running?" : err.message);
    } finally { setBusy(false); }
  }
  const onKey = (e) => { if ((e.metaKey || e.ctrlKey) && e.key === "Enter") submit(e); };

  return (
    <div className="grid xl:grid-cols-[23rem_1fr] gap-6 xl:gap-8 items-start">
      <form ref={formRef} onSubmit={submit} onKeyDown={onKey} className="glass p-4 space-y-4 xl:sticky xl:top-0">
        <div>
          <p className="label mb-2">Try a scenario</p>
          <div className="flex flex-wrap gap-1.5">
            {SAMPLES.map((s) => (
              <button type="button" key={s.name} aria-pressed={sample === s.name} className="chip"
                onClick={() => { setV({ ...v, text: s.text, channel: s.channel, sender: s.sender }); setSample(s.name); }}>{s.name}</button>
            ))}
          </div>
        </div>
        <label className="block space-y-1.5">
          <span className="label">Message</span>
          <textarea value={v.text} onChange={set("text")} rows={6} className="field resize-none leading-relaxed" placeholder="Paste the WhatsApp, SMS or email text, or notes from the call" />
        </label>
        <DropZone file={file} setFile={setFile} />
        <div className="grid grid-cols-2 gap-3">
          <label className="block space-y-1.5"><span className="label">Arrived via</span>
            <select value={v.channel} onChange={set("channel")} className="field capitalize">{CHANNELS.map((c) => <option key={c} value={c}>{c === "sms" ? "SMS" : c}</option>)}</select>
          </label>
          <label className="block space-y-1.5"><span className="label">Claims to be</span>
            <select value={v.claimed_person_id} onChange={set("claimed_person_id")} className="field">
              <option value="">Work it out</option>
              {people.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </label>
        </div>
        <label className="block space-y-1.5"><span className="label">From (number or address)</span>
          <input value={v.sender} onChange={set("sender")} className="field" placeholder="+91 98… or name@company.com" />
        </label>
        <label className="flex items-center justify-between gap-3 text-[12.5px]">
          <span className="text-ink-soft">Email file (.eml) for header checks</span>
          <span className="btn btn-plain h-7 px-2.5 text-[12px] cursor-pointer">{eml ? eml.name.slice(0, 18) : "Choose…"}
            <input type="file" accept=".eml,message/rfc822" onChange={(e) => setEml(e.target.files[0] || null)} className="sr-only" /></span>
        </label>
        <button disabled={busy} className="btn btn-primary w-full h-10 text-[14.5px]">
          {busy ? "Checking…" : "Check before I act"}<kbd className="text-white/60">{mod}↵</kbd>
        </button>
        {busy && file && <p className="text-[12.5px] text-ink-soft">The first media check loads the models; it can take a minute.</p>}
        {error && <p className="text-[13px] text-high" role="alert">{error}</p>}
      </form>

      <section ref={resultRef} aria-live="polite" className={`min-w-0 scroll-mt-10 ${result ? "max-lg:min-h-[100svh]" : ""}`}>
        <AnimatePresence mode="wait">
          {busy ? (
            <motion.div key="busy" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="glass p-8">
              <p className="display text-3xl font-bold tracking-tight">Checking voice, face, words and request…</p>
              <div className="mt-6 h-1.5 bg-night/10 rounded-full overflow-hidden"><motion.div className="h-full heat-scale w-1/3 rounded-full" animate={{ x: ["-100%", "300%"] }} transition={{ repeat: Infinity, duration: 1.3, ease: "easeInOut" }} /></div>
            </motion.div>
          ) : result ? (
            <motion.div key={result.case_id} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
              <Verdict result={result} caseId={result.case_id} />
            </motion.div>
          ) : (
            <motion.div key="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="frame dusk relative overflow-hidden min-h-[30rem] p-8 sm:p-10 flex flex-col justify-start">
              <DuskScene alert={0} className="absolute inset-x-0 bottom-0 top-[52%] opacity-90 [mask-image:linear-gradient(to_bottom,transparent,black_40%)]" />
              <h2 className="relative text-5xl font-bold tracking-[-0.04em] leading-[0.98] text-white max-w-[13ch] drop-shadow-[0_2px_24px_rgb(35_22_94/0.25)]">Got a request for money, an OTP or files?</h2>
              <p className="relative mt-4 text-[15px] leading-relaxed max-w-md text-ink/85">Paste it, add the voice note or video, and say who it claims to be from. You get a verdict, the reasons behind it, and the safest way to verify, before you act.</p>
            </motion.div>
          )}
        </AnimatePresence>
      </section>
    </div>
  );
}
