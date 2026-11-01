"""Out-of-band verification over what needs nothing on the presenting device: email, a QR code or a plain link.

No app to install and no paid API. Every message carries a signed link to a small page this backend serves:
- /v/{case}: "Did YOU send this request?" with YES / NO.
- /me/{person}: the person's live code word (Human 2FA) and any requests waiting for their answer.
Links are signed with the person's code_secret (HMAC), so nobody can answer for someone else by guessing a URL.

Delivery:
- Email goes out automatically when SMTP_USER / SMTP_PASS are set (a free Gmail app password works).
- Email goes to the person's REGISTERED address from the Trust Graph, never to the sender of the request.
- In the room: the verdict shows the link as a QR code; "Copy message" lets anyone send it on any app.
  ponytail: no WhatsApp or SMS links on purpose; both depend on the presenting device (WhatsApp set up, a SIM),
  too risky on stage. An SMS gateway (Android gateway app, or a DLT-registered API) is the upgrade path.
- Telegram still works for anyone who linked it (verify.py).
The phone has to reach this backend: on the same Wi-Fi run uvicorn with --host 0.0.0.0, or set PUBLIC_URL to a tunnel.
"""
import hashlib
import hmac
import html
import os
import smtplib
import socket
import time
from email.message import EmailMessage
from urllib.parse import quote

import db
from detectors.identity import inr


def lan_ip():
    try:  # the address other devices on this Wi-Fi reach the laptop on (no packet is actually sent)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except OSError:
        return "localhost"


def setting(key, default=None):
    """Read backend/.env each time, so a new tunnel address or mail password works without restarting the backend."""
    from dotenv import dotenv_values
    return dotenv_values(os.path.join(os.path.dirname(__file__), ".env")).get(key) or os.getenv(key) or default


def public_url():
    return (setting("PUBLIC_URL") or f"http://{lan_ip()}:{os.getenv('PORT', '8000')}").rstrip("/")


def sign(pid, what):
    secret = db.code_secret(pid)
    return hmac.new(bytes.fromhex(secret), what.encode(), hashlib.sha256).hexdigest()[:24] if secret else ""


def signed(pid, what, token):
    return bool(token) and hmac.compare_digest(sign(pid, what), token)


def case_link(case, pid):
    return f"{public_url()}/v/{case['id']}?t={sign(pid, 'v:' + case['id'])}"


def me_link(pid):
    return f"{public_url()}/me/{pid}?t={sign(pid, 'me')}"


def request_text(case, person):
    r = case["result"]
    amount = (r.get("facts") or {}).get("amount_inr")
    ask = {"payment": "a payment", "payment_high": "a payment", "credentials": "an OTP or password", "install_app": "an app install",
           "click_link": "a link to be opened", "personal_info": "ID documents"}.get(r.get("action"), "an action")
    return (f"TrustCheck security check for {person['name']}: someone using your name just asked us for {ask}"
            + (f" of {inr(amount)}" if amount else "") + f" via {r.get('channel') or 'an unknown channel'}. "
            f"Did YOU send it? Answer YES or NO here: {case_link(case, person['id'])}")


def smtp_ready():
    return bool(setting("SMTP_USER") and setting("SMTP_PASS"))


def send_email(to, subject, body):
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = setting("SMTP_FROM") or setting("SMTP_USER"), to, subject
    msg.set_content(body)
    with smtplib.SMTP_SSL(setting("SMTP_HOST", "smtp.gmail.com"), int(setting("SMTP_PORT", "465")), timeout=15) as s:
        s.login(setting("SMTP_USER"), setting("SMTP_PASS").replace(" ", ""))  # Google shows app passwords in groups of 4
        s.send_message(msg)


