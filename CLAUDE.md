# CLAUDE.md: TrustCheck (D3COY hackathon, PS 02)

Read this first. It is the full context for continuing this project in a new Claude session. Last updated 31 Oct 2026, evening, after the mentoring-round prep.

## Who and what

- Owner: Dhruv Patel (ItzDhruv), second-year CS at DJSCE, team **Semicolons**. The laptop and its git identity belong to teammate Raj Naik. Frontend strength: React + Tailwind. Targets AI/ML internships.
- Event: **D3COY** cybersecurity hackathon. Allocated **PS 02: AI-Based Deepfake-Enabled Social Engineering Detection**. Mentoring round criteria (equal weight): problem understanding, proposed approach, technical feasibility, innovation and creativity, current progress.
- GitHub: `https://github.com/D3C0Y-1-0/Semicolons_D3C0Y_DhruvPatel` (private, org-owned), branch **`d3coy-trustcheck`** (the only branch; no `main` on the remote). Push from this laptop with git; the `origin` remote is set and the laptop's account has access.
- Local folder: `C:\Users\raj naik\OneDrive\Desktop\DECOY HACKATHON`
- **Full project spec: `docs/PROJECT_SPEC.md`.** Read it before changing features. Where it and older plan docs differ, the spec wins (B-Free became UnivFD, MuRIL became our trained TF-IDF classifier, SyncNet became the lip-sync heuristic). Features added after the spec (Decoy Mode, mule blocklist, Human 2FA, cooling-off lock, amount-scaled floor) are described here.

## What PS 02 asks for (and how we answer it)

The PS wants detection of deepfake-*enabled social engineering*, analysing "content AND the context in which it is presented", and verification "before acting". Six objectives: synthetic media detection, suspicious message analysis, multimodal risk, identity/context verification, explainable detection, alerting and reporting. Deliverables: prototype, UI with risk and indicators, demo on authorised samples, docs with methodology, **model limitations** and response workflow.

**Thesis (the pitch line):** "Detectors will lose the arms race. Process won't. We don't only ask *is this fake?*, we ask *should you act on this?*" Second line, for the new features: "Every other tool defends. We turn the scam into evidence against the scammer."

```
R = 100 × sigmoid(b + Σ wᵢ · ln(sᵢ/(1−sᵢ))) × Impact,   b = ln(0.05/0.95) = −2.944
```
Impact: 1.0 large payment / over approval limit / new account / gift cards / crypto; 0.8 credentials, OTP, remote access; 0.7 routine payment; 0.4 share documents; 0.2 no action.
Then hard policy rules set floors (payment/credential request from an unregistered channel or to a new beneficiary, known mule account, digital-arrest pattern, bad URL: never below HIGH = 60). The HIGH floor grows with the money at stake (`money_floor` / `moneyFloor`): 60 up to ₹10,000, 75 at ₹1 lakh, 90 from ₹10 lakh. Bands: LOW < 30, MEDIUM 30–59, HIGH ≥ 60.

Worked examples (must stay true; both `backend/fusion.py` and `frontend/src/lib/fusion.js` assert them, plus the money-floor values 60/75/90/90):
- A, Arup-style fake CFO wire: **99.9 HIGH**
- B, same fake, birthday message (impact 0.2): **9.8 LOW**
- C, perfect fake fools all detectors: maths **17.3**, Rule 1 lifts to **HIGH (60)**

## USPs (keep these visible in UI and pitch)

