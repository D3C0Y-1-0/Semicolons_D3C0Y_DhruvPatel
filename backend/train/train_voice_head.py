"""Measures pellav2 (cloned-voice detector) on Indian English and Hindi, and adapts its head to them.

Data (built on this laptop):
  real: LibriSpeech dev-clean (CC BY 4.0, English, 40 speakers) + FLEURS hi_in dev (CC BY 4.0, Hindi)
  fake: neural TTS (Microsoft Edge voices, en-IN / hi-IN / en-US / en-GB) reading the SAME transcripts, and
        Windows desktop TTS (David, Hazel, Zira) as an engine the model never trains on
Every clip, real or fake, is MP3-encoded the same way (so codec artefacts carry no signal), and a second copy goes
through Opus 16 kbps, the WhatsApp voice-note codec.

Split: real speakers and fake voices are held out whole (no voice appears in both train and test); Windows TTS is
test-only. Model: the w2v-BERT backbone stays frozen; only pellav2's 1024->1 head is refit, from its original
weights and pulled back towards them (L2), so it can't forget the cloning systems it was trained on.

Run from backend/:  python train/train_voice_head.py --stage prep   (downloads + TTS, CPU and network only)
                    python train/train_voice_head.py --stage train  (GPU: embeddings, fit, report)
Writes models/pellav2_head_tuned.pt (used by detectors/audio.py when present) and eval/voice_head_report.md.
ponytail: no voice-CLONING engine (XTTS, F5-TTS) in the fake set yet; add consented team clones to close that gap.
"""
import argparse
import asyncio
import csv
import json
import random
import subprocess
import sys
import tarfile
import time
import urllib.request
from pathlib import Path

import numpy as np

import os
os.environ["USE_TUNED_HEADS"] = "0"  # always start from (and compare against) the original heads

HERE = Path(__file__).resolve().parent
BACKEND = HERE.parent
sys.path.insert(0, str(BACKEND))
DATA = HERE / "data" / "big" / "voice"
OUT = BACKEND / "models" / "pellav2_head_tuned.pt"
REPORT = BACKEND.parent / "eval" / "voice_head_report.md"
LIBRI = "https://www.openslr.org/resources/12/dev-clean.tar.gz"
FLEURS = "https://huggingface.co/datasets/google/fleurs/resolve/main/data/hi_in"
EDGE = {"en": ["en-IN-NeerjaNeural", "en-IN-PrabhatNeural", "en-US-GuyNeural", "en-US-AriaNeural", "en-GB-RyanNeural"],
        "hi": ["hi-IN-SwaraNeural", "hi-IN-MadhurNeural"]}
TEST_VOICES = {"en-IN-PrabhatNeural", "en-GB-RyanNeural", "hi-IN-MadhurNeural"}  # never seen in training
SAPI = ["Microsoft David Desktop", "Microsoft Hazel Desktop", "Microsoft Zira Desktop"]


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def fetch(url, dest):
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        log("downloading", url)
        urllib.request.urlretrieve(url, dest.with_suffix(".part"))
        dest.with_suffix(".part").rename(dest)
    return dest


def ffmpeg(*args):
    from detectors.audio import ffmpeg_exe
    subprocess.run([ffmpeg_exe(), "-nostdin", "-v", "error", "-y", *map(str, args)], check=True)


