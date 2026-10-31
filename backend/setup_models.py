"""One command to download every model and prove each one runs on this machine:
    python setup_models.py
Prints a pass/fail table. Run it once on good Wi-Fi before the hackathon (about 6 GB of downloads)."""
import time
import traceback

import numpy as np

RESULTS = []


def step(name):
    def wrap(fn):
        t = time.time()
        try:
            detail = fn() or ""
            RESULTS.append((name, "PASS", f"{time.time() - t:.0f}s {detail}"))
        except Exception as e:
            RESULTS.append((name, "FAIL", f"{type(e).__name__}: {e}"))
            traceback.print_exc()
        return fn
    return wrap


@step("ffmpeg (PATH or imageio-ffmpeg)")
def _():
    from detectors import audio
    return audio.ffmpeg_exe()


@step("Message classifier (trained)")
def _():
    from detectors import message
    if message._clf() is None:  # different sklearn version: retrain in ~20 s
        import subprocess, sys
        subprocess.run([sys.executable, "train/train_message_clf.py"], check=True)
        message._clf.cache_clear()
    p = message.classifier_prob("Urgent and confidential: transfer ₹45 lakh to the new vendor account within 30 minutes")
    assert p > 0.5, p
    return f"scam example p={p:.2f}"


SPEECHY = (np.sin(2 * np.pi * 180 * np.arange(16000 * 5) / 16000) * np.abs(np.sin(np.arange(16000 * 5) / 1600))).astype(np.float32) * 0.3


@step("pellav2 voice-clone detector")
def _():
    from detectors import audio
    tl = audio.spoof_timeline(SPEECHY)
    assert tl, "no windows scored"
    return f"{len(tl)} windows, device {audio.device()}"


@step("ECAPA voiceprint")
def _():
    from detectors import audio
    return f"{len(audio.voice_embedding(SPEECHY))}-dim embedding"


@step("faster-whisper transcription")
def _():
    from detectors import audio
    audio.transcribe(SPEECHY)
    return f"model {audio.WHISPER_SIZE}"


@step("InsightFace (face detection + ArcFace)")
def _():
    from detectors import video
    video.face_app()


@step("GenD face-swap detector + fake-class index")
def _():
    import io
    import urllib.request
    from PIL import Image
    from detectors import video
    base = "https://github.com/yermandy/deepfake-detection/blob/main/datasets/FF/{}/000.png?raw=true"
    imgs = [Image.open(io.BytesIO(urllib.request.urlopen(base.format(k), timeout=30).read())).convert("RGB") for k in ("DF/000_003", "real/000")]
    p_fake, p_real = video.fake_probs(imgs)
    assert p_fake > p_real, f"fake {p_fake:.2f} <= real {p_real:.2f}: set GEND_FAKE_INDEX={1 - video.FAKE_INDEX} in .env"
    return f"fake sample {p_fake:.2f}, real sample {p_real:.2f}"


@step("UnivFD AI-image detector")
def _():
    import tempfile
    from PIL import Image
    from detectors import image
    f = tempfile.mktemp(suffix=".png")
    Image.fromarray((np.random.rand(300, 300, 3) * 255).astype("uint8")).save(f)
    return f"p={image.univfd_prob(f):.2f} on noise"


if __name__ == "__main__":
    print("\n" + "\n".join(f"{s:5} {n:44} {d}" for n, s, d in RESULTS))
    fails = [n for n, s, _ in RESULTS if s == "FAIL"]
    print("\nAll models ready." if not fails else f"\n{len(fails)} failed. Fix those, then re-run. The app still works without them (that check is skipped).")
