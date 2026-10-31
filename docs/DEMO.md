# Demo run-sheet (4 minutes)

Slides: `docs/TrustCheck_pitch.pptx` (11 slides in the site's glass style, speaker notes on each; each slide carries a "Criterion n of 5" pill). Pitch slides 1 to 8, then the demo, then slides 9 to 11.

Mentoring round criteria (equal weight) and where each is answered:

| Criterion | Slides | Show live |
| --- | --- | --- |
| 1 Problem understanding | 2 (Arup US$25M, ₹1,935 cr digital arrest, 41% of CISOs, the PS ask) | |
| 2 Proposed approach | 3 thesis, 4 five checks, 5 the maths (A, B, C) | Landing maths lab, "A perfect fake" |
| 3 Technical feasibility | 8 (architecture; 5.5 GB on one 6 GB GPU, 2.5 s voice note, 4.5 s video, 1.2 s live update) | Check with a voice note |
| 4 Innovation and creativity | 6 six differentiators, 7 Telegram verification loop | Ask the real person, tap NO |
| 5 Current progress | 9 what works, 10 what's measured and the limits | The full run below |

## 30 minutes before

1. Backend: `cd backend; .\.venv\Scripts\activate; uvicorn app:app --port 8000`
2. Frontend: `cd frontend; npm run dev` and open http://localhost:5173
3. Clean queue: stop the backend, delete `backend/trustcheck.db`, run `python seed.py`, start it again.
4. Warm the models: on **Check a message**, drop one voice note and one video and press **Check before I act**. The first check after a start takes about a minute; afterwards a 20 s voice note takes about 2.5 s.
5. Telegram: `TELEGRAM_BOT_TOKEN` in `backend/.env`; the teammate playing the CFO has sent `/start` to the bot, and their chat id is saved on Rajesh Kumar in **Trust Graph**. Without this, use the **They didn't send it** button instead of the phone.
6. Live call: a Meet tab open with the consented voice clone ready to play; Chrome extension loaded from `extension/`.
7. Backup video of this exact run on the desktop.

## The run

| Time | Screen | Do | Say |
| --- | --- | --- | --- |
| 0:00 | Landing | Let the hero scan run once | "The voice sounds like your CFO. The request doesn't." |
| 0:30 | Landing, the maths | Click "A perfect fake" | "Every detector fooled: the maths says 17. The policy rule still says HIGH." |
| 1:00 | Console, Check | "Fake CFO wire", claims to be Rajesh Kumar, Check | Read the three reasons: never used WhatsApp, ₹45 lakh over his ₹10 lakh limit, new beneficiary |
| 1:45 | Same | **Ask the real person on Telegram**; teammate taps NO | "A clone can't tap YES on the real phone." |
| 2:15 | Security queue | Shows the confirmed attack; download the CERT-In draft | "Ready for the 6-hour CERT-In window." |
| 2:45 | Check | "Digital arrest (Hinglish)" | Point at the 1930 helpline advice |
| 3:15 | Live call | Share the Meet tab, play the clone | HIGH as soon as the money is asked for; read out the challenge |

## The "we fight back" segment (about 90 seconds, after the Telegram NO)

1. On the Fake CFO verdict, point at the **30-minute lock**: "Scams run on urgency. We take the urgency away."
2. **Code word**: "Sir, what's our word?" On the phone linked to Rajesh, send `/code` to @trustcheck_semicolons_bot and read the two words out. Type them into *Ask for Rajesh's code word*: green. Type anything else: red, "treat as an impostor".
3. **Decoy Mode**: press *Start Decoy Mode*. Read the decoy's line ("what exact name should I write as the beneficiary?"). Paste a scammer reply such as `Use UPI then, fastpay.vendor@ybl. Hurry up` and press *Extract and reply*. The UPI id lights up and goes on the blocklist.
4. **Blocklist pays off**: open Security queue to show the *Mule blocklist*. Then on Check, paste a polite, harmless-looking `Please send the pending invoice to UPI fastpay.vendor@ybl today. Thanks` with no claimed person: **HIGH**, purely because that UPI id was caught by the decoy.

Line: "Every other tool defends. We turn the scam into evidence against the scammer."

## If something breaks

- Backend down: the sidebar shows "Backend offline". Restart uvicorn; the page reconnects by itself.
- Telegram doesn't arrive: press **They didn't send it**; the queue updates the same way.
- Live call stays LOW: the call hasn't asked for anything yet. The score multiplies by what is being asked, so it rises when money or an OTP is mentioned.
- Anything else: play the backup video.
