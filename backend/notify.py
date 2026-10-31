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
import threading
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
    if person.get("email") and smtp_ready():
        try:
            send_email(person["email"], subject, text)
            sent.append("email")
        except Exception as e:
            errors.append(f"email failed: {e}")
    links = {"email": f"mailto:{person['email']}?subject={quote(subject)}&body={quote(text)}" if person.get("email") else None}
    return {"sent": sent, "errors": errors, "links": {k: v for k, v in links.items() if v}, "text": text}


def record_answer(cid, ans, via):
    """YES / NO from any channel. A case that's already decided keeps its first answer."""
    case = db.get_case(cid)
    if not case or case["status"] in ("verified", "confirmed_attack"):
        return case
    case = db.update_case(cid, status="verified" if ans == "yes" else "confirmed_attack",
                          result_patch={"verification": {"answer": ans, "at": time.time(), "via": via}})
    if ans == "no":
        import mules
        mules.harvest_case(case, "confirmed attack")
        person = db.get_person(case.get("claimed_person_id") or "")
        if person and person.get("family_emails") and not case["result"].get("family_alert"):
            family_alert(case, person)  # a confirmed impersonation: the family hears it from us before the scammer calls them
    return case


ASK = {"payment": "a payment", "payment_high": "a payment", "credentials": "an OTP or password", "install_app": "an app install",
       "click_link": "to open a link", "personal_info": "ID documents", "call_back": "a call back"}


def family_alert(case, person, no_reply=False):
    """Email the person's family contacts: someone is using their name, and scammers call family next."""
    to = person.get("family_emails") or []
    if not to:
        return {"sent": [], "errors": [f"{person['name']} has no family emails in the Trust Graph."]}
    if not smtp_ready():
        return {"sent": [], "errors": ["Email isn't set up: add SMTP_USER and SMTP_PASS to backend/.env."]}
    r, first = case["result"], person["name"].split()[0]
    amount = (r.get("facts") or {}).get("amount_inr")
    kind = (r.get("scam_types") or [{}])[0].get("label")
    confirmed = case["status"] == "confirmed_attack"
    body = (f"Hello,\n\nYou are listed as a family contact for {person['name']} in TrustCheck, the scam check used at work.\n\n"
            f"Someone just used {first}'s name to ask for {ASK.get(r.get('action'), 'something')}"
            + (f" of {inr(amount)}" if amount else "") + f" via {r.get('channel') or 'an unknown channel'}. "
            + (f"{first} confirmed it was NOT them." if confirmed
               else f"{first} did not confirm it within a minute of being asked, so TrustCheck is treating it as a SCAM." if no_reply
               else f"TrustCheck rated it {r.get('band')} risk" + (f" ({kind})." if kind else "."))
            + f"\n\nScammers often contact family next with the same story or a cloned voice: \"{first} had an accident\", "
            f"\"{first} is arrested\", \"send money urgently\". If anyone contacts you in {first}'s name asking for money, an OTP "
            f"or to stay on a call: hang up, then call {first} on the number you already have. Don't pay and don't share codes.\n\n"
            "Report scams: call 1930 or visit cybercrime.gov.in.\n\nTrustCheck")
    sent, errors = [], []
    for addr in to:
        try:
            send_email(addr, f"TrustCheck alert: someone is pretending to be {person['name']}", body)
            sent.append(addr)
        except Exception as e:
            errors.append(f"{addr}: {e}")
    if sent:
        db.update_case(case["id"], result_patch={"family_alert": {"to": sent, "at": time.time()}})
    return {"sent": sent, "errors": errors}


FAMILY_AFTER = int(os.getenv("FAMILY_ALERT_AFTER", "60"))  # seconds to wait for the real person's YES / NO


def alert_if_silent(cid, after=None):
    """Asked the real person and heard nothing back in time: treat it as a scam and warn the family.
    ponytail: in-process timer, lost if the backend restarts mid-wait; a job queue survives restarts."""
    def check():
        case = db.get_case(cid)
        person = db.get_person((case or {}).get("claimed_person_id") or "")
        if case and person and case["status"] == "verifying" and not case["result"].get("family_alert"):
            out = family_alert(case, person, no_reply=True)
            db.update_case(cid, result_patch={"no_reply_alert": out})
    t = threading.Timer(FAMILY_AFTER if after is None else after, check)
    t.daemon = True
    t.start()
    return t


def pending_for(pid):
    """Requests in this person's name waiting for their YES / NO, in plain words."""
    out = []
    for row in db.list_cases(200):
        if row["claimed_person_id"] == pid and row["status"] == "verifying":
            c = db.get_case(row["id"])
            r = c["result"]
            amount = (r.get("facts") or {}).get("amount_inr")
            when = time.strftime("%d %b, %H:%M", time.localtime(c["created"]))
            out.append({"summary": f"{when}: a request for {r.get('action', 'action').replace('_high', '').replace('_', ' ')}"
                        + (f" of {inr(amount)}" if amount else "") + f" via {r.get('channel') or 'unknown channel'}",
                        "link": case_link(c, pid)})
    return out


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


def case_page(case, person, token, answered=None):
    r = case["result"]
    amount = (r.get("facts") or {}).get("amount_inr")
    first = html.escape(person["name"].split()[0])
    if answered or case["status"] in ("verified", "confirmed_attack"):
        yes = (answered or ("yes" if case["status"] == "verified" else "no")) == "yes"
        return page("Recorded", f"<h1>Thank you, {first}.</h1><p class='done' style='color:var(--{'low' if yes else 'high'})'>"
                    + ("You confirmed the request. It can go ahead." if yes else "Recorded: it was NOT you. The request is blocked and security has been alerted.")
                    + "</p><p>You can close this page.</p>")
    said = (r.get("message") or {}).get("text") or ""
    what = "“" + html.escape(said[:180] + ("…" if len(said) > 180 else "")) + "”" if said else "A request in your name."
    return page("Did you send this?", f"""<h1>{first}, did you send this request?</h1>
<p>Someone using your name contacted a colleague via <b>{html.escape(r.get('channel') or 'an unknown channel')}</b>.</p>
<div class="req">{('Amount: ' + inr(amount) + '<br>') if amount else ''}{what}</div>
<form method="post" class="row"><input type="hidden" name="t" value="{html.escape(token)}">
<button class="yes" name="answer" value="yes">YES, it was me</button><button class="no" name="answer" value="no">NO, not me</button></form>
<p style="font-size:14px">If you didn't send it, tap NO. Nothing is paid until you answer.</p>""")


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
document.getElementById('pending').innerHTML=d.pending.length?'<div class="req">Waiting for your answer:<ul>'+d.pending.map(p=>'<li><a href="'+p.link+'">'+p.summary+'</a></li>').join('')+'</ul></div>':'';
}}catch(e){{document.getElementById('left').textContent='Offline, retrying…'}}}}
tick();setInterval(tick,1000);
</script>""")


def demo():
    p = {"id": "x", "name": "Test Person", "email": "t@example.com", "phone": "9876543210"}
    assert family_alert({"id": "x", "result": {}, "status": "open"}, p)["errors"][0].endswith("no family emails in the Trust Graph.")
    out = deliver(p, "s", "hello there")
    assert list(out["links"]) == ["email"] and out["links"]["email"].startswith("mailto:t@example.com")
    print("notify ok:", public_url())


if __name__ == "__main__":
    demo()
