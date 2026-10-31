"""TrustCheck API. Run: uvicorn app:app --reload --port 8000"""
import asyncio
import datetime as dt
import os
import random
import shutil
import tempfile
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import HTMLResponse, PlainTextResponse, Response  # noqa: E402

import codeword  # noqa: E402
import db  # noqa: E402
import fusion  # noqa: E402
import mules  # noqa: E402
import notify  # noqa: E402
import report  # noqa: E402
import verify  # noqa: E402
from detectors import identity, message  # noqa: E402

AUDIO_EXT = {".wav", ".mp3", ".m4a", ".ogg", ".opus", ".flac", ".aac", ".amr"}
VIDEO_EXT = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".3gp"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic"}
TEXT_EXT = {".txt"}  # a pasted chat export: read as the message
MAX_TEXT = 50_000  # characters checked; a longer paste is cut, the verdict notes nothing about the rest
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "200"))
LIVE_CONTEXT_S = 90  # seconds of the call the live transcript covers
HOLD_MINUTES = int(os.getenv("HOLD_MINUTES", "30"))  # cooling-off lock on HIGH payment/credential requests

CHALLENGES = [  # GOTCHA (NYU): occlusion and face deformation break real-time deepfakes best
    "Ask them to slowly wave a hand across their face.",
    "Ask them to press a finger into their cheek and hold it there.",
    "Ask them to take off or put on their glasses.",
    "Ask them to pull a big surprised face, then smile.",
    "Ask for the team code word. Never say it first yourself.",
    "Say you'll call back on their registered number, hang up, and do it.",
]
PHRASE_WORDS = ["mango", "seven", "river", "blue", "tiger", "window", "pencil", "monsoon", "cricket", "lantern"]

ACTIONS = {
    "HIGH": ["Do not pay, share data or credentials yet", "Verify through a separately trusted channel (button below)",
             "Escalate to the security team", "Payment is on hold until verified"],
    "MEDIUM": ["Pause before acting", "Use a challenge question on the call", "Verify through the person's registered number"],
    "LOW": ["No strong warning signs; normal caution applies"],
}


def challenge():
    c = random.choice(CHALLENGES + ["phrase"])
    return f"Ask them to repeat: '{' '.join(random.sample(PHRASE_WORDS, 3))}'" if c == "phrase" else c


_ocr = []


def screenshot_text(path):
    """Text in a screenshot (forwarded WhatsApp/SMS scams), read offline with RapidOCR on the GPU runtime. '' if none."""
    try:
        import cv2
        if not _ocr:
            from rapidocr_onnxruntime import RapidOCR
            _ocr.append(RapidOCR())
        res, _ = _ocr[0](cv2.imread(path))
        return "\n".join(r[1] for r in res or [] if r[2] >= 0.5)
    except Exception:  # OCR not installed or unreadable image: fall back to the image checks
        return ""


def qr_codes(path):
    """Decoded QR payloads in an image (OpenCV, already installed for the face models)."""
    import cv2
    try:
        ok, data, _, _ = cv2.QRCodeDetector().detectAndDecodeMulti(cv2.imread(path))
        return [d for d in (data if ok else []) if d]
    except Exception:
        return []


def summarise(result):
    pos = [s for s in result["signals"] if s["contribution"] > 0][:3]
    parts = [s["why"] for s in pos] + [f"policy: {r}" for r in result["rules_fired"]]
    body = "; ".join(parts)
    return f"{result['band']} risk. " + (body[:1].upper() + body[1:] + "." if parts else "No strong warning signs.")


