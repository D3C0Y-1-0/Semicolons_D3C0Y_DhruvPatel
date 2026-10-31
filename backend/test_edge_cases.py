"""Awkward inputs the demo (or a judge) might throw at TrustCheck. Run from backend/: python test_edge_cases.py
Uses a throwaway database (TRUSTCHECK_DB), no Telegram, no e-mail, no model warm-up. Every case must answer cleanly:
a verdict or a clear 4xx message, never a 500 or a hang.
"""
import os
import sys
import tempfile
import wave

TMP = tempfile.mkdtemp(prefix="tc_edge_")
os.environ.update(TRUSTCHECK_DB=os.path.join(TMP, "edge.db"), TELEGRAM_BOT_TOKEN="", WARMUP="0", SMTP_USER="", SMTP_PASS="")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import app  # noqa: E402
import notify  # noqa: E402

notify.smtp_ready = lambda: False  # never send real mail from a test
c = TestClient(app.app)
FAILS = []


def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else f"  -> {detail}"))
    if not cond:
        FAILS.append(name)


def f(name, data=b""):
    p = os.path.join(TMP, name)
    with open(p, "wb") as fh:
        fh.write(data)
    return p


def wav(name, seconds, silent=False):
    p = os.path.join(TMP, name)
    t = np.arange(int(16000 * seconds)) / 16000
    x = np.zeros_like(t) if silent else 0.3 * np.sin(2 * np.pi * 220 * t)
    with wave.open(p, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    return p


def analyze(text="", path=None, **form):
    files = {"media": (os.path.basename(path), open(path, "rb"))} if path else None
    return c.post("/analyze", data={"text": text, **form}, files=files)


c.post("/enroll", data={"id": "cfo-rajesh", "name": "Rajesh Kumar", "role": "CFO", "email": "rajesh@acme.com", "phone": "9876543210",
                        "channels": "email,teams", "approval_limit": 1000000, "usual_requests": "information,payment"})

# --- text ------------------------------------------------------------------------------------------------------
r = analyze("")
check("empty request is refused or LOW", r.status_code in (200, 400) and (r.status_code == 400 or r.json()["band"] == "LOW"), r.text[:200])
r = analyze("   \n\t  ")
check("whitespace only", r.status_code in (200, 400), r.text[:200])
r = analyze("Transfer ₹5 lakh now to the new account, urgent. " * 4000)
check("200 KB message answers", r.status_code == 200 and r.json()["band"] == "HIGH", r.text[:200])
r = analyze("😀🎉🙏🔥")
check("emoji only", r.status_code == 200 and r.json()["band"] == "LOW", r.text[:200])
r = analyze("कल ऑफिस में दस बजे मीटिंग है, रिपोर्ट तैयार रखना।")
check("Hindi, harmless", r.status_code == 200 and r.json()["band"] == "LOW", r.text[:200])
r = analyze("𝐃𝐞𝐚𝐫 𝐜𝐮𝐬𝐭𝐨𝐦𝐞𝐫, 𝐲𝐨𝐮𝐫 𝐒𝐁𝐈 𝐚𝐜𝐜𝐨𝐮𝐧𝐭 𝐰𝐢𝐥𝐥 𝐛𝐞 𝐛𝐥𝐨𝐜𝐤𝐞𝐝 𝐭𝐨𝐝𝐚𝐲. 𝐔𝐩𝐝𝐚𝐭𝐞 𝐊𝐘𝐂: http://sbi-kyc-update.xyz/login")
check("Unicode bold letters (evasion)", r.status_code == 200 and r.json()["band"] == "HIGH" and r.json()["scam_types"], r.text[:300])
r = analyze("Ｙｏｕｒ ｐａｒｃｅｌ ｉｓ ｏｎ ｈｏｌｄ. Ｐａｙ Ｒｓ ２５ ｒｅｄｅｌｉｖｅｒｙ ｆｅｅ ａｔ indiapost-redelivery.top/in")
check("fullwidth letters (evasion)", r.status_code == 200 and r.json()["band"] == "HIGH", r.text[:300])
r = analyze("Share the O​T​P you just received, I am from the bank fraud team. Urgent.")
check("zero-width spaces inside OTP (evasion)", r.status_code == 200 and r.json()["band"] == "HIGH", r.text[:300])
r = analyze("<script>alert(1)</script> transfer 45 lakh now")
check("HTML in message comes back as plain text", r.status_code == 200 and "<script>" in r.json()["message"]["text"], r.text[:200])
r = analyze("hello", claimed_person_id="nobody-like-this")
check("unknown claimed person", r.status_code == 200, r.text[:200])
r = analyze("hello", hour="99")
check("impossible hour", r.status_code in (200, 422), r.text[:200])

# --- files -----------------------------------------------------------------------------------------------------
r = analyze("", f("chat.txt", "Rajesh here, urgent and confidential: transfer ₹45 lakh to the new vendor account now".encode()))
check(".txt export is read as the message", r.status_code == 200 and "45 lakh" in r.json()["message"]["text"] and r.json()["band"] == "HIGH", r.text[:200])
for name, data, what in [("notes.pdf", b"%PDF-1.4 fake", "PDF"), ("data.docx", b"PK fake", "Word file"),
                         ("empty.mp3", b"", "zero-byte audio"), ("broken.mp3", os.urandom(4000), "corrupt audio"),
                         ("broken.mp4", os.urandom(8000), "corrupt video"), ("broken.jpg", os.urandom(3000), "corrupt image"),
                         ("empty.png", b"", "zero-byte image")]:
    r = analyze("", f(name, data))
    ok = r.status_code in (200, 400, 415) and (r.status_code != 200 or r.json().get("errors"))
    check(f"{what} gives a clear answer", ok, f"{r.status_code} {r.text[:200]}")
r = analyze("", wav("short.wav", 0.5))
check("half-second audio", r.status_code == 200, r.text[:200])
r = analyze("", wav("silent.wav", 5, silent=True))
check("silent audio", r.status_code == 200 and r.json()["band"] == "LOW", r.text[:200])
r = c.post("/analyze", data={"text": ""}, files={"eml": ("bad.eml", b"\x00\xff not an email at all")})
check("garbage .eml", r.status_code in (200, 400), r.text[:200])

# --- ids and tokens ------------------------------------------------------------------------------------------
check("unknown case 404", c.get("/cases/doesnotexist").status_code == 404)
check("verify unknown case 404", c.post("/verify/doesnotexist").status_code == 404)
check("decision with bad answer 400", c.post("/cases/doesnotexist/decision", data={"answer": "maybe"}).status_code in (400, 404))
check("decoy on unknown case 404", c.post("/cases/doesnotexist/decoy", data={"scammer": "hi"}).status_code == 404)
check("report on unknown case 404", c.get("/cases/doesnotexist/report").status_code == 404)
check("code word for unknown person 404", c.post("/people/nobody/code", data={"said": "mango river"}).status_code == 404)
r = c.post("/people/cfo-rajesh/code", data={"said": ""})
check("empty code word refused", r.status_code in (400, 422) or (r.status_code == 200 and r.json()["match"] is False), r.text[:200])
cid = analyze("Rajesh here, urgent: transfer 45 lakh to the new vendor account now", claimed_person_id="cfo-rajesh").json()["case_id"]
check("verify page with bad token 403", c.get(f"/v/{cid}?t=wrong").status_code == 403)
check("verify answer with bad token 403", c.post(f"/v/{cid}", data={"t": "wrong", "answer": "no"}).status_code == 403)
check("code page with bad token 403", c.get("/me/cfo-rajesh?t=wrong").status_code == 403)
r = c.post(f"/cases/{cid}/decision", data={"answer": "no"})
check("NO recorded", r.status_code == 200 and r.json()["status"] == "confirmed_attack", r.text[:200])
r = c.post(f"/cases/{cid}/decision", data={"answer": "yes"})
check("a second answer can't flip a decided case", r.status_code == 200 and r.json()["status"] == "confirmed_attack", r.text[:200])
low = analyze("Happy birthday team!").json()["case_id"]
r = c.post(f"/verify/{low}")
check("verify a case with nobody to ask gives a clear 400", r.status_code == 400 and "detail" in r.json(), r.text[:200])
r = c.post("/cases/" + cid + "/decoy", data={"scammer": ""})
check("decoy with an empty reply", r.status_code == 200, r.text[:200])
check("QR for a very long text", c.get("/qr", params={"data": "x" * 5000}).status_code == 200)
check("enrol with hours out of range 400", c.post("/enroll", data={"name": "X", "work_start": 30}).status_code == 400)
check("enrol with no name 422", c.post("/enroll", data={"role": "CFO"}).status_code == 422)

print(f"\n{len(FAILS)} failed" + (": " + ", ".join(FAILS) if FAILS else ", all edge cases handled"))
sys.exit(1 if FAILS else 0)
