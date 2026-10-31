"""Out-of-band verification over what every phone already has: SMS, email, a QR code or a plain link.

No app to install and no paid API. Every message carries a signed link to a small page this backend serves:
- /v/{case}: "Did YOU send this request?" with YES / NO.
- /me/{person}: the person's live code word (Human 2FA) and any requests waiting for their answer.
Links are signed with the person's code_secret (HMAC), so nobody can answer for someone else by guessing a URL.

Delivery:
- Email goes out automatically when SMTP_USER / SMTP_PASS are set (a free Gmail app password works).
- SMS opens on the employee's phone with the message pre-filled (sms: link), addressed to the person's
  REGISTERED number from the Trust Graph, never to the number the request came from.
- In the room: the verdict shows the link as a QR code.
  ponytail: no WhatsApp link on purpose; it needs WhatsApp set up on the presenting device and failed that test.
- Telegram still works for anyone who linked it (verify.py).
The phone has to reach this backend: on the same Wi-Fi run uvicorn with --host 0.0.0.0, or set PUBLIC_URL to a tunnel.
"""
import hashlib
import hmac
import html
import os
import re
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


def public_url():
    return (os.getenv("PUBLIC_URL") or f"http://{lan_ip()}:{os.getenv('PORT', '8000')}").rstrip("/")


def sign(pid, what):
    secret = db.code_secret(pid)
    return hmac.new(bytes.fromhex(secret), what.encode(), hashlib.sha256).hexdigest()[:24] if secret else ""


def signed(pid, what, token):
    return bool(token) and hmac.compare_digest(sign(pid, what), token)


def case_link(case, pid):
    return f"{public_url()}/v/{case['id']}?t={sign(pid, 'v:' + case['id'])}"


def me_link(pid):
    return f"{public_url()}/me/{pid}?t={sign(pid, 'me')}"


def intl(phone):
    d = re.sub(r"\D", "", phone or "")
    return "91" + d if len(d) == 10 else d


def request_text(case, person):
    r = case["result"]
    amount = (r.get("facts") or {}).get("amount_inr")
    ask = {"payment": "a payment", "payment_high": "a payment", "credentials": "an OTP or password", "install_app": "an app install",
           "click_link": "a link to be opened", "personal_info": "ID documents"}.get(r.get("action"), "an action")
    return (f"TrustCheck security check for {person['name']}: someone using your name just asked us for {ask}"
            + (f" of {inr(amount)}" if amount else "") + f" via {r.get('channel') or 'an unknown channel'}. "
            f"Did YOU send it? Answer YES or NO here: {case_link(case, person['id'])}")


def smtp_ready():
    return bool(os.getenv("SMTP_USER") and os.getenv("SMTP_PASS"))


def send_email(to, subject, body):
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = os.getenv("SMTP_FROM") or os.getenv("SMTP_USER"), to, subject
    msg.set_content(body)
    with smtplib.SMTP_SSL(os.getenv("SMTP_HOST", "smtp.gmail.com"), int(os.getenv("SMTP_PORT", "465")), timeout=15) as s:
        s.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASS"))
        s.send_message(msg)


def deliver(person, subject, text):
    """Email it if SMTP is set up; always return one-tap SMS / email links to send it by hand."""
    sent, errors = [], []
    if person.get("email") and smtp_ready():
        try:
            send_email(person["email"], subject, text)
            sent.append("email")
        except Exception as e:
            errors.append(f"email failed: {e}")
    phone = intl(person.get("phone"))
    links = {"sms": f"sms:+{phone}?body={quote(text)}" if phone else None,
             "email": f"mailto:{person['email']}?subject={quote(subject)}&body={quote(text)}" if person.get("email") else None}
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
    return case


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
    assert intl("98765 43210") == "919876543210" and intl("+91 98765 43210") == "919876543210"
    p = {"id": "x", "name": "Test Person", "email": "t@example.com", "phone": "9876543210"}
    out = deliver(p, "s", "hello there")
    assert out["links"]["sms"] == "sms:+919876543210?body=hello%20there" and "whatsapp" not in out["links"]
    print("notify ok:", public_url())


if __name__ == "__main__":
    demo()
