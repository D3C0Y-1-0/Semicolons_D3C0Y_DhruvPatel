# Manual test plan

Tick each box as you go. "Expected" is what a pass looks like; anything else, note the step number and what you saw.
Test files are in `demo/`. Console: http://localhost:5173/#/app/check

## 0. Setup (5 min)

- [ ] `cd backend; .\.venv\Scripts\python.exe reset_demo.py` → "cleared … kept 3 people"
- [ ] From the project folder: `.\start-demo.ps1 -Tunnel` → green "TrustCheck ready", console opens
- [ ] Sidebar status: Backend online, **Models ready**, Email sends itself, Telegram on
- [ ] On your phone, open the tunnel address + `/health` → `{"ok":true,…}`
- [ ] Trust Graph → Rajesh Kumar has your inbox as Work email and your number as Registered mobile

## 1. Scam messages (Check page, one scenario chip each, then **Ctrl+Enter**)

| # | Scenario | Expected |
| --- | --- | --- |
| [ ] 1.1 | Fake CFO wire, claims to be Rajesh Kumar | HIGH ~100, "Looks like: Impersonation money ask", 30-minute lock, reasons: WhatsApp not his channel, over his ₹10 lakh limit |
| [ ] 1.2 | Digital arrest (Hinglish) | HIGH, advice mentions 1930 and "real police never arrest over video call" |
| [ ] 1.3 | CEO asks for OTP | HIGH, "OTP / PIN / CVV request" |
| [ ] 1.4 | KYC phishing link | HIGH, "KYC / account-block phishing", link reason says it isn't SBI's real site |
| [ ] 1.5 | Parcel fee link | HIGH, "Fake parcel / customs fee" |
| [ ] 1.6 | Part-time job (Hinglish) | HIGH, "Task / part-time job scam" |
| [ ] 1.7 | Harmless update | LOW, no lock, no scam type |
| [ ] 1.8 | Type your own: "Hi mom, new number, send 20000 urgently to this UPI, don't tell papa" | HIGH, family emergency |
| [ ] 1.9 | Type your own genuine one: "Your OTP is 482913. Do not share it with anyone. - HDFC Bank" | LOW |

## 2. Screenshot of a scam
- [ ] 2.1 Screenshot any scam SMS (or type one into Notes and screenshot it), drop the image on Check → HIGH, the scam type named, **no** "Synthetic media" badge
- [ ] 2.2 Screenshot a normal chat → LOW

## 3. Voice, video, image (drop the file, no text)
- [ ] 3.1 `demo/cloned_cfo_voice.wav`, claims to be Rajesh → HIGH, "Synthetic media detected", red stretches on the waveform, transcript shown, within ~15 s
- [ ] 3.2 `demo/cloned_cfo_whatsapp.opus` → still HIGH (WhatsApp compression)
- [ ] 3.3 `demo/real_human_voice.wav` → LOW, no synthetic badge
- [ ] 3.4 `demo/face_swap_call.mp4` → face-swap signal high, face frames shown
- [ ] 3.5 Any photo from your phone → no false "AI-generated" on an ordinary camera photo (note the score)

## 4. Ask the real person (on the 1.1 verdict)
- [ ] 4.1 Press **Ask the real person** → "Sent to Rajesh by email" + a QR code
- [ ] 4.2 Email arrives on your phone within a minute (check spam) → open the link → YES/NO page shows the message
- [ ] 4.3 Tap **NO** → laptop flips to "Confirmed attack" by itself; lock turns red "Payment blocked"
- [ ] 4.4 Open the same link again and tap YES → it still says NOT you (first answer wins)
- [ ] 4.5 New 1.1 check → Ask → **scan the QR** with the phone → tap YES → "Verified genuine", lock says "Released"
- [ ] 4.6 New 1.1 check → Ask → answer on **Telegram** instead → same result
- [ ] 4.7 Download CERT-In report on a confirmed attack → a .md file with the identifiers

## 5. Fight back
- [ ] 5.1 Trust Graph → Rajesh → **Send their code-word page** → scan QR → two words, changing every 30 s
- [ ] 5.2 On a HIGH Rajesh verdict, type those words into *Ask for Rajesh's code word* → green "Correct"
- [ ] 5.3 Type wrong words → red "Wrong code word"
- [ ] 5.4 On a HIGH verdict, **Start Decoy Mode** → a victim-style reply appears
- [ ] 5.5 Paste `Use UPI then, fastpay.vendor@ybl. Hurry up` → **Extract and reply** → the UPI id lights up as caught
- [ ] 5.6 Security queue → Mule blocklist shows it
- [ ] 5.7 Check: `Please send the pending invoice to UPI fastpay.vendor@ybl today. Thanks` (no claimed person) → HIGH because of the blocklist

## 6. Live call
- [ ] 6.1 Open `demo/cloned_cfo_voice.wav` in a Chrome tab
- [ ] 6.2 Live call page → claims to be Rajesh → **Listen to a call tab** → pick that tab, tick **Also share tab audio** → play
- [ ] 6.3 Readings every ~3 s; HIGH once the money is asked for (~13 s); a challenge prompt appears
- [ ] 6.4 Same with `demo/real_human_voice.wav` → stays LOW
- [ ] 6.5 Real Google Meet call with a teammate (Chrome extension or tab share) → readings arrive

## 7. Console and Trust Graph
- [ ] 7.1 Ctrl+1 / 2 / 3 / 4 switch pages; red traffic light goes to the landing page
- [ ] 7.2 Security queue badge counts open HIGH cases; tiles and "Money held back" update
- [ ] 7.3 Enrol a new test person (name, email, 2 channels) → appears in the list
- [ ] 7.4 Phone width (or a narrow browser window): one column, dock at the bottom, no sideways scrolling

## 8. Things going wrong
- [ ] 8.1 Drop a .pdf → clear "can't be checked" message
- [ ] 8.2 Stop the backend → sidebar says "Backend offline"; a check says it can't reach the backend; start it again → recovers
- [ ] 8.3 Close the tunnel window → QR/email links fail on the phone; Telegram and "It wasn't them" still work

## 9. After testing
- [ ] `cd backend; .\.venv\Scripts\python.exe reset_demo.py` so the demo starts clean
- [ ] Note every failed step number with what you saw, and send it over
