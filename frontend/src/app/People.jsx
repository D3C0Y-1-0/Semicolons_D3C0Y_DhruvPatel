import { useEffect, useState } from "react";
import { api, form } from "../lib/api.js";
import { SendLinks } from "../components/Defense.jsx";

const field = "field mt-1 font-normal";
const Tick = ({ on, label }) => <span className={`rounded-md px-2 py-0.5 text-[12px] font-semibold ${on ? "bg-low/12 text-low" : "bg-ink/[0.05] text-ink-soft"}`}>{on ? "✓" : "–"} {label}</span>;

export default function People() {
  const [people, setPeople] = useState([]);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [edit, setEdit] = useState(null); // existing person being updated (adds phone, voice or face), else new
  const [invite, setInvite] = useState({}); // person id -> delivery of their code-word page
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

  const sendInvite = async (p) => {
    try { const d = await api(`/people/${p.id}/invite`, { method: "POST" }); setInvite((v) => ({ ...v, [p.id]: d })); }
    catch (err) { setInvite((v) => ({ ...v, [p.id]: { errors: [err.message] } })); }
  };

  const input = (name, label, props = {}) => <label className="block label">{label}<input name={name} className={field} {...props} /></label>;

  return (
    <div className="grid xl:grid-cols-[1fr_22rem] gap-8">
      <div>
        <h2 className="text-[28px] font-bold tracking-tight">Trust Graph</h2>
        <p className="text-ink-soft mt-1 text-[13.5px] max-w-prose">The people attackers are most likely to imitate, and what normal looks like for each. A request that breaks their pattern raises the risk, however real it sounds.</p>
        {!people.length ? <p className="mt-8 text-ink-soft">Nobody enrolled yet. Run <code>python seed.py</code> in the backend for the demo team, or enrol someone here.</p> : (
          <ul className="mt-5 glass divide-y divide-ink/[0.07]">{people.map((p) => (
            <li key={p.id} className="p-4 grid sm:grid-cols-[15rem_1fr] gap-x-6 gap-y-3 items-center">
              <div className="flex items-center gap-4"><span className="orb size-11 bg-gradient-to-b from-[#4a3aa6] to-night text-white text-[15px] font-bold shrink-0 shadow-[inset_0_0.5px_0_rgb(255_255_255/0.4)]">{p.name.split(" ").map((w) => w[0]).join("").slice(0, 2)}</span><div><p className="text-[15px] font-semibold">{p.name}</p><p className="text-ink-soft text-[13px]">{p.role}</p></div></div>
              <div className="text-[13px] space-y-1.5">
                <p>Uses {p.channels?.join(", ") || "no channels set"}, usually {p.work_start}:00 to {p.work_end}:00. Approves up to ₹{Number(p.approval_limit || 0).toLocaleString("en-IN")}.</p>
                <p className="flex flex-wrap gap-2"><Tick on={p.voice_enrolled} label="voiceprint" /><Tick on={p.face_enrolled} label="face" /><Tick on={!!p.email} label="email for verification" />{p.telegram_chat_id && <Tick on label="Telegram" />}</p>
                <button onClick={() => sendInvite(p)} className="text-night font-semibold hover:underline">{invite[p.id] ? "Send again" : "Send their code-word page"}</button>
              </div>
              {invite[p.id] && <div className="sm:col-span-2"><SendLinks delivery={invite[p.id]} who={p.name.split(" ")[0]} qr={invite[p.id].link} qrLabel={`${p.name.split(" ")[0]} scans this to open their page`} /></div>}
            </li>
          ))}</ul>
        )}
      </div>

      <form key={edit?.id || "new"} onSubmit={submit} className="space-y-3 glass-strong p-4 self-start xl:sticky xl:top-0">
        <h3 className="text-[17px] font-bold">{edit ? `Update ${edit.name}` : "Enrol someone"}</h3>
        <p className="text-[12.5px] text-ink-soft">Only embeddings are stored, never the recording or photo. Get their consent first.</p>
        <label className="block label">Person
          <select value={edit?.id || ""} onChange={(e) => setEdit(people.find((p) => p.id === e.target.value) || null)} className={field}>
            <option value="">Someone new</option>
            {people.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        </label>
        {edit && <input type="hidden" name="id" value={edit.id} />}
        {input("name", "Name", { required: true, defaultValue: edit?.name })}
        <div className="grid grid-cols-2 gap-3">{input("role", "Role", { placeholder: "CFO", defaultValue: edit?.role })}{input("approval_limit", "Approval limit (₹)", { type: "number", min: 0, defaultValue: edit?.approval_limit })}</div>
        {input("email", "Work email", { type: "email", defaultValue: edit?.email })}
        {input("phone", "Registered mobile", { defaultValue: edit?.phone, placeholder: "98765 43210" })}
        {input("telegram_chat_id", "Telegram chat id (optional)", { placeholder: "Only if they use Telegram: they send /start to the bot", defaultValue: edit?.telegram_chat_id })}
        {input("channels", "Channels they use for work", { defaultValue: edit?.channels?.join(",") ?? "email,teams" })}
        {input("usual_requests", "Requests they normally make", { defaultValue: edit?.usual_requests?.join(",") ?? "information" })}
        <div className="grid grid-cols-2 gap-3">{input("work_start", "Day starts (hour, 0–23)", { type: "number", min: 0, max: 23, step: 1, required: true, defaultValue: edit?.work_start ?? 9 })}{input("work_end", "Day ends (hour, 0–23)", { type: "number", min: 0, max: 23, step: 1, required: true, defaultValue: edit?.work_end ?? 19 })}</div>
        <label className="block label">Voice sample, 20–60 s{edit?.voice_enrolled && " (leave empty to keep the saved one)"}<input name="voice" type="file" accept="audio/*" className="block mt-1 font-normal text-[12.5px] text-ink file:mr-3 file:h-7 file:px-2.5 file:rounded-md file:border-0 file:bg-night/10 file:text-night file:font-semibold file:cursor-pointer" /></label>
        <label className="block label">Face photo{edit?.face_enrolled && " (leave empty to keep the saved one)"}<input name="photo" type="file" accept="image/*" className="block mt-1 font-normal text-[12.5px] text-ink file:mr-3 file:h-7 file:px-2.5 file:rounded-md file:border-0 file:bg-night/10 file:text-night file:font-semibold file:cursor-pointer" /></label>
        <button disabled={busy} className="btn btn-primary w-full h-10">{busy ? "Saving…" : edit ? "Save changes" : "Enrol"}</button>
        {msg && <p className="text-[13px]" aria-live="polite">{msg}</p>}
      </form>
    </div>
  );
}
