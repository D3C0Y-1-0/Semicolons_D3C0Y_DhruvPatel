"""Synthetic bilingual (English / Hinglish / Hindi) corpus of Indian social-engineering messages and
look-alike benign ones. Each row keeps its template id so evaluation can hold out whole templates:
the classifier is scored on phrasings it has never seen, not on reshuffled slot fills.

Hard negatives are deliberate: genuine bank OTP notices, real payment reminders, polite urgent work
requests. They share vocabulary with scams, so the model has to learn the manipulation, not the topic."""
import itertools
import random

NAMES = ["Rajesh", "Ananya", "Vikram", "Priya", "Sanjay", "Meera", "Arjun", "Kavita", "Rohit", "Neha"]
ROLES = ["CFO", "CEO", "MD", "Director", "VP Finance", "Head of Accounts"]
AMOUNTS = ["₹45,00,000", "₹12 lakh", "Rs 3,50,000", "₹2 crore", "Rs 85,000", "₹9.5 lakh", "INR 18,40,000"]
SMALL = ["₹2 lakh", "Rs 49,999", "₹1,20,000", "Rs 15,000", "₹75,000"]
APPS = ["WhatsApp", "Telegram", "Signal", "my personal number"]
MINUTES = ["15 minutes", "30 minutes", "1 hour", "the next hour", "EOD today"]
AGENCIES = ["CBI", "Mumbai Police", "Narcotics Control Bureau", "ED", "Customs", "Cyber Crime Branch", "TRAI"]
CITIES = ["Mumbai", "Delhi", "Bengaluru", "Pune", "Hyderabad"]