def deliver(person, subject, text):
    """Email it if SMTP is set up; always return a one-tap email link to send it by hand."""
    sent, errors = [], []
    if (person.get("email") or "").lower().endswith(("@acme.com", "@acme.in")):  # seed.py's demo addresses: a real company's domain
        errors.append(f"{person['email']} is a demo address from seed.py, so it wasn't emailed. Put a real inbox in Trust Graph.")
    elif person.get("email") and smtp_ready():
        try:
            send_email(person["email"], subject, text)
            sent.append("email")
        except Exception as e:
            errors.append(f"email failed: {e}")
    links = {"email": f"mailto:{person['email']}?subject={quote(subject)}&body={quote(text)}" if person.get("email") else None}
    return {"sent": sent, "errors": errors, "links": {k: v for k, v in links.items() if v}, "text": text}


FAST_YES_SECONDS = int(os.getenv("FAST_YES_SECONDS", "8"))  # quicker than a person can read the request


def strong_needed(case, person):
    """Why one tap of YES isn't enough on this case (empty: it is). A hacked phone or a leaked login can tap YES."""
    r = case["result"]
    amount = (r.get("facts") or {}).get("amount_inr") or 0
    limit = (person or {}).get("approval_limit") or 0
    if limit and amount > limit:
        return [f"{inr(amount)} is above {person['name'].split()[0]}'s {inr(limit)} approval limit"]
    return ["it is a high-value payment"] if r.get("action") == "payment_high" else []


def record_answer(cid, ans, via, approver=None):
    """YES / NO from any channel; a decided case keeps its first decision. NO from anyone blocks at once.
    A plain YES releases a small request. Above the approval limit, or when the YES came impossibly fast, it releases
    only with a video YES (via="video") or a YES from both the person and a second approver."""
    case = db.get_case(cid)
    if not case or case["status"] in ("verified", "confirmed_attack"):
        return case
    r, now = case["result"], time.time()
    answers = r.get("answers", []) + [{"answer": ans, "via": via, "at": round(now), **({"approver": approver} if approver else {})}]
    if ans == "no":
        case = db.update_case(cid, status="confirmed_attack",
                              result_patch={"answers": answers, "verification": {"answer": "no", "at": now, "via": via}})
        import mules
        mules.harvest_case(case, "confirmed attack")
        return case
    person = db.get_person(case["claimed_person_id"]) if case.get("claimed_person_id") else None
    why = list((r.get("needs") or {}).get("why") or strong_needed(case, person))
    if via in ("link", "telegram") and r.get("asked_at") and now - r["asked_at"] < FAST_YES_SECONDS:
        why.append(f"the YES came {now - r['asked_at']:.0f} s after the request, faster than a person can read it")
    owner_yes = any(x["answer"] == "yes" and not x.get("approver") for x in answers)
    approver_yes = any(x["answer"] == "yes" and x.get("approver") for x in answers)
    if via == "video" or (owner_yes and approver_yes) or (not why and not approver):
        return db.update_case(cid, status="verified",
                              result_patch={"answers": answers, "verification": {"answer": "yes", "at": now, "via": via}})
    return db.update_case(cid, status="verifying",
                          result_patch={"answers": answers, "needs": {"why": why, "what": "a 5-second video YES or a second approver"}})


def approver_link(case, pid):
    return f"{public_url()}/a/{case['id']}/{pid}?t={sign(pid, 'a:' + case['id'])}"


def _summary(c):
    r = c["result"]
    amount = (r.get("facts") or {}).get("amount_inr")
    when = time.strftime("%d %b, %H:%M", time.localtime(c["created"]))
    return (f"{when}: a request for {r.get('action', 'action').replace('_high', '').replace('_', ' ')}"
            + (f" of {inr(amount)}" if amount else "") + f" via {r.get('channel') or 'unknown channel'}")