def run_analysis(media_path=None, text="", eml_bytes=None, claimed_id=None, channel=None, sender=None, hour=None):
    from detectors import audio, image, video  # heavy imports only when media arrives
    signals, errors, extra = [], [], {}
    voice_emb = face_emb = None
    person = db.get_person(claimed_id) if claimed_id else None
    text = message.normalize(text)[:MAX_TEXT]  # look-alike Unicode and hidden characters can't dodge the checks

    if media_path:
        ext = Path(media_path).suffix.lower()
        wav = None
        if ext in AUDIO_EXT or ext in VIDEO_EXT:
            try:
                a = audio.analyze(media_path)
                wav = a.pop("wav")
                signals += a["signals"]; errors += a["errors"]; voice_emb = a["voice_emb"]
                extra |= {"timeline": a["timeline"], "duration": a["duration"], "transcript": a["transcript"], "peaks": a["peaks"]}
                if a["transcript"] and a["transcript"]["text"]:
                    text = (text + "\n" if text else "") + a["transcript"]["text"]
            except Exception as e:  # e.g. video without an audio track
                errors.append(f"no usable audio: {e}")
        if ext in VIDEO_EXT:
            v = video.analyze(media_path, wav)
            signals += v["signals"]; errors += v["errors"]; face_emb = v["face_emb"]; extra["frames"] = v["frames"]
            extra.setdefault("duration", max([f["t"] for f in v["frames"]], default=0) + 1)
        if ext in IMAGE_EXT:
            shot = screenshot_text(media_path)
            if len(shot) >= 40:  # a screenshot of a chat or SMS: read the scam; AI-image forensics on app pixels would only raise false alarms
                extra["screenshot_text"] = shot
                text = (text + "\n" if text else "") + shot
            else:
                im = image.analyze(media_path)
                signals += im["signals"]; errors += im["errors"]; face_emb = im["face_emb"]
            extra["qr"] = qr_codes(media_path)  # "scan to receive money" QR scams: the payload goes through the text checks
            if extra["qr"]:
                text = (text + "\n" if text else "") + "\n".join("QR code: " + q for q in extra["qr"])

    msg_signals, facts, info = message.analyze(text, eml_bytes, approval_limit=(person or {}).get("approval_limit"))
    signals += msg_signals
    mule_sig, mule_facts, identifiers = mules.signals(f"{text}\n{sender or ''}")
    signals += mule_sig
    facts |= mule_facts
    if not person:
        person = db.find_person_by_domain_or_name(text + " " + str((info.get("header") or {}).get("from", "")))
    b_sig, b_facts = identity.biometric_signals(person, voice_emb, face_emb)
    c_sig, c_facts = identity.context_signal(person, channel, sender or facts.get("sender_email"), hour,
                                            facts.get("action", "none"), facts.get("amount_inr"))
    signals += b_sig + c_sig
    facts |= b_facts | c_facts

    result = fusion.fuse(signals, facts.get("action", "none"), facts)
    result |= {"summary": "", "facts": facts, "channel": channel, "sender": sender, "errors": errors,
               "claimed_person": {"id": person["id"], "name": person["name"], "role": person.get("role"),
                                  "telegram": bool(person.get("telegram_chat_id"))} if person else None,
               "message": info, "identifiers": identifiers, "scam_types": info.get("scam_types", []), **extra}
    # spec 7: even a LOW verdict badges media that looks synthetic (weak "no provenance" metadata doesn't count)
    result["synthetic_media"] = any((s["score"] or 0) >= (0.9 if s["signal"] == "image_synthetic" else 0.5)
                                    for s in signals if s["signal"] in ("audio_spoof", "face_video", "image_univfd", "image_synthetic"))
    result["summary"] = summarise(result)
    result["recommended_actions"] = ACTIONS[result["band"]]
    if result["synthetic_media"] and result["band"] == "LOW":
        result["recommended_actions"] = ["Nothing risky is being asked, so no need to block it",
                                         "Don't forward or rely on this media as genuine: it looks AI-generated or manipulated"]
    if result["scam_types"] and result["band"] != "LOW":  # say what this scam is and the one thing that beats it
        result["recommended_actions"] = list(dict.fromkeys(t["advice"] for t in result["scam_types"]))[:2] + ACTIONS[result["band"]][:1] + [
            "Tell colleagues and family: the same scam often goes to several people"]
    if facts.get("digital_arrest"):
        result["recommended_actions"] = ["Hang up. Real police, CBI or courts never arrest anyone over a video call",
                                         "Don't pay or share any OTP, even 'for verification'",
                                         "Call the national cyber helpline 1930 or report at cybercrime.gov.in",
                                         "Tell a family member; scammers rely on keeping you isolated on the call"]
    if media_path and result["band"] != "LOW":
        result["challenge"] = challenge()
    if result["band"] == "HIGH" and result["action"] in ("payment", "payment_high", "credentials"):
        result["hold_until"] = time.time() + HOLD_MINUTES * 60  # only the real person's YES lifts it early
    result["_voice_emb"] = voice_emb  # kept server-side for campaign clustering, stripped before responding
    return result


