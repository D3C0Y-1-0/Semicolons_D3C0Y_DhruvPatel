"""Do voice CLONES of a specific person get past TrustCheck? Run from backend/ after gen_voice_clones.py:
    python train/eval_voice_clones.py
Two questions, each on clean (MP3 48k) and WhatsApp-like (Opus 16k) audio:
  1. pellav2: is the clone flagged as synthetic, and are the real clips of the same speakers left alone?
  2. Voiceprint (ECAPA): does the clone MATCH the real speaker's enrolled voice? If it does, the voiceprint
     alone can't stop it, which is why TrustCheck adds the code word and the out-of-band YES/NO.
Writes eval/voice_clone_report.md.
"""
import json
import os
import sys
from pathlib import Path

import numpy as np

os.environ["USE_TUNED_HEADS"] = "0"
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from train_voice_head import DATA, clip_probs, coded, embed, log, metrics  # noqa: E402

REPORT = HERE.parent.parent / "eval" / "voice_clone_report.md"


def main():
    from detectors import audio, identity
    clones = [r for r in json.loads((DATA / "clones.json").read_text(encoding="utf-8")) if Path(r["path"]).exists()]
    spk = {c["speaker"] for c in clones}
    refs = {c["ref"] for c in clones}
    real = [r for r in json.loads((DATA / "real.json").read_text(encoding="utf-8"))
            if r["speaker"] in spk and r["path"] not in refs]  # the clip used to clone is not scored as "real"
    rows, y = real + clones, np.array([0] * len(real) + [1] * len(clones))
    model, _ = audio.pellav2()
    w = model.head.weight.detach().float().cpu().numpy().reshape(-1)
    b = model.head.bias.detach().float().cpu().numpy()

    lines = ["# Voice clones of specific people: does TrustCheck catch them?", "",
             f"{len(clones)} zero-shot clones (F5-TTS) of {len(spk)} LibriSpeech speakers, each cloned from one of their own clips; "
             f"{len(real)} other real clips of the same speakers. One in three clone lines is a scam line.", "",
             "## 1. Synthetic-voice detector (pellav2)", "",
             "| Codec | n | AUROC | EER | Clones caught | Real clips flagged |", "| --- | --- | --- | --- | --- | --- |"]
    for c in ("mp3", "opus"):
        m = metrics(y, clip_probs(embed(rows, c), w, b))
        lines.append(f"| {'MP3 48k' if c == 'mp3' else 'Opus 16k (WhatsApp)'} | {m['n']} | {m['AUROC']:.3f} | {m['EER']:.3f} | {m['recall']:.3f} | {m['FPR']:.3f} |")

    log("voiceprints")
    enrolled = {}  # each speaker enrolled from the clip the attacker cloned from: the realistic worst case
    for c in clones:
        if c["speaker"] not in enrolled:
            enrolled[c["speaker"]] = audio.voice_embedding(coded(c["ref"], "mp3"))
    sims = {"clone": [], "real": []}
    for r, label in [(r, "real") for r in real] + [(c, "clone") for c in clones]:
        for codec in ("mp3", "opus"):
            sims[label].append(identity.cosine(enrolled[r["speaker"]], audio.voice_embedding(coded(r["path"], codec))))
    th = identity.VOICE_THRESHOLD
    passed = np.mean(np.array(sims["clone"]) >= th)
    lines += ["", "## 2. Voiceprint check (ECAPA, threshold %.2f)" % th, "",
              "| | Median similarity to the enrolled voice | Accepted as the same person |", "| --- | --- | --- |",
              f"| Real clips of the speaker | {np.median(sims['real']):.2f} | {np.mean(np.array(sims['real']) >= th):.0%} |",
              f"| Clones of the speaker | {np.median(sims['clone']):.2f} | {passed:.0%} |", "",
              "A clone that passes the voiceprint still has to say the rotating code word and get past the real person's YES/NO; "
              "neither depends on how good the clone is.", "",
              "Limits: one cloning engine (F5-TTS); read audiobook English, not phone calls; no Hindi clones (the open model is "
              "English/Chinese). Commercial cloning services may score differently."]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines).encode("ascii", "replace").decode())


if __name__ == "__main__":
    main()
