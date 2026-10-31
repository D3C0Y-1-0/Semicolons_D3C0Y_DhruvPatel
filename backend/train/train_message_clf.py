"""Trains the LLM-independent message classifier (the plan's second opinion next to the tactic tagger).

Data:
  1. SMS Spam Collection (Almeida & Hidalgo, UCI; CC BY 4.0), 5,574 English SMS: spam = attack.
  2. train/indic_corpus.py: Indian social-engineering scams and hard-negative benign messages in
     English, Hinglish and Hindi.

Model: character n-grams (robust to Hinglish spelling and Devanagari) + word n-grams -> logistic
regression, then sigmoid calibration so the output is a usable probability for the fusion engine.

Honest evaluation: the Indic set is split by TEMPLATE (GroupShuffleSplit), so the test set only
contains phrasings the model never saw. Run from backend/:  python train/train_message_clf.py
Writes models/message_clf.joblib and eval/message_clf_report.md."""
import csv
import sys
from pathlib import Path

import joblib
import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import GroupKFold, train_test_split
from sklearn.pipeline import FeatureUnion, make_pipeline

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from indic_corpus import build  # noqa: E402

OUT = HERE.parent / "models" / "message_clf.joblib"
REPORT = HERE.parent.parent / "eval" / "message_clf_report.md"


def make_model():
    feats = FeatureUnion([
        ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=2, sublinear_tf=True, max_features=120_000)),
        ("word", TfidfVectorizer(analyzer="word", ngram_range=(1, 2), min_df=2, sublinear_tf=True, token_pattern=r"(?u)\b\w+\b")),
    ])
    lr = LogisticRegression(C=6, class_weight="balanced", max_iter=3000)
    return make_pipeline(feats, CalibratedClassifierCV(lr, method="sigmoid", cv=5))


def metrics(y, p):
    yhat = (p >= 0.5).astype(int)
    return {"n": len(y), "AUROC": roc_auc_score(y, p), "AP": average_precision_score(y, p),
            "precision": precision_score(y, yhat, zero_division=0), "recall": recall_score(y, yhat),
            "F1": f1_score(y, yhat), "FPR": float(((yhat == 1) & (y == 0)).sum() / max(1, (y == 0).sum()))}


def weights(n_sms, groups):
    """Every Indic template counts the same, however many slot fills it produced: a one-line genuine template
    (an app-update notice) otherwise drowns under scam templates with forty fills each."""
    counts = {g: (groups == g).sum() for g in set(groups)}
    return np.concatenate([np.ones(n_sms), [np.sqrt(40 / counts[g]) for g in groups]])


def load_sms():
    rows = list(csv.reader(open(HERE / "data" / "sms_spam_collection.tsv", encoding="utf-8"), delimiter="\t"))
    return [r[1] for r in rows], np.array([1 if r[0] == "spam" else 0 for r in rows])


def main():
    sms_x, sms_y = load_sms()
    sx_tr, sx_te, sy_tr, sy_te = train_test_split(sms_x, sms_y, test_size=0.2, stratify=sms_y, random_state=7)

    indic = build()
    ix, iy, ig = [r[0] for r in indic], np.array([r[1] for r in indic]), np.array([r[2] for r in indic])
    # out-of-fold: every Indic template is predicted by a model that never saw it
    oof, sms_p = np.zeros(len(ix)), []
    for tr, te in GroupKFold(n_splits=5).split(ix, iy, ig):
        m = make_model().fit(sx_tr + [ix[i] for i in tr], np.concatenate([sy_tr, iy[tr]]),
                             calibratedclassifiercv__sample_weight=weights(len(sx_tr), ig[tr]))
        oof[te] = m.predict_proba([ix[i] for i in te])[:, 1]
        sms_p.append(m.predict_proba(sx_te)[:, 1])
    res = {"SMS Spam Collection (held-out 20%)": metrics(sy_te, np.mean(sms_p, axis=0)),
           "Indian scams, unseen templates (5-fold by template)": metrics(iy, oof)}
    by_t = {}
    for g, y, p in zip(ig, iy, oof):
        by_t.setdefault(g, []).append(int((p >= .5) == y))
    worst = sorted(by_t.items(), key=lambda kv: np.mean(kv[1]))[:6]

    # final model on everything for deployment
    final = make_model().fit(sms_x + ix, np.concatenate([sms_y, iy]), calibratedclassifiercv__sample_weight=weights(len(sms_x), ig))
    OUT.parent.mkdir(exist_ok=True)
    joblib.dump(final, OUT)

    demo = ["Hi Priya, Rajesh here (CFO). Urgent and confidential: transfer ₹45,00,000 to our new vendor account in 30 minutes.",
            "Main CBI officer bol raha hoon. Video call pe raho, turant 2 lakh UPI karo.",
            "Hi team, the quarterly review moves to Thursday 3 pm. Thanks, Rajesh",
            "482913 is your OTP for Rs 499 at Swiggy. Do not share this OTP with anyone. - HDFC Bank"]
    dp = final.predict_proba(demo)[:, 1]

    lines = ["# Message classifier: training report", "",
             f"Training rows: {len(sms_x) + len(ix)} ({int(sms_y.sum() + iy.sum())} attacks). Model: char 2-5 + word 1-2 TF-IDF, calibrated logistic regression.", "",
             "| Test set | n | AUROC | Avg precision | Precision | Recall | F1 | False-positive rate |", "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for k, m in res.items():
        lines.append(f"| {k} | {m['n']} | {m['AUROC']:.3f} | {m['AP']:.3f} | {m['precision']:.3f} | {m['recall']:.3f} | {m['F1']:.3f} | {m['FPR']:.3f} |")
    lines += ["", "Hardest unseen templates (share classified correctly): " + ", ".join(f"{g} {np.mean(v):.0%}" for g, v in worst), "",
              "Spot checks with the final model:", ""] + [f"- {p:.2f}: {t}" for t, p in zip(demo, dp)] + [
              "", "Limits: the Indic set is synthetic and template-based, so real-world recall will be lower than the unseen-template score.",
              "The classifier is one weighted signal (0.4) in the fusion engine, never the decision on its own."]
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines).encode("ascii", "replace").decode())  # the Windows console can't print the rupee sign


if __name__ == "__main__":
    main()