SCAM = {
    "ceo_wire": "Hi {n}, {r} here. I'm in a board meeting and can't talk. Need you to transfer {a} to our new vendor account urgently, within {m}. Keep this confidential, message me on {app} once done.",
    "ceo_wire_short": "{n}, urgent. Process a payment of {a} to the account below right away. Don't discuss with the team, I'll explain later. - {r}",
    "invoice_change": "Dear accounts team, please note our bank details have changed. Kindly remit the pending invoice of {a} to the new account by {m}, otherwise the shipment will be held.",
    "gift_cards": "Hey {n}, are you at your desk? I need a quick favour. Buy 10 Amazon gift cards for a client and send me the codes on {app}. Keep it between us. - {r}",
    "kyc_otp": "Dear customer your SBI account will be blocked today due to pending KYC. Share the OTP sent to your mobile immediately to avoid suspension.",
    "otp_ceo": "{n}, {r} here, locked out of the bank portal before the audit. Send me the OTP you just received, urgently. Don't tell anyone please.",
    "remote_access": "This is the IT helpdesk. Your system is compromised. Install AnyDesk now and share the 9 digit code so we can secure your account immediately.",
    "digital_arrest_en": "This is an officer from {ag}. A parcel in your name with illegal drugs was seized in {c}. You are under digital arrest. Stay on the video call and transfer {s} for verification or police will come to your house.",
    "digital_arrest_hing": "Main {ag} se officer bol raha hoon. Aapke naam pe money laundering case hai, arrest warrant nikla hai. Video call pe raho, disconnect mat karna. Turant {s} UPI karo verification ke liye.",
    "digital_arrest_hi": "मैं {ag} से अधिकारी बोल रहा हूँ। आपके नाम पर मनी लॉन्ड्रिंग का केस है। कॉल मत काटिए, तुरंत {s} ट्रांसफर कीजिए वरना आपको गिरफ्तार किया जाएगा।",
    "electricity": "Dear consumer your electricity will be disconnected tonight at 9.30 pm because previous month bill was not updated. Call electricity officer immediately on 98xxxxxx10.",
    "customs_parcel": "Your international parcel is held at {c} customs. Pay clearance fee of {s} within {m} via the link or the parcel will be returned and a case filed.",
    "task_job": "Part time job! Earn Rs 3000 daily by liking YouTube videos. Pay {s} registration first to unlock high paying tasks. Limited seats, reply on {app} now.",
    "refund_hing": "Sir aapka refund {s} pending hai. Jaldi se link pe click karke UPI PIN daalo, warna refund cancel ho jayega. Kisi ko mat batana.",
    "boss_hing": "{n} ji, {r} bol raha hoon. Bahut urgent hai, abhi ke abhi {a} is naye account mein transfer kar do. Kisi ko mat batana, baad mein baat karte hain. {app} pe message karo.",
    "bank_impersonation": "This is calling from HDFC fraud department. Suspicious transaction of {s} detected. To block it, confirm your card CVV and the OTP we just sent, right now.",
    "lottery": "Congratulations! Your number won {a} in the KBC lucky draw. Pay {s} processing fee to claim your prize today.",
    "pan_kyc": "Your PAN card will be deactivated today. Update KYC by clicking the link and entering your net banking password immediately.",
    "favour_ping": "{n} this is your {r}. I need a small favour, are you free? Don't call, I'm in a meeting. Reply only on {app}.",
    "sim_block_hing": "Aapka SIM 2 ghante mein band ho jayega. TRAI officer se baat karne ke liye 9 dabaiye aur Aadhaar number aur OTP batayiye.",
    "investment": "Investment opportunity: guaranteed 40% returns in 30 days. Join our {app} group and deposit {s} today to start, seats closing.",
    "family_emergency": "Your son has been arrested in {c}. Send {s} immediately for bail. Don't tell anyone, he is scared and cannot talk.",
    "tech_support": "Hello sir, I am calling from Microsoft. Your computer has a virus. Install TeamViewer now and give me the code so I can fix it.",
    "sextortion_threat": "We have recordings of your video call. Pay {s} in crypto within {m} or it will be sent to all your contacts. Do not contact police.",
    # beyond money asks: links, apps, data and account takeover
    "kyc_link": "Dear customer your {bank} account will be suspended today. Complete PAN KYC now at {bad}/kyc to avoid blocking.",
    "kyc_link_hing": "Aapka {bank} account aaj band ho jayega. KYC update karne ke liye is link pe click karo: {bad}/update",
    "parcel_link": "{courier}: your parcel is on hold due to incomplete address. Update details and pay Rs 25 redelivery fee at {bad} within 12 hrs.",
    "challan_link": "Your vehicle has a pending traffic e-challan of Rs 500. Pay immediately at {bad} to avoid court action and licence suspension.",
    "it_refund_link": "Income Tax Dept: you are eligible for a refund of {s}. Submit your bank details at {bad} to receive it today.",
    "reward_points": "Your {bank} credit card reward points worth {s} expire today. Redeem now: {bad}",
    "apk_loan": "Pre-approved instant loan of {a} sanctioned in your name. Download the app now to get money in 10 minutes: {bad}/loan.apk",
    "apk_update": "{bank} alert: install the new security update app from {bad}/secure.apk or your net banking will stop working today.",
    "code_mistake": "Hi, I sent you a 6 digit code by mistake on your phone. Please forward it to me quickly, it's urgent.",
    "code_mistake_hing": "Sorry galti se aapke number pe OTP chala gaya, please woh code bhej do jaldi.",
    "sim_esim": "Your SIM will be deactivated in 2 hours due to eSIM upgrade. Reply with the OTP you receive to continue service.",
    "family_new_number": "Hi mom, this is my new number, my phone broke. Can you send {s} to this UPI for an urgent bill? Will explain later.",
    "romance_gift": "My dear, I have sent you a gift parcel from London with gold and dollars. Pay the customs clearance fee of {s} to the agent to receive it.",
    "upi_mistake": "I sent {s} to your account by mistake, please return it. Scan this QR code and enter your UPI PIN to receive the refund.",
    "aadhaar_harvest": "For the work from home job, please send your Aadhaar card, PAN card and a selfie on {app} to complete verification.",
    "electricity_link": "Electricity bill not updated. Your power will be disconnected tonight. Pay now at {bad} or call our officer.",
    "crypto_group": "Join our VIP crypto signals group. Guaranteed 3x profit in 7 days, members earning {a} monthly. Deposit {s} to start.",
}

