# TrustCheck — D3COY PS 02: deepfake-enabled social engineering detection

Most deepfake tools only ask "is this fake?". TrustCheck asks "should you act on this?" It scores the media, the wording, who the message claims to come from and what it asks you to do, then makes you verify before any money or data moves.

```
backend/      FastAPI service: detectors, fusion engine, Telegram bot, CERT-In report
frontend/     Landing page (Three.js voice landscape, live maths lab) + console: Check, Live call, Security queue, Trust Graph
extension/    Chrome "Live Call Guard": listens to a Meet/Zoom/Teams tab during the call
eval/         Measure accuracy on your own labelled samples
```

## 1. One-time setup (Windows)

You need Python 3.12 (use Anaconda), Node 18+, ffmpeg and Chrome.

```powershell
# ffmpeg (needed to read any audio or video)
winget install Gyan.FFmpeg

# Python environment
conda create -n trustcheck python=3.12 -y
conda activate trustcheck
cd backend

# PyTorch first. NVIDIA GPU:
pip install torch==2.8.0 torchvision==0.23.0 torchaudio==2.8.0 --index-url https://download.pytorch.org/whl/cu126
# No GPU: pip install torch==2.8.0 torchvision==0.23.0 torchaudio==2.8.0

pip install -r requirements.txt
# faster-whisper and insightface pull in CPU onnxruntime, which shadows the GPU build: remove it, restore the GPU one
pip uninstall -y onnxruntime; pip install --force-reinstall --no-deps onnxruntime-gpu==1.23.2
copy .env.example .env      # then edit .env
```

`insightface` fails to install on Windows unless the **Microsoft C++ Build Tools** are present ("Desktop development with C++" in the Visual Studio Build Tools installer). Install them, reopen the terminal, then run `pip install insightface` again.

No GPU? In `.env` set `WHISPER_SIZE=small` and `VIDEO_FRAMES=8`, and `pip install onnxruntime` in place of `onnxruntime-gpu`.

No `winget`? Skip ffmpeg: the backend falls back to the binary bundled with `imageio-ffmpeg` (in requirements).

On a 6 GB GPU (tested: RTX 4050 laptop) every model fits at once: pellav2, GenD and UnivFD run in fp16, InsightFace runs on CUDA through `onnxruntime-gpu==1.23.2` (newer PyPI builds need CUDA 13, torch here is CUDA 12). Warm timings: a 20 s voice note about 2.5 s, a 20 s video call about 4.5 s. The backend now loads every model in the background at startup (about 1.5 min; the console sidebar shows "Models: warming up… / ready"), so the first check on stage takes about 13 s instead of 1-2 min. `WARMUP=0` skips it for quick restarts while editing code.

## 2. Check that everything works

Run these from `backend/`:

```powershell
python setup_models.py           # downloads every model (~6 GB) and prints PASS/FAIL per model
python fusion.py                 # fusion maths: A=99.9 HIGH, B=9.8 LOW, C=17.3 -> HIGH by rule
python -m detectors.message      # message, header and lookalike checks
python -m detectors.identity     # Trust Graph checks
python -m detectors.audio        # audio windowing maths
python ..\eval\check_gend.py     # downloads GenD and confirms its fake-class index
```

The first audio, video or image check downloads the models: pellav2 (~1.3 GB), GenD CLIP-L/14 (~1.2 GB), ECAPA, Whisper and InsightFace buffalo_l. Do this before the event, on good Wi-Fi.

## 3. Run it

```powershell
# terminal 1
cd backend
python seed.py                   # demo Trust Graph: Rajesh Kumar (CFO), Ananya Iyer (CEO), Farhan Shaikh (HR)
uvicorn app:app --port 8000

# terminal 2
cd frontend
npm install
npm run dev                      # landing: http://localhost:5173  console: http://localhost:5173/#/app/check
```

**Chrome extension.** Open `chrome://extensions`, turn on Developer mode, click "Load unpacked" and choose the `extension` folder. Open the call tab, click the TrustCheck icon, then "Listen to this tab". If the extension fails at the venue, the dashboard's **Live call** page does the same job through tab sharing.

**Out-of-band verification: email and QR (no app, no paid API).**
"Ask the real person" sends a signed link to the person's *registered* number or email from the Trust Graph, never to the number the request came from. They open it on any phone and tap YES or NO.
- No WhatsApp or SMS links on purpose: both depend on the presenting device. "Copy message" pastes into any app.
- Email: sent automatically when `SMTP_USER` / `SMTP_PASS` are in `.env` (a Gmail app password works).
- In the room: the verdict shows a QR code; the real person scans it and answers.
- Code word: on **Trust Graph**, "Send their code-word page" gives each person a page with their 30-second code word (add it to the home screen).
- Phones must reach the backend. College and guest Wi-Fi isolate devices, so use a Cloudflare quick tunnel (free, no account, works on any network including a phone hotspot):
  1. Once: download `cloudflared-windows-amd64.exe` from https://github.com/cloudflare/cloudflared/releases/latest (save as `cloudflared.exe`).
  2. Keep running during the demo: `cloudflared.exe tunnel --url http://127.0.0.1:8000`
  3. Put the printed `https://….trycloudflare.com` in `backend/.env` as `PUBLIC_URL=`. No restart needed; new QR codes use it.
  localhost.run was tried and drops idle tunnels within minutes. Anyone with the address reaches the API while it runs: close it after the demo. If it fails on stage, Telegram YES/NO needs no tunnel.