def finish(result):
    """Save the case, attach campaign info, drop server-only fields."""
    voice_emb = result.pop("_voice_emb", None)
    result["case_id"], result["campaign"] = db.save_case(result, (result.get("claimed_person") or {}).get("id"), voice_emb)
    return result


def citizen_analyze(path, text):
    return finish(run_analysis(path, text, channel="telegram"))


WARM = {"state": "cold", "seconds": None, "failed": []}


def warm_up():
    """Load every model once at startup, so the first voice or video check on stage isn't the slow one."""
    from detectors import audio, image, video
    WARM["state"], t0 = "warming", time.time()
    for name, load in [("voice-clone detector", audio.pellav2), ("voiceprint", audio.ecapa),
                       ("transcriber", lambda: audio.whisper(audio.WHISPER_SIZE, audio.WHISPER_DEVICE)),
                       ("face finder", video.face_app), ("face-swap detector", video.gend), ("AI-image detector", image.univfd),
                       ("message classifier", message._clf),
                       ("screenshot reader", lambda: screenshot_text(os.path.join(os.path.dirname(__file__), "models", "warmup.png")))]:
        try:
            load()
        except Exception as e:  # a missing model only switches its signal off; the app keeps working
            WARM["failed"].append(f"{name}: {e}")
    WARM["state"], WARM["seconds"] = "ready", round(time.time() - t0)
    print(f"models warm in {WARM['seconds']} s" + (f", unavailable: {WARM['failed']}" if WARM["failed"] else ""), flush=True)


@asynccontextmanager
async def lifespan(_):
    db.conn().close()
    verify.start(citizen_analyze)
    if os.getenv("WARMUP", "1") != "0":  # WARMUP=0 for a quick backend restart while editing code
        threading.Thread(target=warm_up, daemon=True).start()
    yield


app = FastAPI(title="TrustCheck", lifespan=lifespan)
# Demo only: open CORS, no auth. Lock both down before any real deployment.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


async def _save(upload):
    if not upload or not upload.filename:
        return None
    fd, path = tempfile.mkstemp(suffix=Path(upload.filename).suffix.lower())
    with os.fdopen(fd, "wb") as f:
        shutil.copyfileobj(upload.file, f)
    return path


@app.get("/health")
def health():
    return {"ok": True, "telegram": bool(verify.TOKEN), "llm": bool(os.getenv("ANTHROPIC_API_KEY")),
            "email": notify.smtp_ready(), "public_url": notify.public_url(), "models": WARM["state"]}


@app.post("/analyze")
async def analyze(text: str = Form(""), channel: str = Form(None), sender: str = Form(None),
                  claimed_person_id: str = Form(None), hour: int = Form(None),
                  media: UploadFile = File(None), eml: UploadFile = File(None)):
    path = await _save(media)
    if path:
        ext = Path(path).suffix.lower()
        if os.path.getsize(path) > MAX_UPLOAD_MB * 1024 * 1024:
            os.remove(path)
            raise HTTPException(413, f"That file is over {MAX_UPLOAD_MB} MB. Trim the recording to the part with the request.")
        if ext in TEXT_EXT:
            with open(path, encoding="utf-8", errors="replace") as fh:
                text = (text + "\n" if text else "") + fh.read(MAX_TEXT)
            os.remove(path)
            path = None
        elif ext not in AUDIO_EXT | VIDEO_EXT | IMAGE_EXT:
            os.remove(path)
            raise HTTPException(415, f"{ext or 'That'} files can't be checked. Use a voice note, video, image or screenshot "
                                     "(.opus .mp3 .wav .mp4 .jpg .png), a .txt export, or paste the text.")
    eml_bytes = await eml.read() if eml and eml.filename else None
    if hour is None:
        hour = dt.datetime.now().hour
    try:
        result = await asyncio.to_thread(run_analysis, path, text, eml_bytes, claimed_person_id or None,
                                         channel or None, sender or None, hour)
    finally:
        if path:
            os.remove(path)  # privacy: raw media is never kept
    return finish(result)


