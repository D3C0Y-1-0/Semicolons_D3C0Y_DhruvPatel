# Voice clones of specific people: does TrustCheck catch them?

120 zero-shot clones (F5-TTS) of 40 LibriSpeech speakers, each cloned from one of their own clips; 360 other real clips of the same speakers. One in three clone lines is a scam line.

## 1. Synthetic-voice detector (pellav2)

| Codec | n | AUROC | EER | Clones caught | Real clips flagged |
| --- | --- | --- | --- | --- | --- |
| MP3 48k | 480 | 1.000 | 0.000 | 1.000 | 0.003 |
| Opus 16k (WhatsApp) | 480 | 1.000 | 0.000 | 1.000 | 0.008 |

## 2. Voiceprint check (ECAPA, threshold 0.40)

| | Median similarity to the enrolled voice | Accepted as the same person |
| --- | --- | --- |
| Real clips of the speaker | 0.70 | 98% |
| Clones of the speaker | 0.78 | 100% |

A clone that passes the voiceprint still has to say the rotating code word and get past the real person's YES/NO; neither depends on how good the clone is.

Limits: one cloning engine (F5-TTS); read audiobook English, not phone calls; no Hindi clones (the open model is English/Chinese). Commercial cloning services may score differently.
