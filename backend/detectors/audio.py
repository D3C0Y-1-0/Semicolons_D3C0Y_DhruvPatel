"""Audio: voice-clone detection (pellav2), voiceprint (ECAPA), transcript (faster-whisper).

Every model loads lazily on first use. If one is missing, its signal comes back with score None
and an error string, and the rest of the pipeline keeps working.
"""
import functools
import importlib.util
import os
import subprocess
from pathlib import Path

import numpy as np

SR = 16000
WIN, HOP = 4 * SR, 2 * SR  # pellav2 scores 4 s crops; 2 s hop gives a timeline
SILENCE_RMS = 0.005
CACHE = Path(__file__).resolve().parent.parent / "model_cache"
PELLA_REPO = "Sadanie/pellav2-audio-deepfake-detector"
# Security: pellav2's model class is downloaded code. Pin a commit hash here once you've read it.
PELLA_REVISION = os.getenv("PELLAV2_REVISION", "main")
WHISPER_SIZE = os.getenv("WHISPER_SIZE", "large-v3")


def device():
    import torch
    if torch.cuda.is_available():
        return "cuda"
    return "mps" if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available() else "cpu"


def load_audio(path):
    """Any audio or video file -> mono 16 kHz float32. Needs ffmpeg on PATH."""
    out = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(out, np.float32).copy()


@functools.cache
def pellav2():
    import torch
    from huggingface_hub import hf_hub_download
    src = hf_hub_download(PELLA_REPO, "pellav2_infer.py", revision=PELLA_REVISION)
    spec = importlib.util.spec_from_file_location("pellav2_infer", src)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    model = mod.Detector()
    weights = hf_hub_download(PELLA_REPO, "pellav2_detector.pt", revision=PELLA_REVISION)
    model.load_state_dict(torch.load(weights, map_location="cpu"))
    return model.to(device()).eval()


def windows(wav):
    """Yield (start_sample, window) covering the clip; short clips are zero-padded like pellav2 does."""
    if len(wav) < WIN:
        yield 0, np.pad(wav, (0, WIN - len(wav)))
        return
    starts = list(range(0, len(wav) - WIN + 1, HOP))
    if starts[-1] + WIN < len(wav):
        starts.append(len(wav) - WIN)
    for s in starts:
        yield s, wav[s:s + WIN]


def spoof_timeline(wav):
    """[{start, end, p_fake}] per non-silent 4 s window."""
    import torch
    model, dev = pellav2(), device()
    items = [(s, w) for s, w in windows(wav) if np.sqrt(np.mean(w ** 2)) >= SILENCE_RMS]
    out = []
    for i in range(0, len(items), 8):
        batch = np.stack([(w - w.mean()) / (w.std() + 1e-7) for _, w in items[i:i + 8]])
        with torch.no_grad():
            p = torch.sigmoid(model(torch.from_numpy(batch).float().to(dev)).reshape(-1)).cpu().tolist()
        out += [{"start": round(s / SR, 2), "end": round(min(s + WIN, len(wav)) / SR, 2), "p_fake": round(q, 3)}
                for (s, _), q in zip(items[i:i + 8], p)]
    return out


def peaks(wav, n=600):
    """Waveform envelope for the UI: n max-abs values scaled 0..1."""
    if not len(wav):
        return []
    chunks = np.array_split(np.abs(wav), min(n, len(wav)))
    p = np.array([c.max() for c in chunks])
    return np.round(p / (p.max() + 1e-9), 3).tolist()


def clip_score(timeline):
    """Mean of the worst 30% of windows: one cloned sentence inside real speech still shows up."""
    ps = sorted((w["p_fake"] for w in timeline), reverse=True)
    k = max(1, round(len(ps) * 0.3))
    return round(sum(ps[:k]) / k, 3) if ps else None


@functools.cache
def ecapa():
    from speechbrain.inference.speaker import EncoderClassifier
    kw = {}
    try:  # Windows without developer mode cannot create symlinks
        from speechbrain.utils.fetching import LocalStrategy
        kw["local_strategy"] = LocalStrategy.COPY
    except ImportError:
        pass
    return EncoderClassifier.from_hparams(source="speechbrain/spkrec-ecapa-voxceleb", savedir=str(CACHE / "ecapa"),
                                          run_opts={"device": device()}, **kw)


def voice_embedding(wav):
    import torch
    with torch.no_grad():
        return ecapa().encode_batch(torch.from_numpy(wav).unsqueeze(0)).reshape(-1).cpu().tolist()


@functools.cache
def whisper(size):
    from faster_whisper import WhisperModel
    return WhisperModel(size, device="auto", compute_type="int8")


def transcribe(wav, size=None):
    segments, info = whisper(size or WHISPER_SIZE).transcribe(wav, word_timestamps=True, vad_filter=True)
    words, text = [], []
    for seg in segments:
        text.append(seg.text.strip())
        words += [{"word": w.word, "start": round(w.start, 2), "end": round(w.end, 2)} for w in (seg.words or [])]
    return {"text": " ".join(text), "words": words, "language": info.language}


def analyze(path=None, wav=None, want_voiceprint=True, want_transcript=True, whisper_size=None):
    wav = load_audio(path) if wav is None else wav
    res = {"duration": round(len(wav) / SR, 2), "signals": [], "errors": [], "timeline": [],
           "transcript": None, "voice_emb": None, "peaks": peaks(wav), "wav": wav}
    try:
        res["timeline"] = spoof_timeline(wav)
        score = clip_score(res["timeline"])
        flagged = [w for w in res["timeline"] if w["p_fake"] >= 0.5]
        res["signals"].append({
            "signal": "audio_spoof", "label": "Synthetic voice (pellav2)", "score": score,
            "why": (f"voice sounds synthetic in {len(flagged)} of {len(res['timeline'])} segments" if flagged
                    else "voice sounds natural in every segment"),
            "evidence": [{"type": "audio", "start": w["start"], "end": w["end"], "text": f"p(fake) {w['p_fake']:.2f}"} for w in flagged]})
    except Exception as e:
        res["errors"].append(f"audio spoof model unavailable: {e}")
        res["signals"].append({"signal": "audio_spoof", "label": "Synthetic voice (pellav2)", "score": None, "why": "model unavailable", "evidence": []})
    if want_voiceprint:
        try:
            res["voice_emb"] = voice_embedding(wav)
        except Exception as e:
            res["errors"].append(f"voiceprint model unavailable: {e}")
    if want_transcript:
        try:
            res["transcript"] = transcribe(wav, whisper_size)
        except Exception as e:
            res["errors"].append(f"transcription unavailable: {e}")
    return res


if __name__ == "__main__":
    # No model needed: window maths self-check
    tl = [{"p_fake": p} for p in (0.1, 0.2, 0.95, 0.9, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1)]
    assert clip_score(tl) == 0.683, clip_score(tl)  # top 3 of 10 = (0.95+0.9+0.2)/3
    assert [s for s, _ in windows(np.zeros(SR * 9, np.float32))] == [0, 2 * SR, 4 * SR, 5 * SR]
    assert len(list(windows(np.zeros(SR, np.float32)))) == 1
    print("audio maths ok")
