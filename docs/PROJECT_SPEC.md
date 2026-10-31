# TrustCheck: complete project specification

Team Semicolons, D3COY 2026, Problem Statement 02 "AI-Based Deepfake-Enabled Social Engineering Detection".
This is the single source of truth for what the final project is, what it does, how it decides, and how it's demonstrated. It reflects what is actually built (31 Oct 2026). CLAUDE.md has the working context; README.md has setup.

---

## 1. The problem, in the PS's own terms

Generative AI makes convincing fake voices, videos, images and messages. Attackers use them for executive impersonation, fraudulent payment requests and identity deception. Old tells (typos, odd wording, visual glitches) no longer work. The PS cites CERT-In's deepfake guidance and a September 2026 Gartner survey: 41% of CISOs saw a deepfake in an employee audio call in the past year.

**Challenge:** detect and assess deepfake-enabled social-engineering attempts by analysing digital content *and the context it arrives in*, explain the indicators, and push users to verify through a trusted channel *before acting*.

**Six objectives (each must be visible in the demo):**

| # | PS objective | TrustCheck feature |
| --- | --- | --- |
| 1 | Synthetic media detection | pellav2 cloned-voice detector, GenD face-swap detector, lip-sync check, UnivFD AI-image detector, C2PA/metadata provenance |
| 2 | Suspicious message analysis | Tactic tagger (Claude API or EN/Hinglish/Hindi lexicon), our trained scam-language classifier, email header forensics, lookalike domains, URL reputation |
| 3 | Multimodal risk assessment | Log-odds fusion × impact of the request + policy floors |
| 4 | Identity and context verification | Org Trust Graph: voiceprint, face, registered channels, hours, approval limit, usual requests |
| 5 | Explainable detection | Verdict stamp, plain-language reasons, signed "why this score" chart, underlined tactics, waveform with synthetic stretches shaded, worst face frames |
| 6 | User alerting and reporting | Action list, challenge prompts, Telegram out-of-band verification, payment hold, security queue, campaign clustering, CERT-In report draft |

**Deliverables:** working prototype, UI with risk and indicators, demo on authorised/public/generated samples, documentation on methodology, model limitations and response workflow.

---

## 2. The idea that wins

> "Detectors will lose the arms race. Process won't. We don't only ask *is this fake?* We ask *should you act on this?*"

Every other team will ship "upload, classifier, 87% fake". TrustCheck scores the risk of *acting*, so it still protects people when a deepfake is perfect, and it ends in a verification step a cloned voice cannot pass: the real person confirming on the phone they enrolled.

---

## 3. Users and journeys

- **Employee (finance, HR, assistants):** gets a call, voice note, video or message asking for money, an OTP or files. Pastes or drops it into *Check a message*, or runs *Live call* / the Chrome extension during a call. Gets a verdict, reasons, what to do, a challenge to try, and a button to ask the real person.
- **Executive being impersonated:** enrolled in the Trust Graph. Receives a Telegram "Did YOU send this request?" with YES/NO.
- **Security team (SOC):** watches the *Security queue*: live counts, filters, campaigns, case detail, CERT-In draft.
- **Citizen (India):** forwards a suspicious voice note or message to the Telegram bot; gets HIGH/MEDIUM/LOW in English and Hindi, with the 1930 helpline for digital-arrest scams.

---

## 4. System architecture

```
Inputs                     Detectors (FastAPI, one service)                       Decision            Outputs
-------                    ---------------------------------                      --------            -------
Web upload  ─┐             Audio: pellav2 spoof timeline, ECAPA voiceprint,        Fusion engine:      Verdict UI + reasons
Live tab     ├──► /analyze  faster-whisper transcript                              log-odds evidence   Telegram verify (YES/NO)
 (web, ext)  │   /live WS   Video: InsightFace faces, GenD per frame, lip-sync      × impact            Payment hold
Telegram bot ┘              Image: UnivFD, C2PA/metadata, GenD on faces             + policy floors     Security queue + campaigns
                            Message: headers, lookalikes, URLs, tactics, classifier                     CERT-In report draft
                            Identity: Trust Graph context + biometrics (SQLite)
```

Every detector returns `{signal, label, score 0..1 | None, why, evidence[]}`. A None score is "unavailable" and is ignored, never penalised. Raw media is deleted after analysis; only embeddings are stored.

