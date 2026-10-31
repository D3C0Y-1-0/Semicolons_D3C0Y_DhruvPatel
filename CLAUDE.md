# CLAUDE.md: TrustCheck (D3COY hackathon, PS 02)

Read this first. It is the full context for continuing this project in a new Claude session.

## Who and what

- Owner: Dhruv Patel (ItzDhruv), second-year CS at DJSCE, team **Semicolons**. Frontend strength: React + Tailwind. Targets AI/ML internships.
- Event: **D3COY** cybersecurity hackathon. Allocated **PS 02: AI-Based Deepfake-Enabled Social Engineering Detection**.
- GitHub target repo: `https://github.com/D3C0Y-1-0/Semicolons_D3C0Y_DhruvPatel` (private, org-owned; the Claude GitHub app had no access as of 31 Oct 2026, so push from the laptop with git). Work on a branch, e.g. `d3coy-trustcheck`, not main.
- Local folder: `C:\Users\raj naik\OneDrive\Desktop\DECOY HACKATHON`
- **Full project spec (what we are building, current): `docs/PROJECT_SPEC.md`.** Read it before changing features. The original plan doc ("D3COY PS2 — Master Build Plan" in the D3COY Claude project) is older; where they differ, the spec wins (B-Free became UnivFD, MuRIL became our trained TF-IDF classifier, SyncNet became the lip-sync heuristic).

## What PS 02 asks for (and how we answer it)

The PS wants detection of deepfake-*enabled social engineering*, analysing "content AND the context in which it is presented", and verification "before acting". Six objectives: synthetic media detection, suspicious message analysis, multimodal risk, identity/context verification, explainable detection, alerting and reporting. Deliverables: prototype, UI with risk and indicators, demo on authorised samples, docs with methodology, **model limitations** and response workflow.

**Thesis (the pitch line):** "Detectors will lose the arms race. Process won't. We don't only ask *is this fake?*, we ask *should you act on this?*"

```
R = 100 × sigmoid(b + Σ wᵢ · ln(sᵢ/(1−sᵢ))) × Impact,   b = ln(0.05/0.95) = −2.944
```
Then hard policy rules set floors (e.g. payment/credential request from an unregistered channel or to a new beneficiary is never below HIGH = 60). Bands: LOW < 30, MEDIUM 30–59, HIGH ≥ 60.

Worked examples (must stay true; both `backend/fusion.py` and `frontend/src/lib/fusion.js` assert them):
- A, Arup-style fake CFO wire: **99.9 HIGH**
- B, same fake, birthday message (impact 0.2): **9.8 LOW**
- C, perfect fake fools all detectors: maths **17.3**, Rule 1 lifts to **HIGH (60)**

## USPs (keep these visible in UI and pitch)

1. Context beats pixels: impact-aware risk works even when the fake is perfect.
2. Live Call Guard: Chrome extension + web Live page listen to a Meet/Zoom tab during the call.
3. Challenge-response coach: occlusion/deformation prompts (GOTCHA, NYU: hand over face and finger on cheek beat head turns).
4. One-click out-of-band verification: Telegram YES/NO to the real person's enrolled chat; NO holds payment and escalates.
5. Org Trust Graph: enrolled voiceprints, faces, channels, hours, approval limits, usual requests.
6. Bharat-ready: Hindi/Hinglish, digital-arrest mode with the 1930 helpline, CERT-In 6-hour report draft, DPDP-aligned (embeddings only).
7. Campaign clustering: the same cloned voice across cases is linked.

## Repo map

