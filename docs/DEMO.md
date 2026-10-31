# Demo run-sheet (4 minutes + 90 s "we fight back")

Slides: `docs/TrustCheck_pitch.pptx` (11 slides, speaker notes on each; each slide carries a "Criterion n of 5" pill). Pitch slides 1 to 8, then the demo, then slides 9 to 11.

Mentoring round criteria (equal weight) and where each is answered:

| Criterion | Slides | Show live |
| --- | --- | --- |
| 1 Problem understanding | 2 (Arup US$25M, ₹1,935 cr digital arrest, 41% of CISOs, the PS ask) | |
| 2 Proposed approach | 3 thesis, 4 five checks, 5 the maths (A, B, C) | Landing maths lab, "A perfect fake" |
| 3 Technical feasibility | 8 (architecture; every model on one 6 GB GPU, 2.5 s voice note, 4.5 s video, 1.2 s live update) | Check with a voice note, a screenshot |
| 4 Innovation and creativity | 6 the four "fight back" features, 7 the verification loop | Ask the real person, tap NO on a phone |
| 5 Current progress | 9 what works, 10 what's measured and the limits | The full run below |

## 30 minutes before

1. **Clean slate:** `cd backend; .\.venv\Scripts\python.exe reset_demo.py` (clears cases and the blocklist, keeps the people as you set them).
   Don't run `seed.py`: it puts the demo emails and phones back over yours.
2. **Start everything:** from the project folder, `.\start-demo.ps1 -Tunnel`
   (blocked? `powershell -ExecutionPolicy Bypass -File .\start-demo.ps1 -Tunnel`).
   It opens the backend, frontend and tunnel windows, writes the tunnel address into `backend\.env`, waits until the
   models are warm (about 1.5 min) and opens the console. The sidebar should say **Models ready, Email sends itself**.
3. **Trust Graph → Rajesh Kumar:** Work email = an inbox on the "CFO" teammate's phone; Registered mobile = their number.
4. **Code word:** Trust Graph → Rajesh → **Send their code-word page** → the teammate scans the QR and keeps the page open.
5. **Phone check:** the teammate opens the tunnel address + `/health` on their phone. If it doesn't load, Telegram is the backup (below).
6. **Screenshot ready:** a screenshot of a scam SMS (KYC block, parcel fee, electricity cut) on the laptop's desktop.
7. **Live call:** a Meet tab open with the consented voice clone ready to play; Chrome extension loaded from `extension/`.
8. **Backup video** of this exact run on the desktop.

## The run

| Time | Screen | Do | Say |
| --- | --- | --- | --- |
| 0:00 | Landing | Let the hero scan run once | "The voice sounds like your CFO. The request doesn't." |
| 0:30 | Landing, the maths | Click "A perfect fake" | "Every detector fooled: the maths says 17. The policy rule still says HIGH." |
| 1:00 | Console, Check | "Fake CFO wire", claims to be Rajesh Kumar, **Ctrl+Enter** | Read the reasons: never used WhatsApp, ₹45 lakh over his ₹10 lakh limit, new beneficiary |
| 1:45 | Same | **Ask the real person**: the email lands on the teammate's phone by itself (or they scan the QR); they tap **NO** | "A clone can't tap YES on the real phone." The verdict flips to Confirmed attack |
| 2:15 | Security queue | The confirmed attack, money held back; download the CERT-In draft | "Ready for the 6-hour CERT-In window." |
| 2:35 | Check | Drop the **scam screenshot** | "Most scams arrive as forwarded screenshots. We read them, and name the scam." |
| 3:00 | Check | "Digital arrest (Hinglish)" | Point at the 1930 helpline advice |
| 3:15 | Live call | Share the Meet tab, play the clone | HIGH as soon as the money is asked for; read out the challenge |

## The "we fight back" segment (about 90 seconds, after the NO)

1. On the Fake CFO verdict, point at the **30-minute lock**: "Scams run on urgency. We take the urgency away."
2. **Code word**: "Sir, what's our word?" The teammate reads the two words from their code-word page. Type them into
   *Ask for Rajesh's code word*: green. Type anything else: red, "treat as an impostor".
   Line: "We cloned 120 real voices; the voiceprint accepted every single clone. The code word can't be cloned."
3. **Decoy Mode**: press *Start Decoy Mode*. Read the decoy's line ("what exact name should I write as the beneficiary?").
   Paste a scammer reply such as `Use UPI then, fastpay.vendor@ybl. Hurry up` and press *Extract and reply*. The UPI id
   lights up and goes on the blocklist.
4. **Blocklist pays off**: Security queue shows the *Mule blocklist*. Then on Check, paste a polite, harmless-looking
   `Please send the pending invoice to UPI fastpay.vendor@ybl today. Thanks` with no claimed person: **HIGH**, purely
   because that UPI id was caught by the decoy.

Line: "Every other tool defends. We turn the scam into evidence against the scammer."

## If something breaks

- **Phone link won't open (tunnel down):** restart the tunnel window (`.\start-demo.ps1 -Tunnel` again re-writes the
  address), or answer on **Telegram** (needs no tunnel), or press **It wasn't them**: the queue updates the same way.
- **Email doesn't arrive:** check spam, then use the QR on screen.
- **Backend down:** the sidebar shows "Backend offline". Restart it; the page reconnects by itself.
- **First voice check slow:** models were still warming. The sidebar says when they're ready.
- **Live call stays LOW:** the call hasn't asked for anything yet. The score multiplies by what is being asked, so it
  rises when money or an OTP is mentioned.
- **Anything else:** play the backup video.