def prep_real(n_en, n_hi):
    """[{path, text, lang, speaker}] real clips, 4-15 s."""
    rows, out = [], DATA / "real"
    out.mkdir(parents=True, exist_ok=True)
    meta = DATA / "real.json"
    if meta.exists():
        return json.loads(meta.read_text(encoding="utf-8"))
    libri = fetch(LIBRI, DATA / "dev-clean.tar.gz")
    trans = {}
    with tarfile.open(libri, "r|gz") as t:  # streamed: a .tar.gz can't seek cheaply
        for m in t:
            if m.name.endswith(".trans.txt"):
                for line in t.extractfile(m).read().decode().splitlines():
                    k, txt = line.split(" ", 1)
                    trans[k] = txt.capitalize()
    keys = sorted(trans)
    random.Random(7).shuffle(keys)
    per_spk, chosen = {}, set()
    for k in keys:
        spk = k.split("-")[0]
        if len(chosen) < n_en and per_spk.get(spk, 0) < n_en // 40 + 1 and 40 < len(trans[k]) < 220:
            chosen.add(k)
            per_spk[spk] = per_spk.get(spk, 0) + 1
    with tarfile.open(libri, "r|gz") as t:
        for m in t:
            k = Path(m.name).stem
            if m.name.endswith(".flac") and k in chosen:
                p = out / f"en_{k}.flac"
                p.write_bytes(t.extractfile(m).read())
                rows.append({"path": str(p), "text": trans[k], "lang": "en", "speaker": "libri-" + k.split("-")[0]})
    tsv = fetch(f"{FLEURS}/dev.tsv", DATA / "fleurs_hi_dev.tsv")
    hi = {r[1]: r for r in list(csv.reader(open(tsv, encoding="utf-8"), delimiter="\t"))[:n_hi]}
    with tarfile.open(fetch(f"{FLEURS}/audio/dev.tar.gz", DATA / "fleurs_hi_dev.tar.gz"), "r|gz") as t:
        for m in t:
            r = hi.get(Path(m.name).name)
            if m.isfile() and r:
                p = out / f"hi_{r[1]}"
                p.write_bytes(t.extractfile(m).read())
                rows.append({"path": str(p), "text": r[2], "lang": "hi", "speaker": "fleurs-" + r[0]})
    meta.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    return rows


async def _edge(text, voice, path):
    import edge_tts
    for attempt in range(4):
        try:
            await edge_tts.Communicate(text, voice).save(str(path))
            return True
        except Exception as e:
            log("edge-tts retry", voice, repr(e)[:80])
            await asyncio.sleep(3 * (attempt + 1))
    return False


def prep_fake(real, per_voice):
    out = DATA / "fake"
    out.mkdir(parents=True, exist_ok=True)
    meta = DATA / "fake.json"
    rows = json.loads(meta.read_text(encoding="utf-8")) if meta.exists() else []
    done = {r["path"] for r in rows}
    rng = random.Random(11)
    for lang, voices in EDGE.items():
        texts = [r["text"] for r in real if r["lang"] == lang]
        for v in voices:
            for j, txt in enumerate(rng.sample(texts, min(per_voice, len(texts)))):
                p = out / f"{v}_{j:03d}.mp3"
                if str(p) not in done and asyncio.run(_edge(txt, v, p)):
                    rows.append({"path": str(p), "text": txt, "lang": lang, "speaker": v, "engine": "edge-neural"})
            log("edge voice done", v)
            meta.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    jobs = []  # Windows desktop TTS: one PowerShell run renders them all
    en_texts = [r["text"] for r in real if r["lang"] == "en"]
    for v in SAPI:
        for j, txt in enumerate(rng.sample(en_texts, min(per_voice, len(en_texts)))):
            p = out / f"sapi_{v.split()[1]}_{j:03d}.wav"
            if str(p) not in done:
                jobs.append({"voice": v, "text": txt, "path": str(p)})
                rows.append({"path": str(p), "text": txt, "lang": "en", "speaker": "sapi-" + v.split()[1], "engine": "windows-sapi"})
    if jobs:
        jf = DATA / "sapi_jobs.json"
        jf.write_text(json.dumps(jobs), encoding="utf-8")
        ps = ("Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
              f"foreach ($j in (Get-Content -Raw -Encoding UTF8 '{jf}' | ConvertFrom-Json)) "
              "{ $s.SelectVoice($j.voice); $s.SetOutputToWaveFile($j.path); $s.Speak($j.text) }; $s.SetOutputToNull()")
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True)
    meta.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    return rows


def coded(path, codec):
    """The clip after MP3 48 kbps (every clip, so codec artefacts don't give fakes away) or Opus 16 kbps (WhatsApp)."""
    from detectors.audio import load_audio
    ext, args = (".mp3", ["-c:a", "libmp3lame", "-b:a", "48k"]) if codec == "mp3" else (".ogg", ["-c:a", "libopus", "-b:a", "16k"])
    tmp = DATA / "tmp" / (Path(path).stem + "_" + codec + ext)
    tmp.parent.mkdir(exist_ok=True)
    src = path
    if codec == "opus":  # Opus goes on top of the shared MP3 step, like a forwarded voice note
        src = DATA / "tmp" / (Path(path).stem + "_mp3.mp3")
        if not src.exists():
            ffmpeg("-i", path, "-ac", "1", "-ar", "16000", "-c:a", "libmp3lame", "-b:a", "48k", src)
    if not tmp.exists():
        ffmpeg("-i", src, "-ac", "1", "-ar", "16000", *args, tmp)
    return load_audio(tmp)


