import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import Verdict from "../components/Verdict.jsx";
import { api, form } from "../lib/api.js";
import { SAMPLES } from "../lib/samples.js";

const CHANNELS = ["email", "whatsapp", "phone", "sms", "meet", "teams", "zoom"];
const field = "w-full bg-sheet border border-rule rounded px-3 py-2.5 focus:border-ink outline-none";

function DropZone({ file, setFile }) {
  const [over, setOver] = useState(false);
  const input = useRef();
  const url = file ? URL.createObjectURL(file) : null;
  const kind = file?.type.split("/")[0];
  return (
    <div onDragOver={(e) => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)}
      onDrop={(e) => { e.preventDefault(); setOver(false); e.dataTransfer.files[0] && setFile(e.dataTransfer.files[0]); }}
      className={`rounded border-2 border-dashed p-4 transition-colors ${over ? "border-ink bg-sheet" : "border-rule"}`}>
      {!file ? (
        <button type="button" onClick={() => input.current.click()} className="w-full text-left">
          <span className="font-semibold block">Drop a voice note, video or image</span>
          <span className="text-sm text-ink-soft">or click to choose. WhatsApp .opus, .mp3, .mp4, .jpg all work.</span>
        </button>
      ) : (
        <div className="space-y-2">
          {kind === "audio" && <audio src={url} controls className="w-full" />}
          {kind === "video" && <video src={url} controls className="w-full rounded max-h-48" />}
          {kind === "image" && <img src={url} alt="Uploaded" className="max-h-40 rounded" />}
          <div className="flex justify-between text-sm"><span className="truncate">{file.name}</span>
            <button type="button" onClick={() => setFile(null)} className="underline shrink-0 ml-3">Remove</button></div>
        </div>
      )}
      <input ref={input} type="file" accept="audio/*,video/*,image/*" hidden onChange={(e) => e.target.files[0] && setFile(e.target.files[0])} />
    </div>
  );
}

export default function Check() {
  const [people, setPeople] = useState([]);
  const [v, setV] = useState({ text: "", channel: "email", sender: "", claimed_person_id: "" });
  const [file, setFile] = useState(null);
  const [eml, setEml] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const set = (k) => (e) => setV({ ...v, [k]: e.target.value });

  useEffect(() => { api("/people").then(setPeople).catch(() => {}); }, []);

  async function submit(e) {
    e.preventDefault();
    if (!v.text.trim() && !file && !eml) return setError("Paste a message or add a file to check.");
    setBusy(true); setError(""); setResult(null);
    try {
      setResult(await api("/analyze", { method: "POST", body: form({ ...v, media: file, eml }) }));
    } catch (err) {
      setError(`Couldn't check this: ${err.message}. Is the backend running on port 8000?`);
    } finally { setBusy(false); }
  }

  return (
    <div className="grid xl:grid-cols-[24rem_1fr] gap-12">
      <form onSubmit={submit} className="space-y-5 xl:sticky xl:top-8 self-start">
        <div>
          <p className="text-sm font-semibold mb-2">Try a scenario</p>
          <div className="flex flex-wrap gap-1.5">
            {SAMPLES.map((s) => (
              <button type="button" key={s.name} onClick={() => setV({ ...v, text: s.text, channel: s.channel, sender: s.sender })}
                className="text-sm px-3 py-1.5 rounded-full border border-ink/25 hover:border-ink bg-sheet">{s.name}</button>
            ))}
          </div>
        </div>
        <label className="block">
          <span className="font-semibold">The message</span>
          <textarea value={v.text} onChange={set("text")} rows={7} className={`${field} mt-1`} placeholder="Paste the WhatsApp, SMS or email text, or notes from the call" />
        </label>
        <DropZone file={file} setFile={setFile} />
        <label className="block text-sm">
          <span className="font-semibold">Email file (.eml) for header checks</span>
          <input type="file" accept=".eml,message/rfc822" onChange={(e) => setEml(e.target.files[0] || null)} className="block w-full mt-1" />
        </label>
        <div className="grid grid-cols-2 gap-3">
          <label className="block"><span className="font-semibold">Arrived via</span>
            <select value={v.channel} onChange={set("channel")} className={`${field} mt-1`}>{CHANNELS.map((c) => <option key={c}>{c}</option>)}</select>
          </label>
          <label className="block"><span className="font-semibold">Claims to be</span>
            <select value={v.claimed_person_id} onChange={set("claimed_person_id")} className={`${field} mt-1`}>
              <option value="">Work it out</option>
              {people.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </label>
        </div>
        <label className="block"><span className="font-semibold">From (address or number)</span>
          <input value={v.sender} onChange={set("sender")} className={`${field} mt-1`} placeholder="+91 98… or name@company.com" />
        </label>
        <button disabled={busy} className="w-full bg-ink text-sheet font-bold py-3.5 rounded disabled:opacity-60 hover:bg-night-2">
          {busy ? "Checking…" : "Check before I act"}
        </button>
        {busy && file && <p className="text-sm text-ink-soft">The first media check loads the models; it can take a minute.</p>}
        {error && <p className="text-sm text-high" role="alert">{error}</p>}
      </form>

      <section aria-live="polite" className="min-w-0">
        <AnimatePresence mode="wait">
          {busy ? (
            <motion.div key="busy" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="pt-8">
              <p className="wide text-3xl font-bold">Checking voice, face, words and request…</p>
              <div className="mt-6 h-1 bg-rule rounded overflow-hidden"><motion.div className="h-full bg-ink w-1/3" animate={{ x: ["-100%", "300%"] }} transition={{ repeat: Infinity, duration: 1.4, ease: "easeInOut" }} /></div>
            </motion.div>
          ) : result ? (
            <motion.div key={result.case_id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              <Verdict result={result} caseId={result.case_id} />
            </motion.div>
          ) : (
            <motion.div key="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="pt-4 max-w-prose">
              <h2 className="wide text-4xl font-extrabold leading-tight">Got a request for money, an OTP or files?</h2>
              <p className="mt-4 text-lg text-ink-soft">Paste it, drop the voice note or video, and say who it claims to be from. You get a verdict, the reasons behind it, and the safest way to verify, before you act.</p>
            </motion.div>
          )}
        </AnimatePresence>
      </section>
    </div>
  );
}