Headline four ("we fight back"), all built and tested 31 Oct:
1. **Decoy Mode**: on a HIGH case, scripted replies play a confused victim ("what exact name should I write as the beneficiary?") so the scammer reveals bank account, IFSC, UPI id, phone. English or Hinglish (auto-detected). Every scammer reply is mined. `backend/mules.py` `decoy_turn`, `POST /cases/{id}/decoy` (form `scammer`), state stored in `result.decoy`. UI: `DecoyPanel` in `frontend/src/components/Defense.jsx`.
2. **Mule blocklist**: identifiers from decoys and confirmed attacks (Telegram NO or the manual "It wasn't them") go in SQLite table `mules`. Any later message (or live-call transcript) naming one gets signal `known_mule` (weight 1.5) and a HIGH floor. `GET /mules`; UI `MuleList` on the Security queue. Extraction regexes in `mules.extract` (enrolled people's own phones are excluded).
3. **Human 2FA code word**: two words that change every 30 s per person, HMAC of a per-person `code_secret` (column on `people`, never sent to the browser). The real person reads it on their personal page `/me/{id}?t=…` (sent once from Trust Graph by WhatsApp/SMS/email, or QR) or with `/code` on Telegram; the employee types what the caller said into `POST /people/{id}/code` (accepts the current and previous window). `backend/codeword.py`; UI `CodeWordCheck` on the verdict and Live call pages.
4. **Cooling-off lock**: HIGH payment/credential cases get `result.hold_until` = now + `HOLD_MINUTES` (30). UI `HoldLock` shows a countdown; "Released" on YES, "Payment blocked" on NO.

Foundation:
5. Context beats pixels: impact-aware risk works even when the fake is perfect; floor scales with the amount.
6. Out-of-band verification over what everyone has (mentor feedback 31 Oct: employees don't use Telegram): `backend/notify.py` sends a signed link (`/v/{case}?t=HMAC(code_secret)`) to the REGISTERED phone/email: email automatic with SMTP_USER/SMTP_PASS, WhatsApp/SMS as one-tap `wa.me`/`sms:` links, QR on screen; Telegram optional. YES/NO from any channel goes through `notify.record_answer` (first answer wins). NO = confirmed attack, CERT-In draft, identifiers to the blocklist. Phones need the backend on `--host 0.0.0.0` (or PUBLIC_URL tunnel).
11. Every scam type, not only money (mentor feedback 31 Oct): 17 topic+hook scam patterns in `message.SCAM_TYPES`, link intelligence (`message.link_risk`: one-hop short-link expansion, fake bank/brand domain, .apk, IP, punycode, throwaway TLD, RDAP domain age), QR decoding in images (`app.qr_codes`), new actions with impacts install_app 0.9, click_link 0.7, personal_info 0.6, call_back 0.5, new signals `link_risk` (1.0) and `scam_pattern` (0.8), new rules: dangerous link -> HIGH, scam pattern backed by classifier/link/2 tactics (`scam_strong`) -> HIGH (money floor), pattern alone -> MEDIUM. Verdict shows "Looks like: …", per-type advice, "Warn family on WhatsApp" and read-aloud; Security queue shows money held and scam types caught.
7. Live Call Guard: web Live page + Chrome extension listen to a Meet/Zoom tab; challenge prompts (GOTCHA, NYU: hand over face, finger on cheek).
8. Org Trust Graph: channels, hours, approval limits, usual requests, voiceprint, face.
9. Bharat-ready: Hindi/Hinglish, digital-arrest mode with 1930, CERT-In 6-hour draft (now lists every identifier), DPDP-aligned (embeddings only).
10. Campaign clustering: the same cloned voice across cases is linked.

## Repo map

```
backend/
  app.py              FastAPI: /analyze /enroll /people /people/{id}/code /cases /cases/{id} /verify/{id} /cases/{id}/decision
                      /cases/{id}/decoy /cases/{id}/report /mules /stats /health, WS /live/{session}
  fusion.py           log-odds fusion + impact + rules + money_floor (self-check: python fusion.py)
  db.py               SQLite (trustcheck.db, gitignored): people (+ code_secret), cases, mules; embeddings/secrets never returned
  mules.py            identifier extraction, mule signals, Decoy Mode (self-check: python mules.py)
  codeword.py         Human 2FA code words (self-check: python codeword.py)
  notify.py           out-of-band verification links (WhatsApp/SMS/email/QR), /v and /me phone pages, record_answer (self-check: python notify.py)
  verify.py           Telegram long-polling bot (optional): /start (chat id), /code, YES/NO callbacks, citizen mode; logs every update
  report.py           CERT-In incident draft (Markdown), includes attacker identifiers
  seed.py             demo people: cfo-rajesh (limit ₹10 lakh), ceo-ananya, hr-farhan
  setup_models.py     downloads every model and prints PASS/FAIL per model
  detectors/
    audio.py          pellav2 voice-clone detector, ECAPA voiceprint, faster-whisper (Indian-money initial prompt), waveform peaks
    video.py          InsightFace buffalo_l, GenD face-swap detector (vendor/modeling_gend.py), heuristic lip-sync
    image.py          C2PA + metadata, UnivFD, GenD on faces
    message.py        headers, lookalike domains, URLs, tactics (Claude API if key, else EN/Hinglish/Hindi lexicon), trained classifier,
                      amount/action extraction (handles "10000 rs", "10k", "25,000/-", bare "need 5000 urgently", "send me", "gpay kar do")
    identity.py       Trust Graph context checks, biometric matches, inr()
  train/, models/     message_clf.joblib (trained by us), univfd_fc.pth
frontend/             Vite + React 19 + Tailwind v4 + Framer Motion + Three.js
  src/landing/        Landing.jsx (frame hero, dusk 3D voice landscape, floating call card), MathsLab.jsx, PhoneVerify.jsx
  src/app/            AppShell (frame + top bar + dock), Check, Live, Cases (queue + mule blocklist), People (Trust Graph)
  src/components/     Dock.jsx (Mac-style bottom dock, every page), Defense.jsx (HoldLock, CodeWordCheck, DecoyPanel, MuleList),
                      Verdict.jsx (heat-gauge Stamp, Waterfall, Highlighted, Waveform), Spectrogram3D.jsx, Icons.jsx
  src/lib/            api.js (VITE_API, default http://localhost:8000), fusion.js, samples.js
extension/            Chrome MV3 Live Call Guard (tabCapture -> offscreen MediaRecorder -> WS /live)
eval/                 run_eval.py (AUROC/EER/FPR, --compress), check_gend.py, manifest.example.csv, message_clf_report.md
demo/                 cloned_cfo_voice.wav (Windows TTS), cloned_cfo_whatsapp.opus, real_human_voice.wav (LibriSpeech CC BY 4.0);
                      face_swap_call.mp4 is local only (gitignored, built from a third-party image)
docs/                 PROJECT_SPEC.md, DEMO.md (run-sheet, slide-to-criterion map, "we fight back" segment), TrustCheck_pitch.pptx (11 slides)
```

## Status (31 Oct 2026, end of day)

Everything below is pushed to `d3coy-trustcheck`.

Models and media (team laptop: RTX 4050 6 GB, Python 3.11 venv `backend/.venv`, torch 2.8.0+cu126):
- Every model runs on the GPU together in 5.5 GB (pellav2, GenD, UnivFD in fp16; ECAPA; faster-whisper large-v3; InsightFace via onnxruntime-gpu 1.23.2).
- Smoke results (n=1 each, NOT an evaluation): TTS voice p(fake) 0.999, human 0.001, unchanged after Opus 16 kbps; face swap 0.979 over 32 frames vs real 0.319.
- Warm timings: 20 s voice note ~2.5 s, 20 s video ~4.5 s. First check after a backend start loads models (~1 min).
- Message classifier: SMS held-out AUROC 0.995; unseen Indian templates AUROC 0.849, recall 0.80, FPR 0.20.

Product, tested 31 Oct:
- Check page: Fake CFO wire HIGH ~98, digital arrest HIGH with 1930, CEO OTP HIGH, harmless LOW 0. Informal money asks now caught (7 scam phrasings HIGH, 6 harmless ones stay "none"; cases in the message self-check).
- Live call: re-transcribes the last 90 s each chunk; cloned CFO HIGH 99.9 at ~13 s, real speech LOW 0, ~1.2–2 s per update warm. Tested by streaming audio to the WebSocket; the human tab-share step in Chrome and the extension on a real call have NOT been tested by a person yet.
- Telegram: bot @trustcheck_semicolons_bot (token in `backend/.env`, never committed). YES/NO and `/code` work on the team phone. Rajesh Kumar and "RAJ NAIK" (HR Lead, created by the team) are linked to two different chats in the local DB; Ananya and Farhan are not linked.
- Decoy Mode, mule blocklist, Human 2FA, cooling-off lock: tested through the API and the browser (decoy caught a new UPI id; a later harmless-looking invoice naming it scored HIGH by the blocklist alone).
- UI redesigned from a team reference (frosted glass over a dusk scene); Mac-style dock for navigation on every page; verified at desktop and phone widths.
- Deck `docs/TrustCheck_pitch.pptx`: 11 slides in the site's style, each tagged "Criterion n of 5", real UI screenshots, speaker notes; slide 6 leads with the four "fight back" features.

Known state of the local DB (gitignored, so a fresh clone has none of this): several test cases and mule entries from today. Before a demo, reset it (see Run) and re-link Telegram chat ids in Trust Graph.

## Run

```powershell
cd backend; .\.venv\Scripts\activate; uvicorn app:app --port 8000
cd frontend; npm run dev        # landing http://localhost:5173 (5174 if 5173 is taken), console /#/app/check
```
Fresh demo data: stop the backend, delete `backend/trustcheck.db`, run `python seed.py`, start the backend, then add each person's Telegram chat id in Trust Graph (they send `/start` to the bot to get it). The backend has no auto-reload: restart it after any Python change. Setup and Windows gotchas are in README.md; the demo script is `docs/DEMO.md`. Warm the models before presenting (one voice note through Check).

## Update 31 Oct night (mentor round)

Done and tested (self-checks, API, browser at desktop and phone widths): every-scam-type detection, link intelligence, QR scams, verification over WhatsApp/SMS/email links with phone pages, code-word page, impact dashboard, share/read-aloud. Message classifier retrained with 41 scam and 43 genuine Indic templates, equal weight per template: unseen-template AUROC 0.921, recall 0.899, FPR 0.234 (was 0.849 / 0.802 / 0.200). Not yet: the phone flow over real Wi-Fi (needs `--host 0.0.0.0`), SMTP email with a real app password, AV model training (next).

## Next steps, in priority order

1. Practise the live demo once with a person doing the Chrome tab share (`demo/cloned_cfo_voice.wav` opened in a tab, "Also share tab audio" ticked); try the extension on a real Meet call.
2. Record the backup demo video (Win + Alt + R) following `docs/DEMO.md`.
3. Training/evaluation (deliberately on hold by the team for now): record consented team voices, clone them (Chatterbox, F5-TTS, XTTS-v2), film Deep-Live-Cam swaps, fill `eval/manifest.csv`, run `python ../eval/run_eval.py ../eval/manifest.csv --compress`, tune thresholds and weights, then replace the left column of deck slide 10 with real numbers.
4. Optional: `ANTHROPIC_API_KEY` in `backend/.env` so Claude reads messages (already wired in `message.llm_tactics`; the lexicon stays as the offline fallback). Decoy replies could also be generated by Claude then.
5. Optional: XLS-R + SLS second audio model (separate service), SyncNet, Grad-CAM, attempt limits on the code-word check.

## Conventions

- Lean code: no new dependencies or abstractions without need; mark deliberate shortcuts with `# ponytail:` comments naming the upgrade path.
- Every detector returns `{signal, label, score 0..1 or None, why, evidence[]}`; a None score means "unavailable" and is ignored by fusion (never penalised).
- If you add a signal or rule, change BOTH `backend/fusion.py` and `frontend/src/lib/fusion.js`, and keep their self-checks passing.
- UI design system: one big rounded white-bezel `.frame` on a misty lavender backdrop, a `.dusk` sky scene inside (the 3D voice landscape as mountains), frosted `.glass` / `.glass-strong` panels, pill controls with an indigo `.orb` arrow, navigation in the bottom `Dock`. Colours: indigo `#23165e` (orb, primary actions), ink `#1c1838`, backdrop `#dedae6`; risk is heat: cold `#26c6da` → `#7c3aed` → `#ff2d6f` → `#ff8a1f` → `#ffd84a` (`.heat-scale`); bands LOW `#0a8ea3`, MEDIUM `#7c3aed`, HIGH `#e01b5f`. Font: Urbanist. Text fields use `rounded-xl` (not pills). The verdict is a heat gauge (`Stamp` in Verdict.jsx).
- Privacy: raw uploads are deleted after analysis; only embeddings are stored; code-word secrets never leave the server. Open CORS, no auth (demo laptop only).
- Honesty: never claim accuracy we haven't measured; the limitations section is part of the pitch.
- Tooling gotchas on this laptop: never rewrite source files with PowerShell `Get-Content`/`Set-Content` (it re-encodes UTF-8 and garbles "…" and "₹"; use the editor tools); long bash heredocs with quotes break, so put scripts in a file; the browser pane is often hidden, so in-page timers stall and screenshots need a viewport size set.