```
backend/
  app.py              FastAPI: /analyze /enroll /people /cases /cases/{id} /verify/{id} /cases/{id}/decision /cases/{id}/report /stats /health, WS /live/{session}
  fusion.py           log-odds fusion + impact + rules (self-check: python fusion.py)
  db.py               SQLite: people (Trust Graph), cases (+ voice_emb, campaign); embeddings never returned to clients
  verify.py           Telegram long-polling bot: /start returns chat id; YES/NO callbacks; citizen mode (forward voice/text, bilingual reply)
  report.py           CERT-In incident draft (Markdown)
  seed.py             demo people: cfo-rajesh (Rajesh Kumar, CFO, limit ₹10 lakh), ceo-ananya, hr-farhan
  setup_models.py     downloads every model and prints PASS/FAIL per model
  detectors/
    audio.py          pellav2 (Sadanie/pellav2-audio-deepfake-detector, MIT, w2v-BERT 2.0 backbone, preprocessing mirrors pellav2_infer.py, revision pinned; 4 s windows, 2 s hop, top-30% mean), ECAPA voiceprint, faster-whisper, waveform peaks
    video.py          InsightFace buffalo_l (detect + ArcFace), GenD (yermandy/GenD_CLIP_L_14, WACV 2026, MIT; vendored in vendor/modeling_gend.py), heuristic lip-sync, face thumbnails
    image.py          C2PA + generator metadata, UnivFD (CVPR 2023; models/univfd_fc.pth + openai/clip-vit-large-patch14), GenD on faces
    message.py        email headers (SPF/DKIM/DMARC, Reply-To, display name), lookalike domains, URLs (blocklist + Safe Browsing), tactic tagging (Claude API if key, else EN/Hinglish/Hindi lexicon), trained classifier, amount/action extraction
    identity.py       Trust Graph context checks, biometric matches, inr() Indian number format
  train/              train_message_clf.py, indic_corpus.py, data/sms_spam_collection.tsv
  models/             message_clf.joblib (trained by us), univfd_fc.pth (UnivFD head, MIT)
frontend/             Vite + React 19 + Tailwind v4 + Framer Motion + Three.js (@react-three/fiber)
  src/landing/        Landing.jsx (hero with 3D spectrogram), MathsLab.jsx (live sliders, JS fusion), PhoneVerify.jsx
  src/app/            AppShell (sidebar), Check, Live, Cases (security queue + stats), People (Trust Graph)
  src/components/     Spectrogram3D.jsx, Verdict.jsx (Stamp, Waterfall, Highlighted, Waveform)
  src/lib/            api.js (VITE_API, default http://localhost:8000), fusion.js, samples.js
extension/            Chrome MV3 Live Call Guard (tabCapture -> offscreen MediaRecorder -> WS /live)
eval/                 run_eval.py (AUROC/EER/FPR, --compress for WhatsApp-like audio, Platt fit), check_gend.py, manifest.example.csv, message_clf_report.md
```

## Status (31 Oct 2026)

Verified in the build sandbox:
- All self-checks pass: `python fusion.py`, `python -m detectors.message`, `python -m detectors.identity`, `python -m detectors.audio`; the JS fusion matches the Python results.
- API end to end on text and .eml, enrolment without media, cases, decision, CERT-In report, stats, campaign clustering.
- Frontend builds; every page screenshotted with live backend results; hero sweep turns the cloned segment red and the HIGH stamp drops.
- Chrome extension loads and its popup reaches the backend.
- Message classifier trained: SMS held-out AUROC 0.995; unseen Indian templates AUROC 0.849, recall 0.80, FPR 0.20.

Verified on the team laptop (RTX 4050 6 GB, i5-13450HX, Python 3.11 venv in `backend/.venv`, torch 2.8.0+cu126), 31 Oct 2026:
- Every model loads and runs on the GPU at once in 5.5 GB: pellav2, GenD and UnivFD (vision tower only) in fp16, ECAPA, faster-whisper large-v3, InsightFace buffalo_l detection + recognition via onnxruntime-gpu 1.23.2 (CUDA 12; 1.24+ on PyPI need CUDA 13). fp16 left every smoke score unchanged.
- Smoke results (not an eval, n=1 each): Windows TTS voice p(fake) 0.999, LibriSpeech human 0.001, both unchanged after Opus 16 kbps; GenD on FF++ sample face-swap 0.967 vs real 0.319, so `GEND_FAKE_INDEX=1` is right.
- `/analyze` with media: TTS "CFO" voice note HIGH 100 with transcript; same voice compressed is linked as one campaign; real speech LOW 0; face-swap video HIGH 100 (GenD 0.979 over 32 frames, lip-sync 0.64); face-swap still with no request LOW + "Synthetic media detected" badge.
- Warm timings: 20 s voice note about 2.5 s, 20 s video call about 4.5 s (was 99 s before the fp16 and GPU-face fixes: VRAM was spilling into system RAM). The first check after a backend start loads models, about a minute.

