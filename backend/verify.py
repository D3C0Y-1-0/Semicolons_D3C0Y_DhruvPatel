"""Out-of-band verification + citizen bot over Telegram (stdlib only, long polling, no public URL needed).

- Staff: /start in the bot replies with the chat id to paste into enrolment.
- Verification: the real person gets YES/NO buttons; the answer updates the case.
- Citizen mode: anyone can forward a voice note or text; the bot replies with a risk band.
"""
import json
import os
import tempfile
import threading
import time
import urllib.request

import db
from detectors.identity import inr

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
API = f"https://api.telegram.org/bot{TOKEN}"


def call(method, **params):
    req = urllib.request.Request(f"{API}/{method}", json.dumps(params).encode(), {"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=40)).get("result")


def send_verification(case, person):
    if not TOKEN:
        raise RuntimeError("Telegram isn't set up: add TELEGRAM_BOT_TOKEN to backend/.env and restart the backend. "
                           "Until then, use the two buttons to record their answer.")
    if not person or not person.get("telegram_chat_id"):
        raise RuntimeError("This person has no Telegram chat id. They send /start to the bot, then you add the id "
                           "in Trust Graph.")
    r = case["result"]
    amount = r.get("facts", {}).get("amount_inr")
    text = (f"TrustCheck security check\n\nSomeone using your name ({person['name']}) just sent a request"
            + (f" for {inr(amount)}" if amount else "") + f" via {r.get('channel') or 'an unknown channel'}.\n\n"
            "Did YOU send this request?")
    call("sendMessage", chat_id=person["telegram_chat_id"], text=text,
         reply_markup={"inline_keyboard": [[{"text": "YES, it was me", "callback_data": f"v:{case['id']}:yes"},
                                            {"text": "NO, not me", "callback_data": f"v:{case['id']}:no"}]]})


def _on_callback(cq):
    import notify  # late import: keeps the bot module light
    _, cid, ans = cq["data"].split(":")
    case = notify.record_answer(cid, ans, "telegram")  # a case already answered elsewhere keeps its first answer
    if case and case["result"].get("verification", {}).get("answer") not in (None, ans):
        ans = case["result"]["verification"]["answer"]
    if case and case["status"] == "verifying" and ans == "yes":  # a big request: a tap isn't enough, ask for the video YES
        why = "; ".join(case["result"].get("needs", {}).get("why", []))
        text = (f"Thanks. One more step: because {why}, a tap isn't enough. Record a 5-second video YES here: "
                + notify.case_link(case, case["claimed_person_id"]))
    else:
        text = "Recorded: " + ("you confirmed the request." if ans == "yes" else "NOT you. The payment is on hold and security has been alerted.")
    call("answerCallbackQuery", callback_query_id=cq["id"], text="Recorded. Thank you.")
    try:  # a second tap asks Telegram to "edit" the message into the text it already has: a harmless 400
        call("editMessageText", chat_id=cq["message"]["chat"]["id"], message_id=cq["message"]["message_id"], text=text)
    except Exception:
        pass


def _download(file_id):
    path = call("getFile", file_id=file_id)["file_path"]
    fd, local = tempfile.mkstemp(suffix=os.path.splitext(path)[1] or ".ogg")
    with os.fdopen(fd, "wb") as f:
        f.write(urllib.request.urlopen(f"https://api.telegram.org/file/bot{TOKEN}/{path}", timeout=60).read())
    return local


def _on_message(msg, analyze_fn):
    chat = msg["chat"]["id"]
    if msg.get("text", "").startswith("/start"):
        call("sendMessage", chat_id=chat, text=f"Your chat id is {chat}. Enter it in TrustCheck enrolment.\n"
             "Send /code any time for your current code word.\n"
             "Or forward me any suspicious voice note or message and I'll check it.")
        return
    if msg.get("text", "").startswith("/code"):
        import codeword
        person = db.person_by_chat(chat)
        if not person:
            call("sendMessage", chat_id=chat, text="This chat isn't linked to anyone in TrustCheck yet. Ask security to add your chat id.")
            return
        call("sendMessage", chat_id=chat, text=f"Your TrustCheck code word right now:\n\n{codeword.phrase(db.code_secret(person['id'])).upper()}\n\n"
             f"It changes in {codeword.seconds_left()} s. Say it only when a colleague asks you to prove it's really you.")
        return
    media = msg.get("voice") or msg.get("audio") or msg.get("video_note") or msg.get("video") or (msg.get("photo") or [None])[-1]  # photo: largest size, a forwarded scam screenshot
    local = _download(media["file_id"]) if media else None
    try:
        r = analyze_fn(local, msg.get("text") or msg.get("caption") or "")
    finally:
        if local:
            os.remove(local)
    hi = {"HIGH": "HIGH RISK / उच्च जोखिम", "MEDIUM": "MEDIUM RISK / मध्यम जोखिम", "LOW": "LOW RISK / कम जोखिम"}[r["band"]]
    advice = ("Do not pay, share OTPs or stay on the call. Real police never 'digitally arrest' anyone. Report at cybercrime.gov.in or call 1930.\n"
              "पैसे न भेजें, OTP न बताएं। असली पुलिस 'डिजिटल अरेस्ट' नहीं करती। 1930 पर कॉल करें।") if r["band"] != "LOW" else (
              "This media looks AI-generated or manipulated, but nothing risky is being asked. Don't forward it as genuine.\n"
              "यह मीडिया नकली (AI) लगता है। इसे असली मानकर आगे न भेजें।" if r.get("synthetic_media")
              else "No strong warning signs found. Still verify through a number you already know.")
    call("sendMessage", chat_id=chat, text=f"{hi} ({r['risk']:.0f}/100)\n\n{r['summary']}\n\n{advice}")


def poll_forever(analyze_fn):
    offset = 0
    while True:
        try:
            for u in call("getUpdates", offset=offset, timeout=25) or []:
                offset = u["update_id"] + 1
                try:  # one bad update must not swallow the rest, or fail without a trace
                    if "callback_query" in u and u["callback_query"].get("data", "").startswith("v:"):
                        print("telegram: answer", u["callback_query"]["data"], flush=True)
                        _on_callback(u["callback_query"])
                    elif "message" in u:
                        m = u["message"]
                        print("telegram: message from chat", m["chat"]["id"], repr((m.get("text") or "<media>")[:40]), flush=True)
                        _on_message(m, analyze_fn)
                except Exception as e:
                    print("telegram handler error:", repr(e), flush=True)
                    chat = (u.get("message") or {}).get("chat", {}).get("id")
                    if chat:
                        call("sendMessage", chat_id=chat, text=f"Sorry, that failed on the TrustCheck server: {e}")
        except Exception as e:  # network blips must not kill the bot
            print("telegram poll error:", repr(e), flush=True)
            time.sleep(3)


def start(analyze_fn):
    if TOKEN:
        threading.Thread(target=poll_forever, args=(analyze_fn,), daemon=True).start()
        print("telegram bot polling", flush=True)