@app.get("/stats")
def stats():
    return db.stats()


@app.post("/enroll")
async def enroll(id: str = Form(None), name: str = Form(...), role: str = Form(""), email: str = Form(""), phone: str = Form(""),
                 telegram_chat_id: str = Form(""), channels: str = Form("email"), work_start: int = Form(9),
                 work_end: int = Form(19), approval_limit: float = Form(0), usual_requests: str = Form("information"),
                 voice: UploadFile = File(None), photo: UploadFile = File(None)):
    name, role, email, phone, telegram_chat_id = (v.strip() for v in (name, role, email, phone, telegram_chat_id))
    if not (0 <= work_start <= 23 and 0 <= work_end <= 23):
        raise HTTPException(400, "Working hours must be between 0 and 23.")
    if approval_limit < 0:
        raise HTTPException(400, "Approval limit can't be negative.")
    voice_emb = face_emb = None
    vp, pp = await _save(voice), await _save(photo)
    try:
        if vp:
            from detectors import audio
            voice_emb = await asyncio.to_thread(lambda: audio.voice_embedding(audio.load_audio(vp)))
        if pp:
            from detectors import video
            _, face_emb, err = await asyncio.to_thread(video.image_face, pp)
            if err or face_emb is None:
                raise HTTPException(400, err or "no face found in the photo")
    finally:
        for p in (vp, pp):
            if p:
                os.remove(p)
    split = lambda s: [x.strip().lower() for x in s.split(",") if x.strip()]
    pid = db.add_person(id=id or None, name=name, role=role, email=email, phone=phone, telegram_chat_id=telegram_chat_id,
                        channels=split(channels), work_start=work_start, work_end=work_end,
                        approval_limit=approval_limit, usual_requests=split(usual_requests),
                        voice_emb=voice_emb, face_emb=face_emb)
    p = db.get_person(pid)
    return {"id": pid, "voice_enrolled": bool(p["voice_emb"]), "face_enrolled": bool(p["face_emb"])}


@app.get("/people")
def people():
    return db.list_people()


@app.get("/cases")
def cases():
    return db.list_cases()


@app.get("/cases/{cid}")
def case(cid: str):
    c = db.get_case(cid)
    if not c:
        raise HTTPException(404)
    return c


@app.post("/verify/{cid}")
def send_verify(cid: str):
    """Ask the real person, out of band: email goes out by itself (or one-tap mailto), plus a QR."""
    c = db.get_case(cid)
    if not c:
        raise HTTPException(404)
    cp = c["result"].get("claimed_person")
    person = db.get_person(cp["id"]) if cp else None
    if not person:
        raise HTTPException(400, "This message doesn't name anyone in the Trust Graph, so there's nobody to ask. "
                                 "Call the person it claims to be on a number you already know.")
    out = notify.deliver(person, "TrustCheck: did you send this request?", notify.request_text(c, person))
    out["link"] = notify.case_link(c, person["id"])
    if person.get("telegram_chat_id") and verify.TOKEN:
        try:
            verify.send_verification(c, person)
            out["sent"].append("telegram")
        except Exception as e:
            out["errors"].append(f"telegram failed: {e}")
    return {**db.update_case(cid, status="verifying"), "delivery": out}


