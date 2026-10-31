# Test every fraud type

Paste each message into **Check a message** (http://localhost:5173/#/app/check), leave *Claims to be* on "Work it out" unless noted, press **Ctrl+Enter**.
Every scam should come back **HIGH** with its type in the *Looks like* badge (a message can show more than one type); the three genuine ones must stay **LOW**.
All of these were run through the real pipeline before being listed here.

## Text and link scams

| # | Fraud type (expected *Looks like*) | Message to paste |
| --- | --- | --- |
| 1 | KYC / account-block phishing | Dear customer, your SBI account will be blocked today due to pending PAN KYC. Update now: http://sbi-kyc-update.xyz/login |
| 2 | Fake bank / fraud department | This is HDFC fraud department. Suspicious transaction on your card. Confirm your card CVV and the OTP we just sent to block it. |
| 3 | Fake parcel / customs fee | India Post: your parcel is on hold due to incomplete address. Pay Rs 25 redelivery fee at indiapost-redelivery.top/in within 12 hours. |
| 4 | Electricity / bill disconnection | Dear consumer, your electricity will be disconnected tonight at 9.30 pm as last month's bill is not updated. Call officer 9876500011 immediately. |
| 5 | Fake e-challan / tax refund / reward points | Your vehicle has a pending traffic e-challan of Rs 500. Pay immediately at echallan-parivahan.cc to avoid court action. |
| 6 | Lottery / prize bait | Congratulations! Your number won Rs 25 lakh in the KBC lucky draw. Pay Rs 12,500 processing fee to claim your prize today. |
| 7 | Task / part-time job scam | Part time job! Earn Rs 3000 daily by liking YouTube videos. Pay Rs 999 registration first, tasks on Telegram. |
| 8 | Investment / trading scam | Join our VIP stock tips group. Guaranteed 40% returns in 30 days. Deposit Rs 10,000 today to start. |
| 9 | Instant-loan app scam | Your personal loan of Rs 2,00,000 is pre-approved, no CIBIL check. Pay Rs 1,999 processing fee and get money in 5 minutes. |
| 10 | Malicious app install | Install the new Aadhaar Update app from this link or your Aadhaar will stop working: tinyurl.com/aadhaar-upd/app.apk |
| 11 | Remote access / tech support | Hello sir, this is Microsoft support. Your laptop has a virus. Please install AnyDesk and give me the code so we can fix it. |
| 12 | Refund / 'sent by mistake' UPI trick | I transferred Rs 3000 to your GPay by mistake, please return it. Scan this QR and enter your UPI PIN to approve the refund. |
| 13 | OTP / account takeover | Hi, I sent you a 6 digit WhatsApp code by mistake. Can you please forward it to me quickly? |
| 14 | OTP / PIN / CVV request | Sir, Airtel office se. Aapka SIM band ho jayega. Jo OTP aaya hai woh bata dijiye abhi. |
| 15 | Sextortion | We recorded your private video call. Pay Rs 40,000 by evening or the clip goes to all your family contacts. |
| 16 | Romance / gift-parcel scam | My dear, I have sent you a gift parcel from London with gold and dollars. Pay the customs clearance fee of Rs 45,000 to receive it. |
| 17 | Family emergency / new number | Hi mom, this is my new number, my phone broke. Send Rs 20,000 to this UPI urgently, don't tell papa. |
| 18 | Personal data harvesting | For your job onboarding, kindly share your Aadhaar card, PAN card and a selfie on this WhatsApp number. |
| 19 | Pay-a-fee-to-receive scam | You have won a Maruti Swift in the lucky draw! Pay registration charges of Rs 6,500 to receive your car. |
| 20 | Impersonation money ask (boss, friend, relative) | Priya, Rajesh here (CFO). In a board meeting, can't call. Urgent and confidential: transfer Rs 45 lakh to our new vendor account now. |
| 21 | Digital arrest / fake police | Main CBI officer bol raha hoon. Aapke naam pe money laundering case hai. Video call pe raho, disconnect mat karna. Turant 2 lakh UPI karo. |
| 22 | Inheritance / donation / 'you've been chosen' scam | prince of wales has decided donate it part of the wealth, u have been chosen as the lucky one for this apportunity and for this transfer as the account is in london you need to send 1 lakh inr to me to open a base account in london so plz do it |

## Genuine look-alikes (must stay LOW)

| # | What | Message to paste |
| --- | --- | --- |
| 23 | bank OTP notice | Your OTP for login to HDFC NetBanking is 482913. Valid for 3 minutes. Do not share this OTP with anyone. |
| 24 | delivery update | Your Flipkart order is out for delivery today. Track it at https://www.flipkart.com/orders. No payment is due. |
| 25 | family message | Mom, I reached the hostel safely. Will call you after dinner. |

## Scams that aren't plain text

| What | How to test | Expected |
| --- | --- | --- |
| Cloned voice | Drop `demo/cloned_cfo_voice.wav`, claims to be Rajesh Kumar | HIGH, "Synthetic media detected", red stretches on the waveform |
| Cloned voice after WhatsApp | Drop `demo/cloned_cfo_whatsapp.opus` | Still HIGH |
| Real voice (control) | Drop `demo/real_human_voice.wav` | LOW, no synthetic badge |
| Face swap | Drop `demo/face_swap_call.mp4` | Face-manipulation signal high, flagged frames shown |
| Scam screenshot | Screenshot any message above (Notes app or a real SMS), drop the image | Same verdict as the text, no "AI image" badge |
| "Scan to receive money" QR | Drop an image of a UPI QR with the text "Scan this QR to receive your cashback" | HIGH, refund / UPI trick |
| Lookalike email | Upload a .eml whose From is `rajesh@acrne.com` (rn instead of m) | Lookalike sender domain flagged |
| Mule blocklist | Decoy Mode on a HIGH case, paste `Use UPI then, fastpay.vendor@ybl` and extract; then check `Please send the pending invoice to UPI fastpay.vendor@ybl today. Thanks` | HIGH from the blocklist alone |
| Live call | Live call page, share a Chrome tab playing `demo/cloned_cfo_voice.wav` | HIGH within ~15 s, challenge prompt |
| Evasion tricks | Paste #1 with **bold** Unicode letters (any "fancy text" generator) or with invisible characters inside "OTP" | Same verdict as the plain text |

Automated version of the table above: `python test_edge_cases.py` (edge cases) and `python ../eval/run_holdout.py ../eval/holdout_messages_v3.csv` (held-out scams) from `backend/`.