BENIGN = {
    "bank_otp_notice": "{o} is your OTP for the transaction of {s} at Amazon. Do not share this OTP with anyone. Bank never asks for OTP. - HDFC Bank",
    "salary_credit": "Your a/c XX4521 is credited with {a} on 31-10 by NEFT from ACME PVT LTD salary. Avl bal updated.",
    "meeting_move": "Hi team, the quarterly review moves to Thursday 3 pm. Please send me the updated report by Wednesday. Thanks, {n}",
    "urgent_work_legit": "{n}, can you share the Q3 deck before the client call at 4? It's a bit urgent, the slides are on the shared drive.",
    "invoice_legit": "Hi accounts, attaching invoice INV-2291 for {s} as per the PO. Payment terms remain 30 days to our usual account on file. Regards",
    "payment_reminder_legit": "Reminder: your electricity bill of {s} is due on 15 Nov. Pay via the official app or website. Ignore if already paid.",
    "family_hing": "Beta khana kha liya? Papa puch rahe the tum kab aa rahe ho Diwali pe. Call karna jab free ho.",
    "family_hi": "दीदी, मैं शाम को सात बजे तक घर पहुँच जाऊँगा। माँ को बता देना।",
    "office_hing": "{n} kal ki meeting 11 baje shift ho gayi hai, conference room B mein. Laptop le aana.",
    "approval_flow": "Hi {n}, the vendor payment of {a} is in the ERP for your approval as the second approver. Details are in the usual workflow.",
    "it_notice_legit": "IT notice: planned maintenance on Saturday 10 pm to 2 am. No action needed. Never share your password with anyone, including IT.",
    "delivery_legit": "Your Flipkart order will be delivered today between 2 pm and 6 pm. Share the delivery code only with the delivery agent at your door.",
    "congrats_legit": "Congratulations {n} on closing the quarter! Team lunch on Friday at 1, my treat. - {r}",
    "birthday": "Happy birthday {n}! Cake in the pantry at 4, see you there.",
    "travel": "Cab booked for 6.30 am tomorrow to {c} airport, driver will call 10 min before. Have a safe trip.",
    "leave_approval": "Please approve the leave request for {n} from Monday to Wednesday in the HR portal when you get a moment.",
    "client_quote": "{n}, the client wants the revised quote today. Can you check the numbers and reply on the email thread?",
    "payment_received": "Payment of {s} received for invoice INV-4410. Thank you for your business. Receipt attached.",
    "upi_success": "Your UPI payment of {s} to Zomato was successful. Ref no 402199113. Not you? Call the number on the back of your card.",
    "timesheets": "Team, reminder to submit timesheets by 6 pm Friday. Ping me if the portal is down.",
    "minutes": "Hi {n}, sharing the minutes of today's call. Action items are highlighted, deadlines are next week.",
    "family_hing_2": "Mummy ne bola hai shaam ko aate waqt sabzi aur doodh le aana. Aur jaldi aana, mehmaan aa rahe hain.",
    "friends_hing": "Bhai kal match dekhne chalega? {c} mein screening hai 7 baje, tickets maine book kar liye.",
    "office_hi": "कल ऑफिस में दस बजे मीटिंग है, रिपोर्ट तैयार रखना और प्रिंट भी ले आना।",
    "pnr": "Your train PNR 4521837702 to {c} is confirmed, coach B2 seat 34. Happy journey.",
    "school": "Dear parent, school will remain closed on Monday on account of Diwali. Classes resume Tuesday.",
    "boss_praise": "{r} here: great work on the audit, {n}. Let's catch up Monday 10 am in my cabin to plan next quarter.",
    "portal_otp": "Your OTP to log in to the HR portal is {o}. Valid for 10 minutes. Do not share it with anyone.",
    "vendor_process": "Hi {n}, finance will process vendor payments on Friday as usual, after both approvals in the ERP.",
    "agreement": "Kindly find attached the signed agreement. Please countersign and return at your convenience.",
    "card_due": "Reminder: credit card bill of {s} is due on 5 Nov. Pay through the official bank app. Ignore if already paid.",
    "urgent_legit_2": "{n}, urgent: the server room AC has failed, please move the backup drives to rack 3 today. Facilities is on it.",
    "recruiter_legit": "Hi {n}, thanks for applying. Your interview with our team is scheduled for Monday 11 am on Teams. No fee is charged at any stage.",
    # genuine messages with links, apps and codes: the model must learn the lure, not the URL
    "order_track": "Your {courier} shipment is out for delivery today. Track it at {good}. No payment is due.",
    "doc_share": "{n}, sharing the slides for tomorrow: {good}/slides. Comments welcome before 5 pm.",
    "meeting_link": "Join the weekly sync at 4 pm: {good}/meet. Agenda is in the invite.",
    "app_update_legit": "A new version of the company HR app is available on the Play Store. Update when convenient, nothing changes in your data.",
    "bank_statement": "Your {bank} e-statement for October is ready. View it in the official mobile app or net banking. We never ask for your OTP or PIN.",
    "kyc_reminder_legit": "{bank}: your periodic KYC update is due. Please visit your home branch with ID proof, or update in the official app. Ignore if done.",
    "otp_login": "{o} is your one time password to log in to {bank} net banking. Valid for 5 minutes. Do not share it with anyone.",
    "refund_legit": "Refund of {s} for your cancelled order has been credited to your original payment method. No action needed.",
    "newsletter": "This week on the company blog: three lessons from our Q3 launch. Read more at {good}/blog",
    "family_call": "Mom, my phone battery is dying, I'll call you from Rohit's phone tonight. Reached {c} safely.",
}