@app.post("/cases/{cid}/decision")
def decision(cid: str, answer: str = Form(...)):
    """Recorded by the employee after checking another way, e.g. a call to the registered number: answer = yes | no."""
    if answer not in ("yes", "no"):
        raise HTTPException(400, "answer must be yes or no")
    return notify.record_answer(cid, answer, "manual")


def _case_person(cid):
    c = db.get_case(cid)
    pid = (c or {}).get("claimed_person_id") or ((c or {}).get("result", {}).get("claimed_person") or {}).get("id")
    if not c or not pid:
        raise HTTPException(404)
    return c, db.get_person(pid)


@app.get("/v/{cid}", response_class=HTMLResponse)
def verify_page(cid: str, t: str = ""):
    """The page the real person opens from the email or the QR code."""
    c, p = _case_person(cid)
    if not notify.signed(p["id"], "v:" + cid, t):
        raise HTTPException(403, "This link isn't valid.")
    return notify.case_page(c, p, t)


@app.post("/v/{cid}", response_class=HTMLResponse)
def verify_answer(cid: str, t: str = Form(""), answer: str = Form(...)):
    c, p = _case_person(cid)
    if not notify.signed(p["id"], "v:" + cid, t) or answer not in ("yes", "no"):
        raise HTTPException(403, "This link isn't valid.")
    c = notify.record_answer(cid, answer, "link")
    return notify.case_page(c, p, t, answered=c["result"].get("verification", {}).get("answer"))


@app.get("/me/{pid}", response_class=HTMLResponse)
def me_page(pid: str, t: str = ""):
    """The person's own page: live code word plus anything waiting for their answer. Works on any phone browser."""
    p = db.get_person(pid)
    if not p or not notify.signed(pid, "me", t):
        raise HTTPException(403, "This link isn't valid.")
    return notify.me_page(p, t)


@app.get("/me/{pid}/code")
def me_code(pid: str, t: str = ""):
    if not db.get_person(pid) or not notify.signed(pid, "me", t):
        raise HTTPException(403)
    return {"phrase": codeword.phrase(db.code_secret(pid)), "seconds_left": codeword.seconds_left(),
            "pending": notify.pending_for(pid)}


@app.post("/people/{pid}/invite")
def invite(pid: str):
    """Send someone their personal code-word page once, by email or as a QR code."""
    p = db.get_person(pid)
    if not p:
        raise HTTPException(404)
    link = notify.me_link(pid)
    text = (f"Hi {p['name'].split()[0]}, this is your TrustCheck page: {link}\nIt shows your code word, which changes every 30 seconds. "
            "If a colleague asks you to prove a call or message is really from you, read it out. Save the link; don't share it.")
    return {**notify.deliver(p, "Your TrustCheck code-word page", text), "link": link}


@app.get("/qr")
def qr(data: str):
    """QR code PNG for a link, so a phone can open it straight from the screen."""
    import cv2
    img = cv2.resize(cv2.QRCodeEncoder.create().encode(data[:900]), None, fx=8, fy=8, interpolation=cv2.INTER_NEAREST)
    img = cv2.copyMakeBorder(img, 24, 24, 24, 24, cv2.BORDER_CONSTANT, value=255)
    return Response(cv2.imencode(".png", img)[1].tobytes(), media_type="image/png")


@app.post("/cases/{cid}/decoy")
def decoy(cid: str, scammer: str = Form("")):
    """Decoy Mode: the next reply to send the scammer; their replies are mined for mule accounts."""
    c = db.get_case(cid)
    if not c:
        raise HTTPException(404)
    state = mules.decoy_turn(c, scammer)
    db.update_case(cid, result_patch={"decoy": state})
    return state


@app.get("/mules")
def mule_list():
    return [{**m, "label": mules.LABEL.get(m["kind"], m["kind"])} for m in db.list_mules()]