def pending_for(pid):
    """This person's dashboard: requests in their name waiting for them, second approvals asked of them,
    and their last decisions, in plain words."""
    pending, history = [], []
    for row in db.list_cases(200):
        mine, asked = row["claimed_person_id"] == pid, None
        if not mine and row["status"] == "verifying":
            c = db.get_case(row["id"])
            asked = (c["result"].get("approver_asked") or {}).get("id") == pid and c
        if not (mine or asked):
            continue
        c = asked or db.get_case(row["id"])
        if row["status"] == "verifying":
            pending.append({"summary": ("Second approval: " if asked else "") + _summary(c),
                            "link": approver_link(c, pid) if asked else case_link(c, pid)})
        elif row["status"] in ("verified", "confirmed_attack") and len(history) < 5:
            history.append({"summary": _summary(c), "status": "approved" if row["status"] == "verified" else "blocked as an attack"})
    return pending, history


# --- Pages for the real person's phone: no app, no login, the signed link is the key --------------------------------
PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#23165e"><title>{title}</title>
<link href="https://fonts.googleapis.com/css2?family=Urbanist:wght@500;700;800&display=swap" rel="stylesheet">
<style>
:root{{--ink:#1c1838;--night:#23165e;--soft:#5d5878;--low:#0a8ea3;--high:#e01b5f}}
*{{box-sizing:border-box}}body{{margin:0;min-height:100vh;font-family:Urbanist,system-ui,sans-serif;color:var(--ink);
background:radial-gradient(120% 80% at 50% 0%,#c9c2e6,#dedae6 60%);display:flex;justify-content:center;padding:24px 16px}}
.card{{width:100%;max-width:440px;background:rgba(255,255,255,.82);border:1px solid #fff;border-radius:32px;padding:28px;
box-shadow:0 30px 60px -30px rgba(35,22,94,.45);align-self:flex-start}}
.brand{{font-weight:800;color:var(--night);letter-spacing:-.02em}}h1{{font-size:28px;line-height:1.1;margin:14px 0 8px;letter-spacing:-.03em}}
p{{color:var(--soft);line-height:1.5}}.req{{background:#f4f2fa;border-radius:20px;padding:16px;color:var(--ink);font-weight:600}}
.row{{display:flex;gap:10px;margin-top:18px}}button,.btn{{flex:1;border:0;border-radius:999px;padding:16px;font:800 18px Urbanist,sans-serif;color:#fff;cursor:pointer;text-align:center;text-decoration:none}}
.yes{{background:var(--low)}}.no{{background:var(--high)}}.code{{font-size:44px;font-weight:800;letter-spacing:-.02em;color:var(--night);text-transform:uppercase;margin:6px 0;line-height:1.05}}
.bar{{height:8px;border-radius:9px;background:#e7e3f3;overflow:hidden}}.bar i{{display:block;height:100%;background:var(--night);transition:width 1s linear}}
.done{{font-size:22px;font-weight:800}}ul{{padding:0;list-style:none}}li{{margin:10px 0}}a{{color:var(--night);font-weight:700}}
</style></head><body><main class="card"><div class="brand">TrustCheck</div>{body}</main></body></html>"""


def page(title, body):
    return PAGE.format(title=html.escape(title), body=body)


def case_page(case, person, token, approver_for=None):
    """The YES / NO page. `person` is who answers; approver_for is the claimed person when a second approver answers."""
    r = case["result"]
    amount = (r.get("facts") or {}).get("amount_inr")
    first = html.escape(person["name"].split()[0])
    if case["status"] in ("verified", "confirmed_attack"):
        yes = case["status"] == "verified"
        return page("Recorded", f"<h1>Thank you, {first}.</h1><p class='done' style='color:var(--{'low' if yes else 'high'})'>"
                    + ("Approved. The request can go ahead." if yes else "Recorded: NOT approved. The request is blocked and security has been alerted.")
                    + "</p><p>You can close this page.</p>")
    mine = [x for x in r.get("answers", []) if x.get("approver") == (person["id"] if approver_for else None)]
    if r.get("needs") and any(x["answer"] == "yes" for x in mine):
        if approver_for:  # this approver has said YES; the case waits for the owner's YES or a video
            return page("Waiting", f"<h1>Thank you, {first}.</h1><p class='done'>Your approval is recorded.</p>"
                        f"<p>It goes ahead once {html.escape(approver_for['name'])} confirms as well.</p>")
        return video_step(case, person, token)
    said = (r.get("message") or {}).get("text") or ""
    what = "“" + html.escape(said[:180] + ("…" if len(said) > 180 else "")) + "”" if said else "A request in your name."
    head = (f"<h1>{first}, can you approve this?</h1><p>A request in <b>{html.escape(approver_for['name'])}</b>'s name needs a second "
            f"approver because {html.escape('; '.join((r.get('needs') or {}).get('why') or ['it is above their limit']))}.</p>") if approver_for else (
            f"<h1>{first}, did you send this request?</h1><p>Someone using your name contacted a colleague via "
            f"<b>{html.escape(r.get('channel') or 'an unknown channel')}</b>.</p>")
    return page("Did you send this?" if not approver_for else "Second approval", f"""{head}
<div class="req">{('Amount: ' + inr(amount) + '<br>') if amount else ''}{what}</div>
<form method="post" class="row"><input type="hidden" name="t" value="{html.escape(token)}">
<button class="yes" name="answer" value="yes">{'Approve' if approver_for else 'YES, it was me'}</button><button class="no" name="answer" value="no">{'Reject' if approver_for else 'NO, not me'}</button></form>
<p style="font-size:14px">If you didn't send it, tap NO. Nothing is paid until you answer.</p>""")


VIDEO_STEP = """<h1>One more step, __FIRST__.</h1>
<p>Because __WHY__, a tap isn't enough: a hacked phone could tap YES too. Record a 5-second video so we can check it's really you.</p>
<div class="req">Look at the camera and say:<div class="code" id="code" style="font-size:32px">…</div>“I approve this request.”<br>
While you speak: <b>__MOVE__</b>.</div>
<video id="cam" playsinline muted autoplay style="width:100%;margin-top:14px;border-radius:20px;background:#1c1838;aspect-ratio:3/4;object-fit:cover"></video>
<div class="row"><button class="yes" id="rec" type="button">Record 5 seconds</button></div>
<p id="st" aria-live="polite"></p><ul id="res"></ul>
<form method="post" class="row"><input type="hidden" name="t" value="__T__"><button class="no" name="answer" value="no">NO, it wasn't me</button></form>
<p style="font-size:13px">The video is checked for a face swap, a cloned voice, your enrolled face and voice, the code word and lip movement, then deleted.</p>
<script>
const T = "__T__", CID = "__CID__", $ = (id) => document.getElementById(id);
async function code() { try { $("code").textContent = (await (await fetch(`/v/${CID}/code?t=${T}`)).json()).phrase; } catch (e) {} }
code(); setInterval(code, 3000);
$("rec").onclick = async () => {
  let stream;
  try { stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" }, audio: true }); }
  catch (e) { $("st").textContent = "The camera or microphone is blocked. Allow both for this page and try again."; return; }
  $("cam").srcObject = stream;
  const type = ["video/webm;codecs=vp8,opus", "video/webm", "video/mp4"].find((t) => window.MediaRecorder && MediaRecorder.isTypeSupported(t)) || "";
  const mr = new MediaRecorder(stream, type ? { mimeType: type } : {}), parts = [];
  mr.ondataavailable = (e) => e.data.size && parts.push(e.data);
  $("rec").disabled = true; $("res").innerHTML = "";
  let n = 5; $("st").textContent = "Recording… 5";
  const iv = setInterval(() => { n -= 1; $("st").textContent = n > 0 ? "Recording… " + n : "Sending…"; }, 1000);
  mr.start(); await new Promise((r) => setTimeout(r, 5200));
  const stopped = new Promise((r) => (mr.onstop = r)); mr.stop(); await stopped;
  clearInterval(iv); stream.getTracks().forEach((t) => t.stop());
  const mime = mr.mimeType || type || "video/webm", fd = new FormData();
  fd.append("t", T); fd.append("video", new Blob(parts, { type: mime }), mime.includes("mp4") ? "yes.mp4" : "yes.webm");
  $("st").textContent = "Checking your face, voice and code word. This takes about 15 seconds…";
  try {
    const res = await fetch(`/v/${CID}/video`, { method: "POST", body: fd }), d = await res.json();
    if (!res.ok) throw new Error(d.detail || "upload failed");
    for (const c of d.checks) {
      const li = document.createElement("li"), b = document.createElement("b"), s = document.createElement("span");
      b.textContent = (c.ok ? "PASS  " : "FAIL  ") + c.name; b.style.color = c.ok ? "var(--low)" : "var(--high)";
      s.textContent = c.detail; s.style.display = "block"; s.style.color = "var(--soft)"; li.append(b, s); $("res").append(li);
    }
    $("st").innerHTML = d.passed ? '<span class="done" style="color:var(--low)">Approved. The request can go ahead.</span>'
      : '<span class="done" style="color:var(--high)">Not accepted, so the request stays on hold.</span>';
    $("rec").textContent = d.passed ? "Done" : "Try again"; $("rec").disabled = d.passed;
  } catch (e) { $("st").textContent = "Couldn't check the video: " + e.message + ". Try again."; $("rec").disabled = false; }
};
</script>"""


def video_step(case, person, token):
    import videoyes
    why = "; ".join((case["result"].get("needs") or {}).get("why") or ["this is a big request"])
    body = (VIDEO_STEP.replace("__FIRST__", html.escape(person["name"].split()[0])).replace("__WHY__", html.escape(why))
            .replace("__MOVE__", html.escape(videoyes.pick_move())).replace("__T__", html.escape(token)).replace("__CID__", html.escape(case["id"])))
    return page("Video YES", body)


def me_page(person, token):
    first = html.escape(person["name"].split()[0])
    pid = html.escape(person["id"])
    return page("My code word", f"""<h1>Hi {first}. Your code word right now:</h1>
<div class="code" id="code">…</div><div class="bar"><i id="bar" style="width:100%"></i></div>
<p id="left">Changes every 30 seconds.</p>
<p>Say it only when a colleague asks you to prove it's really you. Never type it into a link or tell it to someone who called you.</p>
<div id="pending"></div>
<p style="font-size:13px">Tip: add this page to your home screen. It works like an authenticator app you read out loud.</p>
<script>
async function tick(){{try{{const r=await fetch('/me/{pid}/code?t={html.escape(token)}');const d=await r.json();
document.getElementById('code').textContent=d.phrase;document.getElementById('left').textContent='Changes in '+d.seconds_left+' s';
document.getElementById('bar').style.width=(d.seconds_left/30*100)+'%';
document.getElementById('pending').innerHTML=(d.pending.length?'<div class="req">Waiting for your answer:<ul>'+d.pending.map(p=>'<li><a href="'+p.link+'">'+p.summary+'</a></li>').join('')+'</ul></div>':'<p>Nothing is waiting for your answer.</p>')
+(d.history.length?'<p style="margin-top:18px"><b>Your recent decisions</b></p><ul>'+d.history.map(h=>'<li>'+h.summary+' <b style="color:var(--'+(h.status==='approved'?'low':'high')+')">'+h.status+'</b></li>').join('')+'</ul>':'');
}}catch(e){{document.getElementById('left').textContent='Offline, retrying…'}}}}
tick();setInterval(tick,1000);
</script>""")


def demo():
    p = {"id": "x", "name": "Test Person", "email": "t@example.com", "phone": "9876543210"}
    out = deliver(p, "s", "hello there")
    assert list(out["links"]) == ["email"] and out["links"]["email"].startswith("mailto:t@example.com")
    print("notify ok:", public_url())


if __name__ == "__main__":
    demo()