**Telegram (optional).** Put a @BotFather token in `.env` as `TELEGRAM_BOT_TOKEN`. People who use Telegram send `/start` and paste the chat id into **Trust Graph**; YES/NO and `/code` then work there too. Anyone can forward a voice note or message to the bot and get a verdict back in English and Hindi.

## 4. The model we trained

`python train/train_message_clf.py` retrains in about 20 seconds. Data: the SMS Spam Collection (UCI, CC BY 4.0) plus `train/indic_corpus.py`, a bilingual English/Hinglish/Hindi corpus of Indian scams (CEO fraud, digital arrest, KYC/OTP, customs, task jobs, sextortion and more) with hard-negative genuine messages (real bank OTP notices, salary credits, urgent but legitimate work requests).

| Test set | AUROC | Recall | False-positive rate |
| --- | --- | --- | --- |
| SMS Spam Collection, held-out 20% | 0.995 | 0.973 | 0.005 |
| Indian scams (41 scam and 43 genuine templates incl. links, APKs, OTP takeover), templates never seen in training (5-fold by template) | 0.921 | 0.899 | 0.234 |

The second row is deliberately harsh: whole phrasings are held out. That's why the classifier is one weighted signal (0.4) next to the tactic tagger, not a verdict on its own. Full report: `eval/message_clf_report.md`.

**Whole pipeline on messages nobody trained on.** Three sets of hand-written messages (English, Hinglish, Hindi), each scored before it was used to fix anything: 53/68 scams HIGH (78%; 85% on the latest set), 52/52 genuine messages LOW, no false HIGH. `python ../eval/run_holdout.py ../eval/holdout_messages_v3.csv`; method and limits in `eval/message_holdout_report.md`.