@app.post("/people/{pid}/code")
def code_check(pid: str, said: str = Form(...)):
    """Human 2FA: did the caller say the claimed person's current code word? The word itself never leaves the server."""
    secret = db.code_secret(pid)
    if not secret:
        raise HTTPException(404)
    return {"match": codeword.check(secret, said), "person": db.get_person(pid)["name"]}


@app.get("/cases/{cid}/report", response_class=PlainTextResponse)
def cert_in(cid: str):
    c = db.get_case(cid)
    if not c:
        raise HTTPException(404)
    return report.cert_in_draft(c, os.getenv("ORG_NAME"))


@app.websocket("/live/{session}")
async def live(ws: WebSocket, session: str, claimed_person_id: str = None, channel: str = "meet"):
    """Live Call Guard: receives MediaRecorder webm/opus chunks, replies with a risk update per chunk.
    ponytail: re-decodes the whole stream each chunk (O(n)); fine for a few-minute call, use a streaming decoder if longer."""
    from detectors import audio
    await ws.accept()
    person = db.get_person(claimed_person_id) if claimed_person_id else None
    buf, done, timeline, transcript, voice_emb = bytearray(), 0, [], "", None
    fd, tmp = tempfile.mkstemp(suffix=".webm")
    os.close(fd)
    try:
        while True:
            buf += await ws.receive_bytes()
            Path(tmp).write_bytes(buf)
            try:
                wav = await asyncio.to_thread(audio.load_audio, tmp)
            except Exception:
                continue  # chunk boundary mid-frame; next chunk completes it
            new = wav[max(0, done - audio.WIN // 2):]  # overlap so windows span chunk edges
            if len(wav) - done < audio.SR * 2:
                continue
            try:
                tl = await asyncio.to_thread(audio.spoof_timeline, new)
                off = max(0, done - audio.WIN // 2) / audio.SR
                timeline += [w | {"start": round(w["start"] + off, 2), "end": round(w["end"] + off, 2)} for w in tl]
            except Exception:
                pass
            try:
                # Re-transcribe the recent call as one piece: 3 s fragments cut words in half ("Please tr-") and
                # hid the payment request. ponytail: older speech drops out after LIVE_CONTEXT_S; keep a rolling summary if calls run long.
                tr = await asyncio.to_thread(audio.transcribe, wav[-LIVE_CONTEXT_S * audio.SR:],
                                             os.getenv("WHISPER_LIVE_SIZE", "small"))
                transcript = tr["text"].strip() or transcript
            except Exception:
                pass
            if voice_emb is None and person and len(wav) >= audio.SR * 6:
                try:
                    voice_emb = await asyncio.to_thread(audio.voice_embedding, wav)
                except Exception:
                    voice_emb = False
            done = len(wav)

            signals = []
            if timeline:
                signals.append({"signal": "audio_spoof", "label": "Synthetic voice (live)", "score": audio.clip_score(timeline),
                                "why": f"{sum(w['p_fake'] >= .5 for w in timeline)} of {len(timeline)} segments sound synthetic", "evidence": []})
            m_sig, facts, info = message.analyze(transcript, approval_limit=(person or {}).get("approval_limit"))
            mule_sig, mule_facts, _ = mules.signals(transcript)
            m_sig += mule_sig
            facts |= mule_facts
            b_sig, b_facts = identity.biometric_signals(person, voice_emb or None)
            c_sig, c_facts = identity.context_signal(person, channel, None, dt.datetime.now().hour,
                                                    facts.get("action", "none"), facts.get("amount_inr"))
            facts |= b_facts | c_facts
            r = fusion.fuse(signals + m_sig + b_sig + c_sig, facts.get("action", "none"), facts)
            r["summary"] = summarise(r)
            await ws.send_json({"risk": r["risk"], "band": r["band"], "summary": r["summary"], "seconds": round(len(wav) / audio.SR),
                                "transcript": transcript[-600:], "tactics": info.get("tactics", []),
                                "timeline": timeline[-30:], "challenge": challenge() if r["band"] != "LOW" else None})
    except WebSocketDisconnect:
        pass
    finally:
        os.remove(tmp)
