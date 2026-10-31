# Semantic scam classifier: report

Encoder sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 (frozen), logistic regression on 7059 texts (SMS Spam Collection + Indian corpus).

Unseen Indian templates (5-fold by template): AUROC 0.891, recall 0.862, FPR 0.266.

Held-out hand-written messages (68 scams, 52 genuine; never used for training):

| Model | AUROC | Scams caught (p >= 0.5) | Genuine flagged |
| --- | --- | --- | --- |
| TF-IDF classifier (current) | 0.884 | 0.956 | 0.269 |
| Semantic classifier (new) | 0.904 | 0.882 | 0.212 |
| Average of both | 0.924 | 0.985 | 0.192 |

These are classifier scores alone, before the scam patterns, link checks and policy rules.
