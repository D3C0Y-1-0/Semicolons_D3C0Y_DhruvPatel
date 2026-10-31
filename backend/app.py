"""TrustCheck API. Run: uvicorn app:app --reload --port 8000"""
import asyncio
import datetime as dt
import os
import random
import shutil
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import PlainTextResponse  # noqa: E402

import db  # noqa: E402
import fusion  # noqa: E402
import report  # noqa: E402
import verify  # noqa: E402
from detectors import identity, message  # noqa: E402

AUDIO_EXT = {".wav", ".mp3", ".m4a", ".ogg", ".opus", ".flac", ".aac", ".amr"}
VIDEO_EXT = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".3gp"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic"}

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
            im = image.analyze(media_path)
            signals += im["signals"]; errors += im["errors"]; face_emb = im["face_emb"]

    msg_signals, facts, info = message.analyze(text, eml_bytes, approval_limit=(person or {}).get("approval_limit"))
    signals += msg_signals
    if not person:
        person = db.find_person_by_domain_or_name(text + " " + str((info.get("header") or {}).get("from", "")))
    b_sig, b_facts = identity.biometric_signals(person, voice_emb, face_emb)
    c_sig, c_facts = identity.context_signal(person, channel, sender or facts.get("sender_email"), hour,
                                            facts.get("action", "none"), facts.get("amount_inr"))
    signals += b_sig + c_sig
    facts |= b_facts | c_facts

    result = fusion.fuse(signals, facts.get("action", "none"), facts)
    result |= {"summary": "", "facts": facts, "channel": channel, "sender": sender, "errors": errors,
               "claimed_person": {"id": person["id"], "name": person["name"], "role": person.get("role")} if person else None,
               "message": info, **extra}
    result["summary"] = summarise(result)
    result["recommended_actions"] = ACTIONS[result["band"]]
    if facts.get("digital_arrest"):
        result["recommended_actions"] = ["Hang up. Real police, CBI or courts never arrest anyone over a video call",
                                         "Don't pay or share any OTP, even 'for verification'",
                                         "Call the national cyber helpline 1930 or report at cybercrime.gov.in",
                                         "Tell a family member; scammers rely on keeping you isolated on the call"]
    if media_path and result["band"] != "LOW":
        result["challenge"] = challenge()
    result["_voice_emb"] = voice_emb  # kept server-side for campaign clustering, stripped before responding
    return result


def finish(result):
    """Save the case, attach campaign info, drop server-only fields."""
    voice_emb = result.pop("_voice_emb", None)
    result["case_id"], result["campaign"] = db.save_case(result, (result.get("claimed_person") or {}).get("id"), voice_emb)
    return result


def citizen_analyze(path, text):
    return finish(run_analysis(path, text, channel="telegram"))


@asynccontextmanager
async def lifespan(_):
    db.conn().close()
    verify.start(citizen_analyze)
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
    return {"ok": True, "telegram": bool(verify.TOKEN), "llm": bool(os.getenv("ANTHROPIC_API_KEY"))}


@app.post("/analyze")
async def analyze(text: str = Form(""), channel: str = Form(None), sender: str = Form(None),
                  claimed_person_id: str = Form(None), hour: int = Form(None),
                  media: UploadFile = File(None), eml: UploadFile = File(None)):
    path = await _save(media)
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
async def enroll(name: str = Form(...), role: str = Form(""), email: str = Form(""), phone: str = Form(""),
                 telegram_chat_id: str = Form(""), channels: str = Form("email"), work_start: int = Form(9),
                 work_end: int = Form(19), approval_limit: float = Form(0), usual_requests: str = Form("information"),
                 voice: UploadFile = File(None), photo: UploadFile = File(None)):
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
    pid = db.add_person(name=name, role=role, email=email, phone=phone, telegram_chat_id=telegram_chat_id,
                        channels=split(channels), work_start=work_start, work_end=work_end,
                        approval_limit=approval_limit, usual_requests=split(usual_requests),
                        voice_emb=voice_emb, face_emb=face_emb)
    return {"id": pid, "voice_enrolled": bool(voice_emb), "face_enrolled": bool(face_emb)}


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
    c = db.get_case(cid)
    if not c:
        raise HTTPException(404)
    cp = c["result"].get("claimed_person")
    try:
        verify.send_verification(c, db.get_person(cp["id"]) if cp else None)
    except Exception as e:
        raise HTTPException(400, str(e))
    return db.update_case(cid, status="verifying")


@app.post("/cases/{cid}/decision")
def decision(cid: str, answer: str = Form(...)):
    """Manual fallback when Telegram is unreachable: answer = yes | no."""
    return db.update_case(cid, status="verified" if answer == "yes" else "confirmed_attack",
                          result_patch={"verification": {"answer": answer, "manual": True}})


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
                tr = await asyncio.to_thread(audio.transcribe, wav[done:], os.getenv("WHISPER_LIVE_SIZE", "small"))
                transcript = (transcript + " " + tr["text"]).strip()
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
