# Face-swapped videos: does GenD catch them?

150 face-swap and 150 real videos from KhunPop/deepfake (MIT; validation split, FaceForensics++-style swaps), scored exactly as the app scores a video (32 frames, mean of the worst third). Threshold 0.5.

| Condition | Videos scored | No face found | AUROC | EER | Face swaps caught | Real videos flagged |
| --- | --- | --- | --- | --- | --- | --- |
| As downloaded | 300 | 0 | 0.973 | 0.073 | 0.973 | 0.400 |
| WhatsApp-like (480p, CRF 30) | 300 | 0 | 0.902 | 0.187 | 0.993 | 0.873 |

Limits: one dataset of lab-made face swaps (FaceForensics++ style); real-time swaps on a live call (Deep-Live-Cam) and newer generators can score lower. Team-filmed, consented swaps are the next test.

## After calibration (fitted on separate videos)

Platt map p = sigmoid(1.45 * logit(score) - 3.49), fitted on 240 scored videos from the dataset's train split (none of the test videos), both codecs. Same 300 test videos as above.

| Condition | AUROC | Face swaps caught | Real videos flagged |
| --- | --- | --- | --- |
| As downloaded | 0.973 | 0.907 | 0.033 |
| WhatsApp-like (480p, CRF 30) | 0.902 | 0.880 | 0.347 |

Calibration moves the cut-off, not the ranking, so AUROC is unchanged. The app uses the calibrated score.