Pushed to GitHub (branch `d3coy-trustcheck`), 31 Oct 2026:
- Full browser pass: four Check scenarios (CFO wire HIGH 98, digital arrest HIGH with 1930, CEO OTP HIGH, harmless LOW 0), decision buttons, queue, Trust Graph.
- Live call fixed: it used to transcribe 3 s fragments with no context ("45 lakh" heard as "45 lock"), so a cloned CFO stayed LOW 20 live. It now re-transcribes the last 90 s as one piece with an Indian-money prompt: HIGH 99.9 within 13 s, real speech LOW 0, about 1.2 s per update.
- Pitch deck `docs/TrustCheck_pitch.pptx` (11 slides incl. Current progress, speaker notes, only measured numbers) and run-sheet `docs/DEMO.md` (maps slides to the mentoring-round criteria).
- Telegram verified end to end: bot @trustcheck_semicolons_bot (token in backend/.env, never committed); Rajesh Kumar linked to the team phone's chat; a Fake CFO wire sent "Did you send this?", the NO tap turned the case into `confirmed_attack`.

## Run

```powershell
cd backend; .\.venv\Scripts\activate; python seed.py; uvicorn app:app --port 8000
cd frontend; npm install; npm run dev        # landing http://localhost:5173, console /#/app/check
```
Setup details, Windows gotchas (ffmpeg falls back to the imageio-ffmpeg binary, insightface needs MS C++ Build Tools, torch 2.8 CUDA wheel) and the 4-minute demo flow are in README.md. Before the demo, run one voice note and one video through Check once so the models are warm.

## Next steps, in priority order

1. Record consented team voices; clone them (Chatterbox, F5-TTS, XTTS-v2); film Deep-Live-Cam swaps; fill `eval/manifest.csv`; run `python ../eval/run_eval.py ../eval/manifest.csv --compress`; tune VOICE_THRESHOLD, FACE_THRESHOLD and weights; put the real numbers in the deck.
2. Link the other enrolled people (Ananya, Farhan) to their own Telegram chats if they'll be shown live.
3. Once eval numbers exist, replace the left column of deck slide 9 with them; record the backup demo video following `docs/DEMO.md`.
4. Optional: XLS-R + SLS as a second audio model (needs fairseq + torch 1.13, so run it as a separate service), SyncNet in place of the heuristic lip-sync check, Grad-CAM heatmaps.

## Conventions

- Lean code: no new dependencies or abstractions without need; mark deliberate shortcuts with `# ponytail:` comments naming the upgrade path.
- Every detector returns `{signal, label, score 0..1 or None, why, evidence[]}`; a None score means "unavailable" and is ignored by fusion (never penalised).
- If you add a signal, add its weight in BOTH `backend/fusion.py` and `frontend/src/lib/fusion.js`.
- UI design system: night `#0d1730`, paper `#eef3f1`, ink `#14213d`, genuine `#2f8f7a`, caution `#b7791f`, synthetic `#c2341f`, action indigo `#3b4ba8`; Archivo variable (wide for headings, condensed for the stamp). One bold element per screen; no caps eyebrow labels, no card grids, no middle-dot meta strings.
- Privacy: raw uploads are deleted after analysis; only embeddings are stored. The backend has open CORS and no auth (demo laptop only).
- Honesty: never claim accuracy we haven't measured; the limitations section is part of the pitch.