def embed(rows, codec):
    """Per clip: pooled backbone features of its first two non-silent 4 s windows, and the original head's p(fake)."""
    import torch
    from detectors.audio import SILENCE_RMS, device, pella_prep, pellav2, windows
    model, mod = pellav2()
    grab = {}
    h = model.head.register_forward_hook(lambda m, i, o: grab.__setitem__("h", i[0].detach().float().cpu().numpy()))
    feats = []
    try:
        for k, r in enumerate(rows):
            wav = coded(r["path"], codec)
            ws = [w for _, w in windows(wav) if np.sqrt(np.mean(w ** 2)) >= SILENCE_RMS][:2] or [next(windows(wav))[1]]
            x = torch.from_numpy(np.stack([pella_prep(w, mod) for w in ws])).float().to(device())
            with torch.no_grad(), torch.autocast("cuda", dtype=torch.float16, enabled=device() == "cuda"):
                model(x)
            feats.append(grab["h"])
            if k % 100 == 0:
                log(f"embedded {k}/{len(rows)} ({codec})")
    finally:
        h.remove()
    return feats


def fit_head(X, y, w0, b0, l2, steps=300):
    import torch
    X, y = torch.tensor(np.asarray(X, np.float32)), torch.tensor(y, dtype=torch.float32)
    w0, b0 = torch.tensor(w0), torch.tensor(b0)
    w, b = w0.clone().requires_grad_(), b0.clone().requires_grad_()
    opt = torch.optim.LBFGS([w, b], max_iter=steps, line_search_fn="strong_wolfe")

    def closure():
        opt.zero_grad()
        loss = torch.nn.functional.binary_cross_entropy_with_logits(X @ w + b, y) + l2 * ((w - w0) ** 2).sum() / len(y)
        loss.backward()
        return loss
    opt.step(closure)
    return w.detach().numpy(), b.detach().numpy()


def clip_probs(feats, w, b):
    return np.array([float(np.mean(1 / (1 + np.exp(-(f @ w + b))))) for f in feats])


def metrics(y, p):
    from sklearn.metrics import roc_auc_score, roc_curve
    y = np.asarray(y)
    out = {"n": len(y), "recall": float((p[y == 1] >= .5).mean()) if (y == 1).any() else None,
           "FPR": float((p[y == 0] >= .5).mean()) if (y == 0).any() else None, "AUROC": None, "EER": None}
    if len(set(y)) == 2:
        fpr, tpr, _ = roc_curve(y, p)
        out |= {"AUROC": roc_auc_score(y, p), "EER": float(fpr[np.nanargmin(np.abs(fpr - (1 - tpr)))])}
    return out


