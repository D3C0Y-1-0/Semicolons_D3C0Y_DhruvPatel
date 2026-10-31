# AI-generated image detector (UnivFD head): adaptation report

Real: 1000 COCO val2017 photos. Fake: 1000 SD-Turbo images prompted with captions of other COCO photos. Both classes resized and JPEG re-encoded the same way. Train 1400, held-out test 600 (70/30 by image). CLIP ViT-L/14 frozen; head refit from the authors' weights with L2 = 0.1 towards them (chosen on a train slice).

| Model, test condition | AUROC | EER | Accuracy @0.5 | Recall (fakes caught) | False-positive rate |
| --- | --- | --- | --- | --- | --- |
| original UnivFD head, JPEG 60-95 | 0.713 | 0.350 | 0.540 | 0.110 | 0.030 |
| tuned head, JPEG 60-95 | 0.989 | 0.047 | 0.953 | 0.967 | 0.060 |
| original UnivFD head, JPEG 50, WhatsApp-like | 0.700 | 0.367 | 0.545 | 0.120 | 0.030 |
| tuned head, JPEG 50, WhatsApp-like | 0.981 | 0.070 | 0.918 | 0.897 | 0.060 |

Limits: one generator in training (SD-Turbo) and COCO-style scenes; a new generator family can score lower. Test images come from the same generator as training (held-out prompts), so this measures adaptation, not generalisation to unseen generators. The original head's numbers on the same set are the honest baseline.
