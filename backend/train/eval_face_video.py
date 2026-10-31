"""How well does the face-swap detector (GenD) catch face-swapped VIDEOS? Run from backend/:
    python train/eval_face_video.py [--n 150]
Data: KhunPop/deepfake on Hugging Face (MIT, not gated), validation split; its fakes follow the FaceForensics++
face-swap naming (target_source.mp4). n real + n fake videos are downloaded (about 2 MB each) and scored exactly
as the app scores a video (detectors/video.analyze), once as downloaded and once after a WhatsApp-like re-encode
(480p, H.264 CRF 30). Nothing is trained here: this measures the shipped model.
Writes eval/face_video_report.md.
ponytail: one source of face swaps; FF++-style lab videos are easier than live Deep-Live-Cam calls, so team-filmed
swaps through eval/run_eval.py are still the honest next step.
"""
import argparse
import json
import random
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
DATA = HERE / "data" / "big" / "video"
REPO = "KhunPop/deepfake"
REPORT = HERE.parent.parent / "eval" / "face_video_report.md"


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def fetch(n):
    from huggingface_hub import HfApi, hf_hub_download
    files = [s.rfilename for s in HfApi().dataset_info(REPO).siblings]
    pick = {}
    for label in ("real", "fake"):
        pool = sorted(f for f in files if f.startswith(f"combined_data/val/{label}/") and f.endswith(".mp4"))
        pick[label] = random.Random(7).sample(pool, min(n, len(pool)))
    out = []
    for label, fs in pick.items():
        for f in fs:
            out.append((hf_hub_download(REPO, f, repo_type="dataset", local_dir=DATA), 1 if label == "fake" else 0))
    return out


def whatsapp(path):
    from detectors.audio import ffmpeg_exe
    out = Path(path).with_name(Path(path).stem + "_wa.mp4")
    if not out.exists():
        subprocess.run([ffmpeg_exe(), "-nostdin", "-v", "error", "-y", "-i", path, "-vf", "scale=-2:480",
                        "-c:v", "libx264", "-crf", "30", "-preset", "veryfast", "-an", str(out)], check=True)
    return str(out)


def score(path):
    from detectors import video
    r = video.analyze(path)
    s = [x["score"] for x in r["signals"] if x["signal"] == "face_video" and x["score"] is not None]
    return s[0] if s else None


def metrics(y, p):
    from sklearn.metrics import roc_auc_score, roc_curve
    y, p = np.asarray(y), np.asarray(p)
    fpr, tpr, _ = roc_curve(y, p)
    return {"n": len(y), "AUROC": roc_auc_score(y, p), "EER": float(fpr[np.nanargmin(np.abs(fpr - (1 - tpr)))]),
            "recall": float((p[y == 1] >= .5).mean()), "FPR": float((p[y == 0] >= .5).mean())}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=150)
    vids = fetch(ap.parse_args().n)
    log(f"{len(vids)} videos ready")
    res, skipped = {"original": ([], []), "whatsapp": ([], [])}, {"original": 0, "whatsapp": 0}
    for k, (path, y) in enumerate(vids):
        for cond in res:
            s = score(path if cond == "original" else whatsapp(path))
            if s is None:  # no face found: the app reports "unavailable", it doesn't guess
                skipped[cond] += 1
                continue
            res[cond][0].append(y)
            res[cond][1].append(s)
        if k % 25 == 0:
            log(f"scored {k}/{len(vids)}")
    real, fake = sum(1 for _, y in vids if y == 0), sum(1 for _, y in vids if y == 1)
    lines = ["# Face-swapped videos: does GenD catch them?", "",
             f"{fake} face-swap and {real} real videos from {REPO} (MIT; validation split, FaceForensics++-style swaps), "
             "scored exactly as the app scores a video (32 frames, mean of the worst third). Threshold 0.5.", "",
             "| Condition | Videos scored | No face found | AUROC | EER | Face swaps caught | Real videos flagged |",
             "| --- | --- | --- | --- | --- | --- | --- |"]
    for cond, (y, p) in res.items():
        m = metrics(y, p)
        lines.append(f"| {'As downloaded' if cond == 'original' else 'WhatsApp-like (480p, CRF 30)'} | {m['n']} | {skipped[cond]} | "
                     f"{m['AUROC']:.3f} | {m['EER']:.3f} | {m['recall']:.3f} | {m['FPR']:.3f} |")
    lines += ["", "Limits: one dataset of lab-made face swaps (FaceForensics++ style); real-time swaps on a live call "
              "(Deep-Live-Cam) and newer generators can score lower. Team-filmed, consented swaps are the next test."]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    (DATA / "scores.json").write_text(json.dumps(res), encoding="utf-8")
    print("\n".join(lines).encode("ascii", "replace").decode())


if __name__ == "__main__":
    main()
