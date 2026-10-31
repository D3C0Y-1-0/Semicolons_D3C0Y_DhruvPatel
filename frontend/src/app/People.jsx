import { useEffect, useState } from "react";
import { api, form } from "../lib/api.js";

const field = "w-full bg-white/80 border border-white rounded-xl px-4 py-2.5 mt-1 focus:border-night/40 outline-none";
const Tick = ({ on, label }) => <span className={`rounded-full px-3 py-1 text-xs font-bold ${on ? "bg-low text-white" : "bg-white/70 text-ink-soft"}`}>{on ? "✓" : "–"} {label}</span>;

export default function People() {
  const [people, setPeople] = useState([]);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [edit, setEdit] = useState(null); // existing person being updated (adds Telegram id, voice or face), else new
  const load = () => api("/people").then(setPeople).catch(() => {});
  useEffect(() => { load(); }, []);

  async function submit(e) {
    e.preventDefault();
    setBusy(true); setMsg("");
    try {
      const f = Object.fromEntries([...new FormData(e.target)].filter(([, v]) => !(v instanceof File) || v.size));
      const r = await api("/enroll", { method: "POST", body: form(f) });
      setMsg(`${edit ? "Updated" : "Enrolled"}. Voiceprint ${r.voice_enrolled ? "saved" : "not added"}, face ${r.face_enrolled ? "saved" : "not added"}.`);
      e.target.reset(); setEdit(null); load();
    } catch (err) { setMsg(err.message); } finally { setBusy(false); }
  }

  const input = (name, label, props = {}) => <label className="block text-sm font-semibold">{label}<input name={name} className={field} {...props} /></label>;

  return (
    <div className="grid xl:grid-cols-[1fr_24rem] gap-14">
      <div>
        <h2 className="text-5xl font-bold tracking-[-0.04em]">Trust Graph</h2>
        <p className="text-ink-soft mt-2 max-w-prose">The people attackers are most likely to imitate, and what normal looks like for each. A request that breaks their pattern raises the risk, however real it sounds.</p>
        {!people.length ? <p className="mt-8 text-ink-soft">Nobody enrolled yet. Run <code>python seed.py</code> in the backend for the demo team, or enrol someone here.</p> : (
          <ul className="mt-8 grid gap-3">{people.map((p) => (
            <li key={p.id} className="glass rounded-[2rem] p-5 sm:p-6 grid sm:grid-cols-[16rem_1fr] gap-x-8 gap-y-3 items-center">
              <div className="flex items-center gap-4"><span className="orb size-14 bg-night text-white text-lg font-bold shrink-0">{p.name.split(" ").map((w) => w[0]).join("").slice(0, 2)}</span><div><p className="text-xl font-bold">{p.name}</p><p className="text-ink-soft">{p.role}</p></div></div>
              <div className="text-sm space-y-1.5">
                <p>Uses {p.channels?.join(", ") || "no channels set"}, usually {p.work_start}:00 to {p.work_end}:00. Approves up to ₹{Number(p.approval_limit || 0).toLocaleString("en-IN")}.</p>
                <p className="flex flex-wrap gap-2"><Tick on={p.voice_enrolled} label="voiceprint" /><Tick on={p.face_enrolled} label="face" /><Tick on={!!p.telegram_chat_id} label="Telegram for verification" /></p>
              </div>
            </li>
          ))}</ul>
        )}
      </div>

      <form key={edit?.id || "new"} onSubmit={submit} className="space-y-3 glass-strong rounded-[2rem] p-6 self-start">
        <h3 className="text-xl font-bold">{edit ? `Update ${edit.name}` : "Enrol someone"}</h3>
        <p className="text-sm text-ink-soft">Only embeddings are stored, never the recording or photo. Get their consent first.</p>
        <label className="block text-sm font-semibold">Person
          <select value={edit?.id || ""} onChange={(e) => setEdit(people.find((p) => p.id === e.target.value) || null)} className={field}>
            <option value="">Someone new</option>
            {people.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        </label>
        {edit && <input type="hidden" name="id" value={edit.id} />}
        {input("name", "Name", { required: true, defaultValue: edit?.name })}
        <div className="grid grid-cols-2 gap-3">{input("role", "Role", { placeholder: "CFO", defaultValue: edit?.role })}{input("approval_limit", "Approval limit (₹)", { type: "number", min: 0, defaultValue: edit?.approval_limit })}</div>
        {input("email", "Work email", { type: "email", defaultValue: edit?.email })}
        {input("phone", "Registered phone", { defaultValue: edit?.phone })}
        {input("telegram_chat_id", "Telegram chat id", { placeholder: "They send /start to the bot to get it", defaultValue: edit?.telegram_chat_id })}
        {input("channels", "Channels they use for work", { defaultValue: edit?.channels?.join(",") ?? "email,teams" })}
        {input("usual_requests", "Requests they normally make", { defaultValue: edit?.usual_requests?.join(",") ?? "information" })}
        <div className="grid grid-cols-2 gap-3">{input("work_start", "Day starts", { type: "number", defaultValue: edit?.work_start ?? 9 })}{input("work_end", "Day ends", { type: "number", defaultValue: edit?.work_end ?? 19 })}</div>
        <label className="block text-sm font-semibold">Voice sample, 20–60 s{edit?.voice_enrolled && " (leave empty to keep the saved one)"}<input name="voice" type="file" accept="audio/*" className="block mt-1 font-normal" /></label>
        <label className="block text-sm font-semibold">Face photo{edit?.face_enrolled && " (leave empty to keep the saved one)"}<input name="photo" type="file" accept="image/*" className="block mt-1 font-normal" /></label>
        <button disabled={busy} className="w-full bg-night text-white font-bold py-3.5 rounded-full disabled:opacity-60">{busy ? "Saving…" : edit ? "Save changes" : "Enrol"}</button>
        {msg && <p className="text-sm" aria-live="polite">{msg}</p>}
      </form>
    </div>
  );
}
