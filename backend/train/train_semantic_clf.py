"""A scam classifier that reads MEANING, not spelling: multilingual sentence embeddings + logistic regression.

The TF-IDF classifier (train_message_clf.py) matches character and word patterns, so "be our online staff, earn per day"
looks new to it even though it means "part-time job, daily income". A multilingual paraphrase encoder maps both close
together, in English, Hindi and Hinglish.

Encoder: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 (Apache-2.0, ~470 MB), run through the installed
`transformers` (mean pooling, no extra package). Data: SMS Spam Collection + train/indic_corpus.py.
Honest test: the three hand-written held-out sets in eval/ (68 scams, 52 genuine) are NEVER used for training; the
report compares this model, the TF-IDF model and their average on them.
Run from backend/: python train/train_semantic_clf.py   ->  models/message_semantic.joblib, eval/semantic_clf_report.md
"""
import csv
import functools
import os
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
from indic_corpus import build  # noqa: E402

ENCODER = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
OUT = HERE.parent / "models" / "message_semantic.joblib"
REPORT = HERE.parent.parent / "eval" / "semantic_clf_report.md"
HOLDOUTS = [HERE.parent.parent / "eval" / f"holdout_messages{s}.csv" for s in ("", "_v2", "_v3")]


@functools.cache
def encoder(device=None):
    import torch
    from transformers import AutoModel, AutoTokenizer
    dev = device or ("cuda" if torch.cuda.is_available() else "cpu")
    tok = AutoTokenizer.from_pretrained(ENCODER)
    model = AutoModel.from_pretrained(ENCODER).to(dev).eval()
    return tok, (model.half() if dev == "cuda" else model), dev


def embed(texts, device=None, batch=64):
    """Mean-pooled, L2-normalised sentence embeddings (the encoder's own pooling)."""
    import torch
    tok, model, dev = encoder(device)
    out = []
    for i in range(0, len(texts), batch):
        enc = tok([t[:1000] for t in texts[i:i + batch]], padding=True, truncation=True, max_length=256, return_tensors="pt").to(dev)
        with torch.no_grad():
            h = model(**enc).last_hidden_state.float()
        m = enc["attention_mask"].unsqueeze(-1).float()
        v = (h * m).sum(1) / m.sum(1).clamp(min=1)
        out.append(torch.nn.functional.normalize(v, dim=1).cpu().numpy())
    return np.concatenate(out)


def load_holdouts():
    rows = [r for p in HOLDOUTS for r in csv.DictReader(open(p, encoding="utf-8"))]
    return [r["text"] for r in rows], np.array([1 if r["label"] == "attack" else 0 for r in rows])


def metrics(y, p):
    from sklearn.metrics import roc_auc_score
    yhat = p >= 0.5
    return {"AUROC": roc_auc_score(y, p), "recall": float(yhat[y == 1].mean()), "FPR": float(yhat[y == 0].mean())}


def main():
    import joblib
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import GroupKFold
    device = os.getenv("EMBED_DEVICE", "cpu")  # the running backend may hold the GPU; CPU is fine for a few thousand texts
    sms = list(csv.reader(open(HERE / "data" / "sms_spam_collection.tsv", encoding="utf-8"), delimiter="\t"))
    indic = build()
    X_txt = [r[1] for r in sms] + [r[0] for r in indic]
    y = np.array([1 if r[0] == "spam" else 0 for r in sms] + [r[1] for r in indic])
    groups = np.array(["sms"] * len(sms) + [r[2] for r in indic])
    print(f"embedding {len(X_txt)} training texts on {device}...", flush=True)
    X = embed(X_txt, device)
    w = np.ones(len(y))
    is_indic = np.arange(len(y)) >= len(sms)
    w[is_indic] = 2.0  # the Indian scams are what this product is for
    lr = lambda: LogisticRegression(C=4, class_weight="balanced", max_iter=4000)

    # unseen Indian templates, 5-fold by template (same protocol as the TF-IDF report)
    ig = groups[is_indic]
    idx = np.where(is_indic)[0]
    oof = np.zeros(len(idx))
    for tr, te in GroupKFold(n_splits=5).split(idx, y[idx], ig):
        train = np.concatenate([np.where(~is_indic)[0], idx[tr]])
        m = lr().fit(X[train], y[train], sample_weight=w[train])
        oof[te] = m.predict_proba(X[idx[te]])[:, 1]
    unseen = metrics(y[idx], oof)

    final = lr().fit(X, y, sample_weight=w)
    joblib.dump({"encoder": ENCODER, "clf": final}, OUT)

    # the honest test: hand-written messages never used for training
    h_txt, h_y = load_holdouts()
    sem = final.predict_proba(embed(h_txt, device))[:, 1]
    tfidf = joblib.load(HERE.parent / "models" / "message_clf.joblib").predict_proba(h_txt)[:, 1]
    rows = {"TF-IDF classifier (current)": tfidf, "Semantic classifier (new)": sem, "Average of both": (tfidf + sem) / 2}
    lines = ["# Semantic scam classifier: report", "",
             f"Encoder {ENCODER} (frozen), logistic regression on {len(y)} texts (SMS Spam Collection + Indian corpus).", "",
             f"Unseen Indian templates (5-fold by template): AUROC {unseen['AUROC']:.3f}, recall {unseen['recall']:.3f}, FPR {unseen['FPR']:.3f}.", "",
             f"Held-out hand-written messages ({int(h_y.sum())} scams, {int((h_y == 0).sum())} genuine; never used for training):", "",
             "| Model | AUROC | Scams caught (p >= 0.5) | Genuine flagged |", "| --- | --- | --- | --- |"]
    for k, p in rows.items():
        m = metrics(h_y, p)
        lines.append(f"| {k} | {m['AUROC']:.3f} | {m['recall']:.3f} | {m['FPR']:.3f} |")
    lines += ["", "These are classifier scores alone, before the scam patterns, link checks and policy rules."]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines).encode("ascii", "replace").decode())


if __name__ == "__main__":
    main()
