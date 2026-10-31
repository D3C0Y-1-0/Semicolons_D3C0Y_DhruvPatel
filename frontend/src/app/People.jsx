import { useEffect, useState } from "react";
import { api, form } from "../lib/api.js";

const field = "w-full bg-sheet border border-rule rounded px-3 py-2 mt-1 focus:border-ink outline-none";
const Tick = ({ on, label }) => <span className={on ? "text-low" : "text-ink-soft/70"}>{on ? "✓" : "–"} {label}</span>;

export default function People() {
  const [people, setPeople] = useState([]);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const load = () => api("/people").then(setPeople).catch(() => {});
  useEffect(() => { load(); }, []);

  async function submit(e) {
    e.preventDefault();
    setBusy(true); setMsg("");
    try {
      const f = Object.fromEntries([...new FormData(e.target)].filter(([, v]) => !(v instanceof File) || v.size));
      const r = await api("/enroll", { method: "POST", body: form(f) });
      setMsg(`Enrolled. Voiceprint ${r.voice_enrolled ? "saved" : "not added"}, face ${r.face_enrolled ? "saved" : "not added"}.`);
      e.target.reset(); load();
    } catch (err) { setMsg(err.message); } finally { setBusy(false); }
  }

  const input = (name, label, props = {}) => <label className="block text-sm font-semibold">{label}<input name={name} className={field} {...props} /></label>;

  return (
    <div className="grid xl:grid-cols-[1fr_24rem] gap-14">
      <div>
        <h2 className="wide text-4xl font-extrabold">Trust Graph</h2>
        <p className="text-ink-soft mt-2 max-w-prose">The people attackers are most likely to imitate, and what normal looks like for each. A request that breaks their pattern raises the risk, however real it sounds.</p>
        {!people.length ? <p className="mt-8 text-ink-soft">Nobody enrolled yet. Run <code>python seed.py</code> in the backend for the demo team, or enrol someone here.</p> : (
          <ul className="mt-8 border-t-2 border-ink">{people.map((p) => (
            <li key={p.id} className="py-5 border-b border-rule grid sm:grid-cols-[14rem_1fr] gap-x-8 gap-y-2">
              <div><p className="text-xl font-bold">{p.name}</p><p className="text-ink-soft">{p.role}</p></div>
              <div className="text-sm space-y-1.5">
                <p>Uses {p.channels?.join(", ") || "no channels set"}, usually {p.work_start}:00 to {p.work_end}:00. Approves up to ₹{Number(p.approval_limit || 0).toLocaleString("en-IN")}.</p>
                <p className="flex flex-wrap gap-x-5"><Tick on={p.voice_enrolled} label="voiceprint" /><Tick on={p.face_enrolled} label="face" /><Tick on={!!p.telegram_chat_id} label="Telegram for verification" /></p>
              </div>
            </li>
          ))}</ul>
        )}
      </div>

      <form onSubmit={submit} className="space-y-3 bg-sheet border border-rule rounded-lg p-6 self-start">
        <h3 className="text-xl font-bold">Enrol someone</h3>
        <p className="text-sm text-ink-soft">Only embeddings are stored, never the recording or photo. Get their consent first.</p>
        {input("name", "Name", { required: true })}
        <div className="grid grid-cols-2 gap-3">{input("role", "Role", { placeholder: "CFO" })}{input("approval_limit", "Approval limit (₹)", { type: "number", min: 0 })}</div>
        {input("email", "Work email", { type: "email" })}
        {input("phone", "Registered phone")}
        {input("telegram_chat_id", "Telegram chat id", { placeholder: "They send /start to the bot to get it" })}
        {input("channels", "Channels they use for work", { defaultValue: "email,teams" })}
        {input("usual_requests", "Requests they normally make", { defaultValue: "information" })}
        <div className="grid grid-cols-2 gap-3">{input("work_start", "Day starts", { type: "number", defaultValue: 9 })}{input("work_end", "Day ends", { type: "number", defaultValue: 19 })}</div>
        <label className="block text-sm font-semibold">Voice sample, 20–60 s<input name="voice" type="file" accept="audio/*" className="block mt-1 font-normal" /></label>
        <label className="block text-sm font-semibold">Face photo<input name="photo" type="file" accept="image/*" className="block mt-1 font-normal" /></label>
        <button disabled={busy} className="w-full bg-ink text-sheet font-bold py-3 rounded disabled:opacity-60">{busy ? "Enrolling…" : "Enrol"}</button>
        {msg && <p className="text-sm" aria-live="polite">{msg}</p>}
      </form>
    </div>
  );
}
