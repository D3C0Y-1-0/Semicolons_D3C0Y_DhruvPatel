"""Video YES: the real person proves the YES is theirs with a 5-second selfie video.

A hacked phone or a leaked password can tap YES. It can't show the person's own live face and voice saying a code word
that didn't exist a minute ago. The clip passes only if every check passes; a check that can't run counts as a fail
(no face enrolled, no speech heard), so the YES never gets through on missing evidence. The clip is deleted after scoring.
ponytail: the random move is shown as a liveness prompt but not verified automatically; a head-pose check
(InsightFace landmarks across frames) is the upgrade path.
"""
import os
import random
import re
import subprocess
import tempfile
import time

import codeword
import db

MOVES = ["turn your head slowly to the left and back", "turn your head slowly to the right and back",
         "look up, then back at the camera", "nod twice", "touch your right cheek", "raise one hand next to your face"]


def pick_move():
    return random.choice(MOVES)


def heard_code(secret, transcript, t=None):
    """Both code words appear in what was said. The last three windows count: recording and upload take time."""
    words = set(re.findall(r"[a-z]+", (transcript or "").lower()))
    t = time.time() if t is None else t
    return any(set(codeword.phrase(secret, t - k * codeword.STEP).split()) <= words for k in range(3))


def _check(name, sig, missing, ok_why, bad_why):
    """A detector signal passes when its score is below 0.5 (no attack); no signal at all is a fail."""
    if not sig or sig.get("score") is None:
        return {"name": name, "ok": False, "detail": missing}
    ok = sig["score"] < 0.5
    return {"name": name, "ok": ok, "detail": (ok_why if ok else bad_why) + f" (score {sig['score']:.2f})"}


def score(path, person):
    from detectors import audio, identity, video
    from detectors.audio import ffmpeg_exe
    fd, mp4 = tempfile.mkstemp(suffix=".mp4")
    os.close(fd)
    try:  # phones record WebM or MP4; one known format keeps frame counts and audio decoding reliable
        subprocess.run([ffmpeg_exe(), "-nostdin", "-v", "error", "-y", "-i", path, "-c:v", "libx264", "-preset", "ultrafast",
                        "-pix_fmt", "yuv420p", "-c:a", "aac", mp4], check=True, capture_output=True)
        a = audio.analyze(mp4)
        wav = a.pop("wav")
        v = video.analyze(mp4, wav)
    finally:
        os.remove(mp4)
    sig = {s["signal"]: s for s in a["signals"] + v["signals"]}
    bio = {s["signal"]: s for s in identity.biometric_signals(person, a["voice_emb"], v["face_emb"])[0]}
    said = ((a.get("transcript") or {}).get("text") or "").strip()
    first = person["name"].split()[0]
    no_face = "no face found in the video" if not v["face_emb"] else f"{first} has no face enrolled in Trust Graph"
    no_voice = "no clear speech heard" if not a["voice_emb"] else f"{first} has no voice enrolled in Trust Graph"
    checks = [
        _check("Real face, not a face swap", sig.get("face_video"), "couldn't check the face", "face looks real", "face looks manipulated"),
        _check(f"Face matches {first}'s enrolled photo", bio.get("face_mismatch"), no_face, "same person", "a different face"),
        _check("Real voice, not a clone", sig.get("audio_spoof"), "no clear speech heard", "voice sounds human", "voice sounds synthetic"),
        _check(f"Voice matches {first}'s voiceprint", bio.get("voice_mismatch"), no_voice, "same voice", "a different voice"),
        {"name": "Said the live code word", "ok": heard_code(db.code_secret(person["id"]), said),
         "detail": f"heard: “{said[:80]}”" if said else "no words heard"},
        _check("Lips move with the words", sig.get("lip_sync"), "couldn't check lip movement", "lips match the audio", "lips don't match the audio"),
    ]
    return {"passed": all(c["ok"] for c in checks), "checks": checks, "errors": a["errors"] + v["errors"]}


def demo():
    s = "00" * 16
    now = 1_000_000.0
    p = codeword.phrase(s, now)
    assert heard_code(s, f"Hi, {p.split()[1].upper()} and {p.split()[0]}, I approve.", now)       # order and case don't matter
    assert heard_code(s, codeword.phrase(s, now - 2 * codeword.STEP), now)                      # a minute late still counts
    assert not heard_code(s, codeword.phrase(s, now - 4 * codeword.STEP), now)                  # an old recording doesn't
    assert not heard_code(s, p.split()[0], now) and not heard_code(s, "", now)                  # one word isn't enough
    c = _check("x", {"score": None}, "missing", "ok", "bad")
    assert not c["ok"] and c["detail"] == "missing"
    assert _check("x", {"score": 0.1}, "m", "ok", "bad")["ok"] and not _check("x", {"score": 0.9}, "m", "ok", "bad")["ok"]
    assert pick_move() in MOVES
    print("videoyes ok:", p)


if __name__ == "__main__":
    demo()
