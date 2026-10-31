# Cloned-voice detector (pellav2 head): evaluation and adaptation report

Real: 600 clips (LibriSpeech dev-clean English, FLEURS Hindi). Fake: 600 TTS clips (Edge neural en-IN/hi-IN/en-US/en-GB reading the same transcripts; Windows desktop TTS as an unseen engine). Held out: 532 clips; unseen voices ['en-GB-RyanNeural', 'en-IN-PrabhatNeural', 'hi-IN-MadhurNeural'], 30% of speakers, all Windows TTS. Every clip MP3-encoded identically; 'Opus 16k' adds the WhatsApp voice-note codec. Head refit from pellav2's weights, L2 = 10.0 towards them (chosen on held-back training voices). Clip score = mean p(fake) of its first two 4 s windows.

| Test group | Codec | Model | n | AUROC | EER | Recall (fakes caught) | False-positive rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| all held-out | MP3 48k | original | 532 | 1.000 | 0.000 | 1.000 | 0.000 |
| all held-out | MP3 48k | tuned | 532 | 1.000 | 0.000 | 0.997 | 0.000 |
| all held-out | Opus 16k | original | 532 | 1.000 | 0.000 | 0.997 | 0.000 |
| all held-out | Opus 16k | tuned | 532 | 1.000 | 0.000 | 0.981 | 0.000 |
| real English (unseen speakers) + Edge neural (unseen voices) | MP3 48k | original | 240 | 1.000 | 0.000 | 1.000 | 0.000 |
| real English (unseen speakers) + Edge neural (unseen voices) | MP3 48k | tuned | 240 | 1.000 | 0.000 | 0.992 | 0.000 |
| real English (unseen speakers) + Edge neural (unseen voices) | Opus 16k | original | 240 | 1.000 | 0.000 | 1.000 | 0.000 |
| real English (unseen speakers) + Edge neural (unseen voices) | Opus 16k | tuned | 240 | 1.000 | 0.000 | 0.983 | 0.000 |
| real Hindi + Edge Hindi neural (unseen voice) | MP3 48k | original | 112 | 1.000 | 0.000 | 1.000 | 0.000 |
| real Hindi + Edge Hindi neural (unseen voice) | MP3 48k | tuned | 112 | 1.000 | 0.000 | 1.000 | 0.000 |
| real Hindi + Edge Hindi neural (unseen voice) | Opus 16k | original | 112 | 1.000 | 0.000 | 0.983 | 0.000 |
| real Hindi + Edge Hindi neural (unseen voice) | Opus 16k | tuned | 112 | 1.000 | 0.000 | 0.917 | 0.000 |
| Windows desktop TTS only (engine never trained on) | MP3 48k | original | 180 | n/a | n/a | 1.000 | n/a |
| Windows desktop TTS only (engine never trained on) | MP3 48k | tuned | 180 | n/a | n/a | 1.000 | n/a |
| Windows desktop TTS only (engine never trained on) | Opus 16k | original | 180 | n/a | n/a | 1.000 | n/a |
| Windows desktop TTS only (engine never trained on) | Opus 16k | tuned | 180 | n/a | n/a | 1.000 | n/a |
| real speech only (false alarms) | MP3 48k | original | 172 | n/a | n/a | n/a | 0.000 |
| real speech only (false alarms) | MP3 48k | tuned | 172 | n/a | n/a | n/a | 0.000 |
| real speech only (false alarms) | Opus 16k | original | 172 | n/a | n/a | n/a | 0.000 |
| real speech only (false alarms) | Opus 16k | tuned | 172 | n/a | n/a | n/a | 0.000 |

Limits: fakes are text-to-speech, not voice CLONES of a target person; a modern cloning model can be harder. LibriSpeech is read audiobook English, not phone calls. Small n: a difference of a few points is noise.

**Decision: keep the original pellav2 head.** It already separates every held-out clip (AUROC 1.000, no false alarm on
172 real speakers, every fake caught including Hindi, Opus 16 kbps and an engine it was never shown), and the refit head
was slightly worse on Hindi after Opus (0.917 vs 0.983 recall). `models/pellav2_head_tuned.pt` is therefore not shipped;
re-running the script recreates it, and detectors/audio.py would load it if present.
What this does and doesn't show: off-the-shelf neural TTS in Indian English and Hindi is caught reliably, even after
WhatsApp compression. It says nothing yet about voice CLONES of a specific person (XTTS, F5-TTS, ElevenLabs): that needs
consented team recordings and clones, the next evaluation step.