SLOTS = dict(n=NAMES, r=ROLES, a=AMOUNTS, s=SMALL, app=APPS, m=MINUTES, ag=AGENCIES, c=CITIES,
             o=["482913", "771204", "093382", "560017"],
             bank=["SBI", "HDFC Bank", "ICICI Bank", "Axis Bank", "Kotak"],
             courier=["India Post", "Blue Dart", "Delhivery", "DTDC"],
             bad=["http://sbi-kyc-update.xyz", "bit.ly/3kYc9a", "https://indiapost-redelivery.top", "http://192.168.43.10",
                  "echallan-parivahan.cc", "https://hdfc-secure-login.online", "tinyurl.com/refund-it", "https://kyc-verify-now.live"],
             good=["https://www.flipkart.com/track", "https://docs.google.com/d/8f2", "https://meet.google.com/abc-defg-hij",
                   "https://www.acme.com/news", "https://www.amazon.in/orders"])


def fill(template, rng, k):
    keys = [s for s in SLOTS if "{" + s + "}" in template]
    combos = list(itertools.product(*[SLOTS[s] for s in keys])) or [()]
    rng.shuffle(combos)
    out = {template.format(**dict(zip(keys, c))) for c in combos[:k]}
    return list(out)


def build(per_template=40, seed=7):
    rng = random.Random(seed)
    rows = []
    for tid, t in SCAM.items():
        rows += [(text, 1, "scam:" + tid) for text in fill(t, rng, per_template)]
    for tid, t in BENIGN.items():
        rows += [(text, 0, "benign:" + tid) for text in fill(t, rng, per_template)]
    return rows


if __name__ == "__main__":
    rows = build()
    print(len(rows), "rows,", sum(r[1] for r in rows), "scam,", len({r[2] for r in rows}), "templates")