---

## 5. Models (as built)

| Check | Model | Source and licence | Notes |
| --- | --- | --- | --- |
| Cloned voice | pellav2 (w2v-BERT 2.0 backbone, 600M, + layer weighting) | HF `Sadanie/pellav2-audio-deepfake-detector`, MIT | 95.8% on a 2026 benchmark of ~25 modern cloning systems; 4 s windows, 2 s hop, clip score = mean of the worst 30% |
| Voiceprint | ECAPA-TDNN | `speechbrain/spkrec-ecapa-voxceleb`, Apache-2.0 | Cosine vs enrolled; threshold `VOICE_THRESHOLD` (tune on eval) |
| Transcript | faster-whisper large-v3 (small for live) | MIT | Hindi/Hinglish |
| Face swap | GenD CLIP ViT-L/14 | `yermandy/GenD_CLIP_L_14`, WACV 2026, MIT (model code vendored) | Cross-dataset AUROC 96.0 Celeb-DF v2, 87.1 DFDC; 32 frames, top-third mean |
| Face detect + match | InsightFace buffalo_l (ArcFace) | non-commercial models (fine for a hackathon) | 1.3× crop, 224 px |
| Lip-sync | Mouth-region motion vs speech energy, best lag correlation | ours | Heuristic stand-in for SyncNet |
| AI-generated image | UnivFD (CLIP ViT-L/14 + trained linear head) | Ojha et al., CVPR 2023, MIT; head in `models/univfd_fc.pth` | 5-crop mean |
| Provenance | C2PA Content Credentials, EXIF/PNG generator metadata | c2pa-python | "trainedAlgorithmicMedia" = AI |
| Tactics | Claude API JSON tagger; fallback lexicon (EN/Hinglish/Hindi) | ours | urgency, secrecy, authority, payment, credential/OTP, channel switch, new beneficiary, fear/legal threat, reward |
| Scam language | **Trained by us**: char 2–5 + word 1–2 TF-IDF, calibrated logistic regression | `train/train_message_clf.py` | SMS held-out AUROC 0.995; unseen Indian templates AUROC 0.849, recall 0.80, FPR 0.20 |
| Email | SPF/DKIM/DMARC, Reply-To, display-name spoof, lookalike domains (edit distance, homoglyphs), URL blocklist + Safe Browsing | ours | `ORG_DOMAINS` in .env |

`python backend/setup_models.py` downloads all of these and prints PASS/FAIL for each.

---

## 6. How the verdict is computed

```
T = sigmoid( b + Σ wᵢ · ln(sᵢ / (1 − sᵢ)) ),  b = ln(0.05/0.95) = −2.944
R = 100 × T × Impact
```

Impact: 1.0 large payment / new account / gift cards / crypto; 0.8 credentials, OTP, remote access; 0.7 routine payment; 0.4 share documents; 0.2 no action.
Bands: LOW < 30, MEDIUM 30–59, HIGH ≥ 60.

Weights: audio_spoof 1.0, voice_mismatch 0.8, face_video 0.8, face_mismatch 0.6, lip_sync 0.5, image_synthetic 0.6, image_univfd 0.7, message_tactics 0.6, message_classifier 0.4, context_anomaly 1.0, lookalike_domain 0.7, header_auth 0.6, bad_url 1.2.

Policy floors:
1. Payment/credential request AND (unregistered channel OR new beneficiary): HIGH; verification mandatory.
2. Known-bad URL: HIGH.
3. Digital-arrest pattern (police/CBI/court threat + payment or "stay on the call"): HIGH, with citizen advice and 1930.
4. Both audio models ≥ 0.9: MEDIUM.
5. Voiceprint mismatch for the claimed enrolled person: MEDIUM.

Worked examples (asserted in code, shown in the landing-page maths lab):
- **A** Fake CFO wire: evidence +9.94, T 0.9991, ×1.0 = **99.9 HIGH**
- **B** Same fake, birthday wish: T 0.489 × 0.2 = **9.8 LOW**
- **C** Perfect fake fools detectors: maths **17.3**, Rule 1 lifts to **HIGH**

---

## 7. Response workflow

