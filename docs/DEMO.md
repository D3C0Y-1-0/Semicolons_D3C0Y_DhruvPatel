# Demo run-sheet (4 minutes)

Slides: `docs/TrustCheck_pitch.pptx` (10 slides, speaker notes on each). Pitch slides 1 to 4, then demo, then slides 9 and 10.

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

## If something breaks

- Backend down: the sidebar shows "Backend offline". Restart uvicorn; the page reconnects by itself.
- Telegram doesn't arrive: press **They didn't send it**; the queue updates the same way.
- Live call stays LOW: the call hasn't asked for anything yet. The score multiplies by what is being asked, so it rises when money or an OTP is mentioned.
- Anything else: play the backup video.