def train():
    import torch
    real = json.loads((DATA / "real.json").read_text(encoding="utf-8"))
    fake = [r for r in json.loads((DATA / "fake.json").read_text(encoding="utf-8")) if Path(r["path"]).exists()]
    spk = sorted({r["speaker"] for r in real if r["lang"] == "en"})
    random.Random(7).shuffle(spk)
    test_spk = set(spk[:len(spk) * 3 // 10])
    rng = random.Random(3)
    for r in real:
        r["test"] = r["speaker"] in test_spk if r["lang"] == "en" else rng.random() < 0.3
    for r in fake:
        r["test"] = r["speaker"] in TEST_VOICES or r["engine"] == "windows-sapi"
    rows = real + fake
    y = np.array([0] * len(real) + [1] * len(fake))
    test = np.array([r["test"] for r in rows])
    F = {c: embed(rows, c) for c in ("mp3", "opus")}

    model, _ = __import__("detectors.audio", fromlist=["pellav2"]).pellav2()
    w0 = model.head.weight.detach().float().cpu().numpy().reshape(-1)
    b0 = model.head.bias.detach().float().cpu().numpy()
    tr = np.where(~test)[0]
    Xtr = [w for c in F for i in tr for w in F[c][i]]  # both codecs, every window
    ytr = [y[i] for c in F for i in tr for _ in F[c][i]]
    best = None
    val = {r["speaker"] for i in tr for r in [rows[i]]}
    val = set(sorted(val)[::5])  # every fifth training voice/speaker held back to choose the L2 strength
    for l2 in (10.0, 1.0, 0.1):
        fit_idx = [i for i in tr if rows[i]["speaker"] not in val]
        w, b = fit_head([w_ for c in F for i in fit_idx for w_ in F[c][i]], [y[i] for c in F for i in fit_idx for _ in F[c][i]], w0, b0, l2)
        vi = [i for i in tr if rows[i]["speaker"] in val]
        auc = metrics(y[vi], clip_probs([F["opus"][i] for i in vi], w, b))["AUROC"] or 0
        log(f"l2={l2}: validation AUROC {auc:.3f}")
        best = max(best or (-1, l2), (auc, l2))
    w, b = fit_head(Xtr, ytr, w0, b0, best[1])

    te = np.where(test)[0]
    groups = {"all held-out": te,
              "real English (unseen speakers) + Edge neural (unseen voices)": [i for i in te if rows[i].get("engine") != "windows-sapi" and rows[i]["lang"] == "en"],
              "real Hindi + Edge Hindi neural (unseen voice)": [i for i in te if rows[i]["lang"] == "hi"],
              "Windows desktop TTS only (engine never trained on)": [i for i in te if rows[i].get("engine") == "windows-sapi"],
              "real speech only (false alarms)": [i for i in te if y[i] == 0]}
    lines = ["# Cloned-voice detector (pellav2 head): evaluation and adaptation report", "",
             f"Real: {len(real)} clips (LibriSpeech dev-clean English, FLEURS Hindi). Fake: {len(fake)} TTS clips "
             f"(Edge neural en-IN/hi-IN/en-US/en-GB reading the same transcripts; Windows desktop TTS as an unseen engine). "
             f"Held out: {int(test.sum())} clips; unseen voices {sorted(TEST_VOICES)}, 30% of speakers, all Windows TTS. "
             f"Every clip MP3-encoded identically; 'Opus 16k' adds the WhatsApp voice-note codec. Head refit from pellav2's weights, "
             f"L2 = {best[1]} towards them (chosen on held-back training voices). Clip score = mean p(fake) of its first two 4 s windows.", "",
             "| Test group | Codec | Model | n | AUROC | EER | Recall (fakes caught) | False-positive rate |",
             "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    f = lambda v: "n/a" if v is None else f"{v:.3f}"
    for g, idx in groups.items():
        for c in ("mp3", "opus"):
            for name, ww, bb in (("original", w0, b0), ("tuned", w, b)):
                m = metrics(y[idx], clip_probs([F[c][i] for i in idx], ww, bb))
                lines.append(f"| {g} | {'MP3 48k' if c == 'mp3' else 'Opus 16k'} | {name} | {m['n']} | {f(m['AUROC'])} | {f(m['EER'])} | {f(m['recall'])} | {f(m['FPR'])} |")
    lines += ["", "Limits: fakes are text-to-speech, not voice CLONES of a target person; a modern cloning model can be harder. "
              "LibriSpeech is read audiobook English, not phone calls. Small n: a difference of a few points is noise."]
    torch.save({"weight": torch.tensor(w).reshape(1, -1), "bias": torch.tensor(b).reshape(1), "l2": best[1]}, OUT)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines).encode("ascii", "replace").decode())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["prep", "train", "all"], default="all")
    ap.add_argument("--n_en", type=int, default=400)
    ap.add_argument("--n_hi", type=int, default=200)
    ap.add_argument("--per_voice", type=int, default=60)
    a = ap.parse_args()
    if a.stage in ("prep", "all"):
        real = prep_real(a.n_en, a.n_hi)
        log(f"{len(real)} real clips")
        log(f"{len(prep_fake(real, a.per_voice))} fake clips")
    if a.stage in ("train", "all"):
        train()
