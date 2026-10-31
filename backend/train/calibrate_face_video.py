"""Calibrate GenD's video score so 0.5 means what the app assumes. Run from backend/ after eval_face_video.py:
    python train/calibrate_face_video.py [--n 60]
GenD ranks swaps above real videos well (AUROC 0.97) but its raw score runs high on real faces, and higher still
after WhatsApp-style re-encoding, so real people got flagged. This fits a logistic (Platt) map
p = sigmoid(a * logit(score) + b) on a SEPARATE calibration set (the dataset's train split, both codecs), then
re-scores the held-out test videos already scored by eval_face_video.py. The map goes to
models/gend_calibration.json; detectors/video.py applies it (USE_TUNED_HEADS=0 goes back to raw scores).
"""
import argparse
import json
import math
import os
import random
import sys
from pathlib import Path

import numpy as np

os.environ["USE_TUNED_HEADS"] = "0"  # score with raw GenD
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from eval_face_video import DATA, REPO, REPORT, log, metrics, score, whatsapp  # noqa: E402

OUT = HERE.parent / "models" / "gend_calibration.json"
logit = lambda s: math.log(min(max(s, 1e-4), 1 - 1e-4) / (1 - min(max(s, 1e-4), 1 - 1e-4)))


def main():
    from huggingface_hub import HfApi, hf_hub_download
    from sklearn.linear_model import LogisticRegression
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=60)
    n = ap.parse_args().n
    files = [s.rfilename for s in HfApi().dataset_info(REPO).siblings]
    X, y = [], []
    for label in ("real", "fake"):
        pool = sorted(f for f in files if f.startswith(f"combined_data/train/{label}/") and f.endswith(".mp4"))
        for k, f in enumerate(random.Random(11).sample(pool, n)):
            p = hf_hub_download(REPO, f, repo_type="dataset", local_dir=DATA)
            for v in (p, whatsapp(p)):  # calibrate on both codecs: the app can't know which one it got
                s = score(v)
                if s is not None:
                    X.append([logit(s)])
                    y.append(1 if label == "fake" else 0)
            if k % 20 == 0:
                log(f"calibration {label} {k}/{n}")
    lr = LogisticRegression().fit(X, y)
    a, b = float(lr.coef_[0][0]), float(lr.intercept_[0])
    OUT.write_text(json.dumps({"a": a, "b": b, "fitted_on": f"{REPO} train split, {len(y)} scored videos (both codecs)"}), encoding="utf-8")

    cal = lambda s: 1 / (1 + math.exp(-(a * logit(s) + b)))
    test = json.loads((DATA / "scores.json").read_text(encoding="utf-8"))
    lines = ["", "## After calibration (fitted on separate videos)", "",
             f"Platt map p = sigmoid({a:.2f} * logit(score) {'+' if b >= 0 else '-'} {abs(b):.2f}), fitted on {len(y)} scored videos "
             f"from the dataset's train split (none of the test videos), both codecs. Same {len(test['original'][0])} test videos as above.", "",
             "| Condition | AUROC | Face swaps caught | Real videos flagged |", "| --- | --- | --- | --- |"]
    for cond, (yy, ss) in test.items():
        m = metrics(yy, [cal(s) for s in ss])
        lines.append(f"| {'As downloaded' if cond == 'original' else 'WhatsApp-like (480p, CRF 30)'} | {m['AUROC']:.3f} | {m['recall']:.3f} | {m['FPR']:.3f} |")
    lines.append("")
    lines.append("Calibration moves the cut-off, not the ranking, so AUROC is unchanged. The app uses the calibrated score.")
    with open(REPORT, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines).encode("ascii", "replace").decode())


if __name__ == "__main__":
    main()