Message or call arrives → Analyse → band.
- LOW: allow; badge if media is synthetic.
- MEDIUM: warn, challenge prompt, verification suggested.
- HIGH: hold the payment; verification mandatory → Telegram to the real person's enrolled chat.
  - YES: release, close as verified.
  - NO or no reply: confirmed attack → security queue, CERT-In draft (6-hour window), block sender, link the voice to a campaign.

Challenge prompts (GOTCHA, NYU): wave a hand across the face, press a finger into the cheek, glasses on/off, big expression change, team code word, a random phrase, or call back on the registered number.

---

## 8. Product surface

**Landing page** (`#/`): 3D spectrogram hero (the cloned segment turns red, the HIGH stamp drops), a three-number problem ledger, the live maths lab (sliders, presets A/B/C), the five-step pipeline, the interactive Telegram verification phone, India features, honest limits, CTA.

**Console** (`#/app/...`):
- *Check a message*: sample scenarios (Fake CFO wire, Digital arrest Hinglish, CEO asks for OTP, Harmless update), text, media drop zone with preview, .eml, channel, claimed person, sender. Verdict: stamp, headline, reasons, actions, challenge, verification buttons, CERT-In download, policy rules, waterfall with evidence and face thumbnails, waveform, transcript, underlined message.
- *Live call*: share a call tab; 3D landscape reacts to risk; stamp, challenge, heard tactics, segment bars, transcript.
- *Security queue*: count tiles that filter, live 3 s refresh, campaigns, case detail.
- *Trust Graph*: enrolled people and their normal patterns; enrolment form with voice sample and photo.

**Chrome extension** (Live Call Guard): popup, badge with live risk, notification on HIGH.
**Telegram bot:** verification YES/NO, `/start` returns chat id, citizen mode.

Design system: night `#0d1730`, paper `#eef3f1`, ink `#14213d`, genuine `#2f8f7a`, caution `#b7791f`, synthetic `#c2341f`, action `#3b4ba8`; Archivo variable (wide headings, condensed stamp); one bold element per screen.

---

## 9. Evaluation plan (what to measure before the pitch)

Authorised data only, with written consent for every cloned voice or face.
- Audio: 60 real (team in EN/HI/Hinglish + LibriTTS/VCTK) and 60 clones (Chatterbox, F5-TTS, XTTS-v2), plus WhatsApp-like re-encodes.
- Video: 40 real and 40 fake (Deep-Live-Cam swaps of teammates + Celeb-DF v2/DFDC).
- Images: 50 camera, 50 FLUX/SDXL.
- Scenarios: 100 attacks (20 "perfect fakes") and 100 benign.
- Metrics: AUROC, EER, FPR per detector, clean vs compressed; fusion HIGH recall on attacks (goal ≥ 95%), false HIGH on benign (goal ≤ 5%); ablation of media only vs + message vs full. Tool: `eval/run_eval.py`.

---

## 10. Demo (4 minutes)

1. Landing hero runs once; the line: "The voice sounds like your CFO. The request doesn't."
2. Maths lab: "A perfect fake", where the maths says 17 and the rule says HIGH.
3. Console: Fake CFO wire as Rajesh Kumar gives HIGH with reasons.
4. Ask the real person: the teammate on stage taps NO; the queue updates live; download the CERT-In draft.
5. Digital arrest (Hinglish) gives HIGH with the 1930 advice.
6. Live call with a consented voice clone; the challenge breaks the face swap.
Fallback: pre-recorded video of the same run.

---

## 11. Limitations (say them out loud)

- Detectors miss generators they haven't seen; new cloning tools appear monthly.
- Phone/WhatsApp compression lowers accuracy; report the gap.
- Good clones can pass voiceprints; they can't tap YES on the real person's phone.
- AI-written text can't be reliably detected; we judge manipulation, not authorship.
- Our classifier's 20% false-positive rate on unseen Indian phrasings is why it carries weight 0.4, not a veto.
- Trust Graph quality depends on enrolment; challenges must be rotated.
- Demo build: open CORS, no auth, single laptop.

## 12. Ethics and privacy

Consent for all cloned samples; embeddings only, never raw media (DPDP Act 2023: purpose limitation, consent, deletion); the system advises and holds, a human decides; cloning tools are used only on the team's own consented samples.