**AI-generated images (UnivFD head, refit by us).** `python train/train_image_head.py` builds 1,000 COCO photos vs 1,000 SD-Turbo images prompted with captions of other COCO photos, both resized and JPEG re-encoded the same way, and refits only the linear head (CLIP stays frozen, weights pulled towards the authors'). On 600 held-out images:

| Head | AUROC | AI images caught | False alarms on real photos | Caught after JPEG 50 (WhatsApp-like) |
| --- | --- | --- | --- | --- |
| Original UnivFD (2023) | 0.713 | 11% | 3% | 12% |
| Refit by us (`models/univfd_fc_tuned.pth`) | 0.989 | 97% | 6% | 90% |

The 2023 head misses today's one-step diffusion images; the refit catches them. Same generator in train and test (held-out prompts), so a new generator family can score lower. `USE_TUNED_HEADS=0` goes back to the original. Report: `eval/image_head_report.md`.

**Cloned voices (pellav2), measured on Indian English and Hindi.** `python train/train_voice_head.py` builds 600 real clips (LibriSpeech, FLEURS Hindi) and 600 TTS fakes (7 Edge neural voices incl. en-IN and hi-IN, plus Windows TTS as an engine never trained on), all MP3-encoded identically, each also through Opus 16 kbps. On 532 held-out clips the original pellav2 caught every fake (99.7% after Opus) with 0 false alarms on 172 real speakers; refitting its head did not help, so the original stays. Report: `eval/voice_head_report.md`.

**Voice clones of a specific person.** `train/gen_voice_clones.py` (F5-TTS, its own venv) clones 40 LibriSpeech speakers from one clip each, 120 clones; `train/eval_voice_clones.py` scores them: pellav2 caught 120/120 (also after WhatsApp Opus), flagging 0.8% of 360 real clips of the same speakers. The voiceprint check accepted 100% of the clones as the real person (clones scored 0.78 similarity, the person's own other clips 0.70): measured proof that biometrics alone can't stop a clone, which is why TrustCheck adds the code word and the real person's YES/NO. Report: `eval/voice_clone_report.md`.

**Face-swapped video (GenD), calibrated by us.** `train/eval_face_video.py` scores 150 face-swap and 150 real videos (KhunPop/deepfake, MIT, FaceForensics++-style) the way the app does. Raw GenD ranked them well (AUROC 0.973) but flagged 40% of real videos, 87% after WhatsApp-style re-encoding. `train/calibrate_face_video.py` fits a Platt map on 240 *other* videos (train split, both codecs), saved as `models/gend_calibration.json` and applied by `detectors/video.py`. On the same test videos: 91% of swaps caught with 3% of real flagged; after re-encoding 88% caught, 35% of real flagged (the open weakness). `USE_TUNED_HEADS=0` restores raw scores. Report: `eval/face_video_report.md`.

## 5. How a verdict is made

```
R = 100 × sigmoid(b + Σ wᵢ · ln(sᵢ / (1 − sᵢ))) × Impact,   b = ln(0.05/0.95)
```

After that, hard policy rules set a minimum. For example, a payment request from an unregistered channel can never score below HIGH. Weights and rules are in `backend/fusion.py`; the full reasoning is in the master plan doc.

| Check | Model | File |
| --- | --- | --- |
| Cloned voice | pellav2 (w2v-BERT 2.0 backbone, MIT) | detectors/audio.py |
| Voiceprint | SpeechBrain ECAPA-TDNN | detectors/audio.py |
| Transcript (Hindi, Hinglish) | faster-whisper | detectors/audio.py |
| Face swap | GenD CLIP-L/14 (WACV 2026, MIT), vendored in `vendor/` | detectors/video.py |
| Lip-sync | Mouth-motion vs speech-energy correlation (SyncNet stand-in) | detectors/video.py |
| Repeat attacker | Campaign clustering by voiceprint across cases | db.py |
| Face match + detection | InsightFace buffalo_l | detectors/video.py |
| AI-generated image | UnivFD (CVPR 2023, MIT): CLIP ViT-L/14 + authors' trained head in `models/univfd_fc.pth` | detectors/image.py |
| Image provenance | C2PA Content Credentials, generator metadata | detectors/image.py |
| Scam-language classifier | Trained by us: char+word TF-IDF, calibrated logistic regression (`models/message_clf.joblib`) | train/train_message_clf.py |
| Manipulation tactics | Claude API, or the offline English/Hindi lexicon | detectors/message.py |
| Header, lookalike domain, URL | stdlib + Safe Browsing | detectors/message.py |
| Scam type (17 patterns: KYC, parcel, challan, lottery, job, investment, loan app, APK, remote access, UPI refund, OTP takeover, sextortion, romance, family emergency, ID harvesting, CEO fraud, digital arrest) | topic + hook regexes, EN/Hinglish | detectors/message.py |
| Link intelligence | short-link expansion (one hop), fake bank/brand domains, .apk, bare IP, punycode, throwaway TLDs, domain age via RDAP | detectors/message.py |
| QR codes in images | OpenCV decoder; "scan to receive money" UPI QRs | app.py |
| Screenshots of chats and SMS | RapidOCR (offline, GPU runtime); the text runs through every message check, photo forensics skipped | app.py |
| Channel, hours, limits, usual requests | Org Trust Graph (SQLite) | detectors/identity.py |

## 6. Not built yet (in priority order)

- **XLS-R + SLS** as a second audio model. It needs fairseq with PyTorch 1.13, so run it as a separate small service. Once it's in, also set the `audio_both_high` fact in `app.py`.
- **SyncNet** to replace the heuristic lip-sync check in `video.py`.
- A transformer (MuRIL) version of the message classifier, if the TF-IDF one's 20% false-positive rate on unseen Indian templates matters in testing.
- Grad-CAM heatmaps on face frames, rPPG pulse check, writing-style match.

## 7. Demo flow (4 minutes)

1. Landing page: let the hero scan run once (the cloned stretch turns red, HIGH stamps down).
2. Scroll to **the maths**, click "A perfect fake": the maths says 17, the policy rule says HIGH.
3. Console, **Check a message**, "Fake CFO wire", claims to be Rajesh Kumar: HIGH, with reasons.
4. Press **Ask the real person on Telegram**; the "CFO" on stage taps NO; the **Security queue** updates live.
5. "Digital arrest (Hinglish)": HIGH, with citizen advice and the 1930 helpline.
6. **Live call** or the Chrome extension on a Meet tab with a consented voice clone.

## 8. Before the demo

- Calibrate: put labelled samples in `eval/manifest.csv` (copy `manifest.example.csv`), run `python ..\eval\run_eval.py ..\eval\manifest.csv --compress`, then tune `VOICE_THRESHOLD`, `FACE_THRESHOLD` and the weights.
- Follow the run-sheet in `docs/DEMO.md` (warm-up, Telegram, fallbacks); the deck is `docs/TrustCheck_pitch.pptx`.
- Record the full demo as a backup video.
- The backend has no login and allows any origin. That's fine on a laptop for the demo; never expose it to the internet as is.

## Team ownership

| Area | Owner |
| --- | --- |
| detectors/audio.py, live WebSocket | Audio ML lead |
| detectors/video.py, image.py | Vision ML lead |
| app.py, fusion.py, message.py, identity.py, verify.py, report.py, eval/ | Backend and fusion lead |
| frontend/, extension/, demo, deck | Dhruv |
