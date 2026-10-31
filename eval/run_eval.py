"""Measure every detector on your own labelled set. Run from the backend folder:
    python ../eval/run_eval.py ../eval/manifest.csv [--compress]

manifest.csv columns: path,label,kind[,text,claimed_person_id,channel]
  label: fake|real (media) or attack|benign (message, scenario)
  kind:  audio | video | image | message | scenario   (scenario = the full pipeline, judged on the band)
--compress also scores a WhatsApp-like copy (Opus 16 kbps) of every audio/video file.
Writes eval/results.csv and prints AUROC, EER and false-positive rate per kind, plus Platt calibration.
"""
import csv
import math
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, ".")
import app  # noqa: E402
from detectors import audio, image, message, video  # noqa: E402

MAIN = {"audio": "audio_spoof", "video": "face_video", "image": "image_synthetic"}


def score(row, path):
    k = row["kind"]
    if k == "audio":
        sigs = audio.analyze(path, want_voiceprint=False, want_transcript=False)["signals"]
    elif k == "video":
        sigs = video.analyze(path)["signals"]
    elif k == "image":
        sigs = image.analyze(path)["signals"]
    elif k == "message":
        text = row.get("text") or (Path(path).read_text(encoding="utf-8") if path else "")
        return message.analyze(text)[0][-1]["score"]
    else:
        r = app.run_analysis(path or None, row.get("text", ""), None, row.get("claimed_person_id") or None, row.get("channel") or None)
        return r["risk"] / 100
    s = [x["score"] for x in sigs if x["signal"] == MAIN[k] and x["score"] is not None]
    return max(s) if s else None


def compress(path):
    out = tempfile.mktemp(suffix=".ogg")
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", path, "-vn", "-ac", "1", "-c:a", "libopus", "-b:a", "16k", out], check=True)
    return out


def metrics(ys, ss):
    from sklearn.metrics import roc_auc_score, roc_curve
    from sklearn.linear_model import LogisticRegression
    auc = roc_auc_score(ys, ss) if len(set(ys)) == 2 else float("nan")
    fpr, tpr, _ = roc_curve(ys, ss)
    eer = min(zip(fpr, tpr), key=lambda p: abs(p[0] - (1 - p[1])))[0]
    neg = [s for y, s in zip(ys, ss) if y == 0]
    fp = sum(s >= 0.5 for s in neg) / max(1, len(neg))
    lr = LogisticRegression().fit([[math.log(max(s, 1e-4) / max(1 - s, 1e-4))] for s in ss], ys)
    return auc, eer, fp, lr.coef_[0][0], lr.intercept_[0]


def main():
    rows = list(csv.DictReader(open(sys.argv[1], encoding="utf-8")))
    do_compress = "--compress" in sys.argv
    out, groups = [], defaultdict(lambda: ([], []))
    for row in rows:
        y = 1 if row["label"] in ("fake", "attack") else 0
        variants = [(row["kind"], row["path"])]
        if do_compress and row["kind"] in ("audio", "video"):
            variants.append((row["kind"] + "+whatsapp", compress(row["path"])))
        for kind, p in variants:
            try:
                s = score(row, p)
            except Exception as e:
                print("skip", p, e)
                continue
            if s is None:
                continue
            out.append({"path": row["path"], "kind": kind, "label": row["label"], "score": round(s, 4)})
            groups[kind][0].append(y)
            groups[kind][1].append(s)
    with open(Path(__file__).parent / "results.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, ["path", "kind", "label", "score"])
        w.writeheader()
        w.writerows(out)
    print(f"{'kind':18} {'n':>4} {'AUROC':>6} {'EER':>6} {'FPR@.5':>7}  Platt a, b")
    for kind, (ys, ss) in sorted(groups.items()):
        auc, eer, fp, a, b = metrics(ys, ss)
        print(f"{kind:18} {len(ys):4} {auc:6.3f} {eer:6.3f} {fp:7.3f}  {a:.2f}, {b:.2f}")
    sc = [r for r in out if r["kind"] == "scenario"]
    if sc:
        att = [r for r in sc if r["label"] == "attack"]
        ben = [r for r in sc if r["label"] == "benign"]
        print(f"scenario HIGH recall on attacks: {sum(r['score'] >= .6 for r in att) / max(1, len(att)):.2%}, "
              f"false HIGH on benign: {sum(r['score'] >= .6 for r in ben) / max(1, len(ben)):.2%}")


if __name__ == "__main__":
    main()
