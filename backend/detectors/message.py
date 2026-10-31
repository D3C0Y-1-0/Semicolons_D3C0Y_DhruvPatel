"""Message analysis: email headers, lookalike domains, URLs, manipulation tactics, request extraction.

Works offline with a bilingual lexicon (English, Hinglish, Hindi). If ANTHROPIC_API_KEY is set,
an LLM tags tactics instead and the lexicon becomes the fallback.
Run `python -m detectors.message` for the self-check.
"""
import email
import functools
import json
import os
import re
import unicodedata

# invisible characters scammers slip inside words ("O​T​P") so filters miss them
INVISIBLE = dict.fromkeys(map(ord, "​‌‍⁠﻿­᠎"), None)


def normalize(text):
    """Fold look-alike Unicode (𝐊𝐘𝐂, ｋｙｃ) to plain letters and drop invisible characters before any check."""
    return unicodedata.normalize("NFKC", text or "").translate(INVISIBLE)
from email import policy
from urllib.parse import urlparse

ORG_DOMAINS = [d.strip().lower() for d in os.getenv("ORG_DOMAINS", "acme.com").split(",") if d.strip()]

TACTICS = {
    "urgency": [r"\burgent(ly)?\b", r"\bimmediately\b", r"\basap\b", r"\bright now\b", r"\bwithin \d+ ?(min|mins|minutes|hours?|hrs?)\b",
                r"\btoday itself\b", r"\bjaldi\b", r"\bturant\b", r"\babhi ke abhi\b", r"तुरंत", r"जल्दी", r"अभी",
                r"\b(lost|forgot|left) my (wallet|purse|card|phone)\b", r"\bemergency\b", r"\bstuck (at|in)\b", r"\bin (big )?trouble\b"],
    "secrecy": [r"\bconfidential\b", r"\bdon'?t (tell|share|discuss)\b", r"\bkeep (this|it) (between us|quiet|private)\b",
                r"\bdo not (tell|discuss|share)\b", r"\bkisi(ko| ko) mat (batana|batao|bolna|bolo)\b", r"\bsecret\b", r"किसी को मत", r"गोपनीय"],
    "authority": [r"\b(ceo|cfo|coo|md|managing director|director|chairman|boss)\b", r"\bon behalf of\b", r"\bsir has asked\b",
                  r"\bmanagement has (asked|approved)\b"],
    "payment_request": [r"\b(wire|transfer|neft|rtgs|imps|upi|remit)\b", r"\bpayment\b", r"\binvoice\b", r"\bbeneficiary\b",
                        r"₹\s?[\d,]+", r"\brs\.?\s?[\d,]+", r"\binr\s?[\d,]+", r"\b\d+(\.\d+)?\s?(lakh|lac|crore|cr)\b",
                        r"\b[\d,]+(\.\d+)?\s?(rs|rupees?|rupay|rupaye|rupiya|bucks)\b", r"\b[\d,]+\s?/-", r"\b\d+(\.\d+)?\s?k\s?(rs|rupees?|inr)\b",
                        r"\bsend (me )?(some )?(money|cash|funds?|the amount)\b", r"\b(deposit|invest)\b", r"\b(lend|loan) me\b", r"\b(gpay|google pay|phone ?pe|paytm)\b",
                        r"\bpaise? (bhejo|transfer|chahiye|de do)\b", r"पैसे", r"भुगतान", r"\bgift ?cards?\b", r"\b(bitcoin|crypto|usdt)\b"],
    "credential_request": [r"\botp\b", r"\bpassword\b", r"\bpin\b", r"\blog ?in (details|credentials)\b", r"\bverify your account\b",
                           r"\b(anydesk|teamviewer|quick ?support|rustdesk)\b", r"\bremote access\b", r"\bcvv\b"],
    "channel_switch": [r"\bwhats ?app\b", r"\bpersonal (number|phone|email)\b", r"\bcall me on\b", r"\btelegram\b",
                       r"\bswitch to\b", r"\bnot on (email|teams)\b", r"\bnew number\b"],
    "new_beneficiary": [r"\bnew (account|vendor|supplier|payee|bank details|beneficiary)\b", r"\bnew \w+ account\b", r"\b(updated|changed) (bank|account) details\b",
                        r"\baccount (has )?changed\b"],
    "fear_threat": [r"\barrest(ed)?\b", r"\bdigital arrest\b", r"\b(cbi|ncb|ed|narcotics|customs|cyber cell)\b", r"\bpolice\b",
                    r"\bcourt\b", r"\bwarrant\b", r"\bmoney laundering\b", r"\bstay on (the )?(call|video)\b", r"\bdon'?t disconnect\b",
                    r"\bcyber ?crime\b", r"\b(drugs|narcotics|mdma)\b", r"\b(call|video call|video) pe (bane |bani )?raho\b", r"\bdisconnect mat\b",
                    r"गिरफ्तार", r"पुलिस"],
    "reward": [r"\b(prize|lottery|cashback|refund|reward|bonus)\b", r"\byou (have )?won\b"],
}
TACTIC_LABEL = {
    "urgency": "Urgency pressure", "secrecy": "Secrecy request", "authority": "Authority claim",
    "payment_request": "Payment request", "credential_request": "Credential or OTP request",
    "channel_switch": "Channel switch", "new_beneficiary": "New beneficiary", "fear_threat": "Fear or legal threat",
    "reward": "Reward bait",
}

HOMOGLYPHS = str.maketrans({"0": "o", "1": "l", "3": "e", "5": "s", "@": "a", "а": "a", "е": "e", "о": "o", "р": "p",
                            "с": "c", "х": "x", "і": "i"})
URL_RE = re.compile(r"https?://[^\s<>\"')]+|www\.[^\s<>\"')]+", re.I)
AMOUNT_RE = re.compile(r"(?:₹|rs\.?|inr)\s?([\d,]+(?:\.\d+)?)|([\d.]+)\s?(lakh|lac|crore|cr|k)\b"
                       r"|\b([\d,]+(?:\.\d+)?)\s?(?:rs\b|rupees?\b|rupay\b|rupaye\b|rupiya\b|bucks\b|inr\b|/-)", re.I)
UNIT = {"lakh": 1e5, "lac": 1e5, "crore": 1e7, "cr": 1e7, "k": 1e3}
# "I need 10000, can you send it" names an amount and asks for it without any banking word
ASK_RE = re.compile(r"\b(send|need|lend|loan|give|transfer|pay|borrow|bhej\w*|de ?do|chahiye|chaiye)\b", re.I)
# "Rs 85,000 has been credited" reports money, it doesn't ask for it
NOTICE_RE = re.compile(r"\b(has been|was|is|got) (credited|debited|received|refunded|deposited)\b", re.I)
# a bare number right after the ask ("need 10000 urgently") is an amount even without "rs"
BARE_ASK_RE = re.compile(r"\b(?:need|send|lend|loan|give|transfer|pay|borrow)\b\W+(?:\w+\W+){0,3}?(\d{1,3}(?:,\d{2,3})+|\d{3,9})\b"
                         r"(?=\s*(?:$|[^\w\s]|(?:urgently|urgent|asap|now|please|plz|pls|today|tonight|tomorrow|till|by|to|for|and|bro|yaar|immediately)\b))", re.I)  # not "500 copies"
BLOCKLIST = {l.strip().lower() for l in open(os.path.join(os.path.dirname(__file__), "url_blocklist.txt"), encoding="utf-8")
             if l.strip() and not l.startswith("#")} if os.path.exists(os.path.join(os.path.dirname(__file__), "url_blocklist.txt")) else set()

# --- Scam types: every pattern needs its topic AND its hook, so a genuine message on the same topic stays quiet ----
LINK_CUE = r"\b(click|tap|open|visit|link)\b|https?://|www\.|\.(ly|xyz|top|apk)\b"
PAY_CUE = r"\b(pay|fee|fees|charges?|deposit|transfer|upi|send|bhej\w*|paise?|paisa)\b|₹|\brs\.?\s?\d"
# "Do not share this OTP. Bank never asks for it" is the genuine notice, not the scam
SAFE_NOTICE = re.compile(r"\b(do not|don'?t|never)\s+(share|disclose)\s+(this|the|your|it)\b.{0,25}\b(otp|code|pin|password|anyone)\b"
                         r"|\b(bank|we|it|ibank) (will )?never asks?\b"
                         r"|\bshare (the |this |your )?(otp|code)\b.{0,30}\b(delivery (partner|agent|executive|boy)|at (your|the) door)", re.I)
SCAM_TYPES = {  # key: (label, topic, hook or None, what to do)
    "kyc_phishing": ("KYC / account-block phishing",
                     r"\b(kyc|pan|aadhaa?r|account|a/c|card|net ?banking|yono|wallet|mailbox|subscription|password)\b.{0,60}\b(block(ed)?|suspend(ed)?|deactivat\w*|expir\w*|frozen|freez\w*|band ho|delet\w*|disabled|terminated|restricted)|\b(update|complete|verify) (your )?(kyc|pan|aadhaa?r)\b",
                     LINK_CUE + r"|\botp\b|\bpassword\b|\bpin\b|\bcall\b",
                     "Banks never block accounts through SMS links. Open your bank's own app or visit the branch."),
    "bank_impersonation": ("Fake bank / fraud department",
                           r"\b(bank|fraud (department|team)|customer care|rbi|credit card (department|team))\b.{0,80}\b(otp|cvv|pin|card number|expiry)\b",
                           None, "Your bank will never ask for an OTP, CVV or PIN. Hang up and call the number on your card."),
    "delivery_customs": ("Fake parcel / customs fee",
                         r"\b(parcel|package|shipment|courier|consignment|india ?post|fedex|dhl|delivery)\b.{0,80}\b(held|on hold|seized|returned|failed|pending|stuck|undeliver\w*|incomplete|wrong address|outstanding|duty|release|could not be delivered|not delivered)",
                         PAY_CUE + "|" + LINK_CUE + r"|\baddress\b", "Couriers don't collect fees through random links. Check the tracking number on the courier's official site."),
    "utility_disconnect": ("Electricity / bill disconnection",
                           r"\b(electricity|power|bijli|gas|light)\b.{0,60}\b(disconnect\w*|cut|band|kat|suspend\w*)",
                           r"\bcall\b|\bofficer\b|\d{10}|" + LINK_CUE, "Power companies don't cut supply over SMS. Pay only in the official app or website."),
    "challan_refund": ("Fake e-challan / tax refund / reward points",
                       r"\be-?challan\b|\btraffic (fine|challan)\b|\b(income ?tax|it) refund\b|\breward points?\b|\bpoints? (will )?expir",
                       LINK_CUE + "|" + PAY_CUE, "Check challans only on parivahan.gov.in and refunds only on incometax.gov.in."),
    "lottery_prize": ("Lottery / prize bait",
                      r"\b(lottery|lucky draw|kbc|jackpot|lucky winner|prize money)\b|\byou (have )?won\b",
                      PAY_CUE + "|" + LINK_CUE + r"|\bclaim\b|\bcall\b|whats ?app", "You can't win a draw you never entered. Never pay to receive a prize."),
    "job_task": ("Task / part-time job scam",
                 r"\b(part[- ]?time|work from home|daily (income|earning)|earn (rs\.?|₹|inr)?\s?[\d,]+|like (youtube )?videos?|rate (hotels|products)|online tasks?|prepaid tasks?)\b",
                 PAY_CUE + r"|\btasks?\b|telegram|whats ?app|registration", "Real jobs never ask you to pay. 'Pay to unlock tasks' always ends in a loss."),
    "investment": ("Investment / trading scam",
                   r"\b(guaranteed|assured|fixed)\s+(\d+%\s+)?(returns?|profits?)\b|\bdouble (your )?money\b|\b(stock|trading|ipo|crypto|forex) (tips|group|signals?)\b|\b\d{2,3}%\s+(returns?|profits?)\b",
                   None, "No real investment guarantees returns. Check SEBI registration before investing anything."),
    "loan_app": ("Instant-loan app scam",
                 r"\b(instant|pre-?approved|quick|easy) (personal )?loan\b|\bloan\b.{0,40}\b(pre-?approved|approved|sanctioned|no cibil)\b",
                 PAY_CUE + "|" + LINK_CUE + r"|\bapp\b|\bapk\b", "RBI-registered lenders don't charge fees before paying out. Never install loan apps from links."),
    "malware_apk": ("Malicious app install",
                    r"\.apk\b|\b(download|install)\b.{0,30}\b(app|apk|application|update)\b", None,
                    "Never install apps from a link. Only use the Play Store or App Store."),
    "remote_access": ("Remote access / tech support",
                      r"\b(anydesk|teamviewer|quick ?support|rustdesk|airdroid)\b|\b(virus|hacked|compromised)\b.{0,60}\b(computer|phone|system|laptop)\b",
                      None, "Nobody genuine asks you to install a screen-sharing app. Hang up."),
    "refund_upi": ("Refund / 'sent by mistake' UPI trick",
                   r"\b(sent|transferred|credited|paid)\b[^.]{0,30}(₹|\brs\.?\s?\d|\b\d{3,}\b|\b(money|amount|gpay|upi|paytm|phonepe)\b)[^.]{0,30}\bby mistake\b|\b(refund|cashback|receive)\b.{0,60}\b(upi pin|pin daal\w*|enter (your )?pin|scan)\b|\bscan\b.{0,30}\bqr\b.{0,40}\b(receive|get|refund|claim)\b|upi://pay.{0,200}\b(receive|refund|claim|prize|won|cashback)\b",
                   None, "You never need a PIN or a QR scan to receive money. A PIN or scan only ever sends it."),
    "account_takeover": ("OTP / account takeover",
                         r"\b(mobile |phone )?number\b.{0,30}\b(will be |is being )?(disconnect\w*|deactivat\w*|blocked|suspended|band)\b.{0,80}\b(press \d|code|otp|kyc|call)\b|\b(sent|forwarded) (you )?(a |the |an )?(\d[- ]?digit )?(code|otp)\b.{0,40}\bmistake\b|\b(sim|esim)\b.{0,40}\b(block\w*|deactivat\w*|band|upgrade|swap)\b|\b(whatsapp|instagram|facebook|telegram) (verification |login )?code\b",
                         None, "Never forward a code you receive. It's the key to your account."),
    "sextortion": ("Sextortion",
                   r"\b(nude|intimate|private|obscene|video call|recordings?)\b.{0,80}\b(leak|viral|contacts|family|share|sent to)\b",
                   PAY_CUE + r"|\bcrypto\b|\bbitcoin\b", "Don't pay: paying brings more demands. Report at cybercrime.gov.in or call 1930."),
    "romance_gift": ("Romance / gift-parcel scam",
                     r"\b(gift|parcel|package)\b.{0,60}\b(for you|sent you|from (the )?(uk|usa|london|abroad))\b|\b(my love|darling|sweetheart|my dear)\b",
                     r"\bcustoms\b|\bclearance\b|" + PAY_CUE, "Never pay customs or fees for a gift from someone you met online."),
    "family_emergency": ("Family emergency / new number",
                         r"\b(mom|mum|mummy|mumma|dad|papa|maa)\b.{0,40}\bnew number\b|\b(son|daughter|beta|bete|beti|husband|brother|bhai)\b.{0,40}\b(arrested|accident|hospital|police station|jail|kidnap\w*)",
                         PAY_CUE + r"|\bbail\b|\bmoney\b", "Call the family member on their old, known number before sending anything."),
    "otp_ask": ("OTP / PIN / CVV request",
                r"\b(tell|share|send|give|read|forward|confirm|provide|bata\w*|bhej\w*)\b.{0,40}\b(otp|cvv|upi pin|atm pin|pin|password|card number|(verification |security |\d[- ]?digit )?code (you|that|which) (receive|got|get))\b"
                r"|\b(otp|cvv|pin|card number)\b.{0,30}\b(bata\w*|bhej\w*|share karo|de do|dijiye)\b",
                None, "Never tell anyone an OTP, PIN or CVV. No bank, telecom or police officer will ever ask for one."),
    "advance_fee": ("Pay-a-fee-to-receive scam",
                    r"\b(processing|registration|clearance|activation|delivery|release|gst|customs|insurance|verification|unlock|diplomat\w*|duty|correction|redelivery)\s+(\w+\s+)?(fee|fees|charges?|amount)\b",
                    r"\b(receive|claim|get|prize|won|winner|loan|release|refund|cashback|reward|unlock|car|job|parcel|gift|money|send you|savings|box|consignment|deliver\w*|order|address)\b",
                    "Nobody genuine makes you pay a fee to receive a prize, loan, refund or parcel."),
    "personal_data": ("Personal data harvesting",
                      r"\b(send|share|upload|provide|submit)\b.{0,30}\b(aadhaa?r|pan( card)?|passport|selfie|date of birth|dob|bank details|card details)\b",
                      None, "Don't send ID documents or selfies to anyone who contacted you first. They're used to open loans and SIMs in your name."),
}
SCAM_RX = {k: (re.compile(t, re.I | re.S), re.compile(h, re.I) if h else None) for k, (_, t, h, _) in SCAM_TYPES.items()}
CREDENTIAL_TYPES = {"bank_impersonation", "account_takeover", "kyc_phishing", "otp_ask"}


def scam_types(text):
    """[(key, label, advice)] for every scam pattern in the text."""
    safe = SAFE_NOTICE.search(text)
    out = []
    for k, (topic, hook) in SCAM_RX.items():
        if topic.search(text) and (hook is None or hook.search(text)) and not (safe and k in CREDENTIAL_TYPES):
            out.append({"type": k, "label": SCAM_TYPES[k][0], "advice": SCAM_TYPES[k][3]})
    return out


# --- Link intelligence -----------------------------------------------------------------------------------------
SHORTENERS = {"bit.ly", "bitly.com", "tinyurl.com", "t.co", "goo.gl", "is.gd", "cutt.ly", "rb.gy", "shorturl.at", "t.ly", "ow.ly",
              "tiny.cc", "rebrand.ly", "s.id", "v.gd", "shorte.st", "u.to", "clck.ru", "qr.ae", "bit.do"}
CHEAP_TLDS = {"xyz", "top", "click", "live", "buzz", "icu", "online", "site", "shop", "club", "rest", "sbs", "cfd", "cyou", "monster",
              "quest", "bond", "lol", "fun", "work", "link", "support", "help", "vip", "win", "loan", "gq", "tk", "ml", "ga", "cf", "cc", "pw"}
BRANDS = {  # name in a domain -> its real domains
    "sbi": ("sbi.co.in", "onlinesbi.sbi", "sbi.bank.in", "sbicard.com"), "hdfc": ("hdfcbank.com", "hdfc.com", "hdfcbank.bank.in"),
    "icici": ("icicibank.com", "icici.bank.in"), "axis": ("axisbank.com",), "kotak": ("kotak.com",), "pnb": ("pnbindia.in",),
    "paytm": ("paytm.com",), "phonepe": ("phonepe.com",), "gpay": ("pay.google.com",), "amazon": ("amazon.in", "amazon.com"),
    "flipkart": ("flipkart.com",), "indiapost": ("indiapost.gov.in",), "incometax": ("incometax.gov.in",), "uidai": ("uidai.gov.in",),
    "aadhaar": ("uidai.gov.in",), "epfo": ("epfindia.gov.in",), "npci": ("npci.org.in",), "parivahan": ("parivahan.gov.in",),
    "echallan": ("parivahan.gov.in",), "irctc": ("irctc.co.in",), "airtel": ("airtel.in",), "jio": ("jio.com",), "rbi": ("rbi.org.in",),
    "whatsapp": ("whatsapp.com",), "instagram": ("instagram.com",), "facebook": ("facebook.com",), "dhl": ("dhl.com", "dhl.co.in"),
    "fedex": ("fedex.com",), "bluedart": ("bluedart.com",), "delhivery": ("delhivery.com",), "microsoft": ("microsoft.com", "live.com"),
    "apple": ("apple.com",), "icloud": ("icloud.com",), "google": ("google.com",), "tatapower": ("tatapower.com",), "netflix": ("netflix.com",), "bescom": ("bescom.co.in",),
}
STRONG_LINK = 0.85  # at or above: the link alone makes the message HIGH


def reg_domain(host):
    parts = host.lower().strip(".").split(".")
    n = 3 if len(parts) >= 3 and len(parts[-1]) == 2 and parts[-2] in ("co", "gov", "org", "net", "ac", "nic", "edu", "res", "bank", "com") else 2
    return ".".join(parts[-n:])


def _is(host, dom):
    return host == dom or host.endswith("." + dom)


@functools.lru_cache(maxsize=512)
def expand_short(url):
    """One redirect hop of a short link, without visiting where it lands. None if offline or no redirect."""
    import urllib.error
    import urllib.request

    class Stop(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None
    try:
        urllib.request.build_opener(Stop).open(urllib.request.Request(url, method="HEAD", headers={"User-Agent": "TrustCheck"}), timeout=3)
    except urllib.error.HTTPError as e:
        return e.headers.get("Location")
    except Exception:
        return None
    return None


@functools.lru_cache(maxsize=512)
def domain_age_days(dom):
    """Days since registration via RDAP (free, no key). None if unknown or offline."""
    import datetime as dt
    import urllib.request
    try:
        req = urllib.request.Request(f"https://rdap.org/domain/{dom}", headers={"Accept": "application/rdap+json", "User-Agent": "TrustCheck"})
        data = json.load(urllib.request.urlopen(req, timeout=4))
        when = next(e["eventDate"] for e in data.get("events", []) if e.get("eventAction") == "registration")
        return (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(when.replace("Z", "+00:00"))).days
    except Exception:
        return None


def link_risk(url, online=None):
    """(score 0..1, reasons, final url). Each reason is plain words for the verdict."""
    online = os.getenv("LINK_LOOKUPS", "1") != "0" if online is None else online
    full = url if url.lower().startswith("http") else "http://" + url
    p = urlparse(full)
    host = (p.hostname or "").lower()
    found, final = [], url
    if online and reg_domain(host) in SHORTENERS:
        target = expand_short(full)
        if target:
            final, tp = target, urlparse(target)
            found.append((0.4, f"short link hides the real address: {tp.hostname}"))
            host, p = (tp.hostname or "").lower(), tp
    if reg_domain(host) in SHORTENERS:
        found.append((0.55, "short link hides where it really goes"))
    dom = reg_domain(host)
    if host in BLOCKLIST or dom in BLOCKLIST or safe_browsing_bad(final):
        found.append((0.97, "on a known phishing or malware list"))
    if p.path.lower().endswith(".apk"):
        found.append((0.95, "downloads an Android app (.apk) from outside the Play Store"))
    if re.fullmatch(r"[\d.]+", host):
        found.append((0.85, "points to a bare IP address, not a named website"))
    if "xn--" in host:
        found.append((0.9, "uses look-alike foreign letters in the address (punycode)"))
    if "@" in (p.netloc or ""):
        found.append((0.8, "hides the real address behind an @ sign"))
    for brand, real in BRANDS.items():
        if re.search(rf"(^|[.\-]){brand}", host) and not any(_is(host, r) for r in real):
            found.append((0.92, f"uses the name {brand.upper()} but isn't its real site ({real[0]})"))
            break
    org = lookalike_of(host)
    if org:
        found.append((0.9, f"imitates your company domain {org}"))
    if not any(_is(host, r) for real in BRANDS.values() for r in real) and re.search(
            r"(login|signin|verify|verification|secure|update|kyc|billing|appeal|unlock|refund|reward|redeem|support|helpdesk|wallet|pay)", dom.split(".")[0]):
        found.append((0.6, "address uses bait words like 'login', 'verify' or 'kyc'"))
    if host.rsplit(".", 1)[-1] in CHEAP_TLDS:
        found.append((0.7, f"uses a throwaway .{host.rsplit('.', 1)[-1]} address favoured by scam sites"))
    official = any(_is(host, r) for real in BRANDS.values() for r in real) or any(_is(host, o) for o in ORG_DOMAINS)
    if online and not official and dom not in SHORTENERS:
        age = domain_age_days(dom)
        if age is not None and age < 180:
            found.append((0.9 if age < 30 else 0.7, f"website was registered only {age} days ago"))
    if not found:
        return None, [], final
    s = 1.0
    for x, _ in found:
        s *= 1 - x
    return round(min(0.99, 1 - s), 3), [r for _, r in found], final


def levenshtein(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def lookalike_of(domain):
    """Return the org domain this one imitates, or None. acrne.com -> acme.com, acme-payments.co -> acme.com."""
    d = (domain or "").lower().strip(".")
    if not d or d in ORG_DOMAINS or any(d.endswith("." + o) for o in ORG_DOMAINS):
        return None
    norm = d.translate(HOMOGLYPHS).replace("rn", "m").replace("vv", "w")
    for org in ORG_DOMAINS:
        base = org.split(".")[0]
        if norm == org or levenshtein(d, org) <= 2 or (len(base) > 3 and base in d.split(".")[0]):
            return org
    return None


def parse_eml(raw):
    msg = email.message_from_bytes(raw, policy=policy.default)
    body = msg.get_body(preferencelist=("plain", "html"))
    text = body.get_content() if body else ""
    if body and body.get_content_type() == "text/html":
        text = re.sub(r"<[^>]+>", " ", text)
    return {
        "from": str(msg.get("From", "")), "reply_to": str(msg.get("Reply-To", "")),
        "subject": str(msg.get("Subject", "")), "auth": str(msg.get("Authentication-Results", "")),
        "body": text,
    }


def _addr(header):
    name, addr = email.utils.parseaddr(header or "")
    return name, addr.lower(), addr.split("@")[-1].lower() if "@" in addr else ""


def header_checks(hdr):
    signals, facts = [], {}
    name, addr, dom = _addr(hdr["from"])
    _, rto, rdom = _addr(hdr["reply_to"])
    ev = []
    fails = re.findall(r"\b(spf|dkim|dmarc)=(fail|softfail|none)\b", hdr["auth"], re.I)
    for mech, res in fails:
        ev.append({"type": "header", "field": "Authentication-Results", "text": f"{mech.upper()}={res}"})
    if rto and rdom != dom:
        ev.append({"type": "header", "field": "Reply-To", "text": f"Replies go to {rto}, not {addr}"})
    if name and "@" in name and name.lower() != addr:
        ev.append({"type": "header", "field": "From", "text": f"Display name shows {name} but address is {addr}"})
    if ev:
        signals.append({"signal": "header_auth", "label": "Email header problems", "score": min(0.95, 0.55 + 0.15 * len(ev)),
                        "why": "the email failed sender checks", "evidence": ev})
    org = lookalike_of(dom)
    if org:
        signals.append({"signal": "lookalike_domain", "label": "Lookalike sender domain", "score": 0.95,
                        "why": f"sender domain {dom} imitates {org}",
                        "evidence": [{"type": "header", "field": "From", "text": f"{dom} looks like {org}"}]})
    facts["sender_email"], facts["sender_domain"] = addr, dom
    return signals, facts


URL_RE_BARE = re.compile(r"\b(?:[a-z0-9-]+\.)+(?:xyz|top|click|live|buzz|icu|online|site|shop|club|in|com|ly|gl|gd|at|co|me|info|net|org|apk)(?:/[^\s<>\"')]*)?", re.I)


def find_urls(text):
    """http(s) and www links, plus bare ones like 'sbi-kyc.xyz/login' that SMS scams use."""
    urls = [u.rstrip(".,;:!?") for u in URL_RE.findall(text or "")]
    rest = re.sub(r"\S+@\S+", " ", URL_RE.sub(" ", text or ""))  # emails and UPI ids aren't links
    urls += [u.rstrip(".,;:!?") for u in URL_RE_BARE.findall(rest) if not re.fullmatch(r"[\d.]+", u) and "@" not in u]
    return list(dict.fromkeys(urls))


def url_checks(text):
    signals, facts, ev, worst = [], {}, [], 0.0
    urls = find_urls(text)
    for url in urls:
        score, reasons, final = link_risk(url)
        if not score:
            continue
        worst = max(worst, score)
        if any("phishing or malware list" in r for r in reasons):
            facts["bad_url"] = True
        ev.append({"type": "url", "text": url, "verdict": "; ".join(reasons), **({"final": final} if final != url else {})})
    facts["has_link"] = bool(urls)
    if ev:
        facts["dangerous_link"] = worst >= STRONG_LINK
        signals.append({"signal": "link_risk", "label": "Link check", "score": worst,
                        "why": f"link {ev[0]['text']} {ev[0]['verdict']}", "evidence": ev})
    return signals, facts


def safe_browsing_bad(url):
    key = os.getenv("GOOGLE_SAFE_BROWSING_KEY")
    if not key:
        return False
    import urllib.request
    body = json.dumps({"client": {"clientId": "trustcheck", "clientVersion": "1"},
                       "threatInfo": {"threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE"],
                                      "platformTypes": ["ANY_PLATFORM"], "threatEntryTypes": ["URL"],
                                      "threatEntries": [{"url": url}]}}).encode()
    try:
        req = urllib.request.Request(f"https://safebrowsing.googleapis.com/v4/threatMatches:find?key={key}", body,
                                     {"Content-Type": "application/json"})
        return bool(json.load(urllib.request.urlopen(req, timeout=5)).get("matches"))
    except Exception:
        return False


def lexicon_tactics(text):
    spans = []
    for tactic, pats in TACTICS.items():
        for p in pats:
            for m in re.finditer(p, text, re.I):
                spans.append({"type": "span", "tactic": tactic, "start": m.start(), "end": m.end(), "text": m.group(0)})
    return spans


LLM_PROMPT = """You are a fraud analyst. Find social-engineering manipulation in the message below (it may be English, Hindi or Hinglish).
Return ONLY JSON: {"tactics":[{"tactic":one of %s,"quote":"exact substring from the message"}],
"action":"payment"|"credentials"|"install_app"|"personal_info"|"click_link"|"call_back"|"information"|"none","amount_inr":number or null,"new_beneficiary":bool,"digital_arrest":bool}
Message:
<<<%s>>>"""


def llm_tactics(text):
    """Returns (spans, extras) or None if no key / any failure (caller falls back to lexicon)."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        return None
    try:
        import anthropic
        msg = anthropic.Anthropic().messages.create(
            model=os.getenv("LLM_MODEL", "claude-sonnet-5-5"), max_tokens=800,
            messages=[{"role": "user", "content": LLM_PROMPT % (list(TACTICS), text[:6000])}])
        data = json.loads(re.search(r"\{.*\}", msg.content[0].text, re.S).group(0))
        spans = []
        for t in data.get("tactics", []):
            i = text.find(t.get("quote", ""))
            if t.get("tactic") in TACTICS and i >= 0 and t["quote"]:
                spans.append({"type": "span", "tactic": t["tactic"], "start": i, "end": i + len(t["quote"]), "text": t["quote"]})
        return spans, data
    except Exception:
        return None


CLF_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models", "message_clf.joblib")


@functools.cache
def _clf():
    try:
        import joblib
        return joblib.load(CLF_PATH)
    except Exception:  # missing or trained with another sklearn version: run train/train_message_clf.py
        return None


def classifier_prob(text):
    m = _clf()
    return float(m.predict_proba([text[:4000]])[0, 1]) if m is not None and text.strip() else None


def parse_amount(text):
    best = None
    for m in AMOUNT_RE.finditer(text):
        try:
            if m.group(1) or m.group(4):
                v = float((m.group(1) or m.group(4)).replace(",", ""))
            else:
                v = float(m.group(2)) * UNIT[m.group(3).lower()]
        except ValueError:  # e.g. a stray "." matched as a number
            continue
        best = max(best or 0, v)
    if best is None:
        bare = [float(m.group(1).replace(",", "")) for m in BARE_ASK_RE.finditer(text)]
        best = max([v for v in bare if v >= 100], default=None)
    return best


def analyze(text="", eml_bytes=None, approval_limit=None):
    """Returns (signals, facts, info) where info has highlights for the UI."""
    signals, facts, header = [], {}, None
    if eml_bytes:
        header = parse_eml(eml_bytes)
        s, f = header_checks(header)
        signals += s
        facts |= f
        text = "\n".join(x for x in (header["subject"], header["body"], text) if x)
    text = normalize(text)
    if not text.strip():
        return signals, facts, {"text": "", "highlights": [], "header": header}

    s, f = url_checks(text)
    signals += s
    facts |= f

    llm = llm_tactics(text)
    spans, extras = llm if llm else (lexicon_tactics(text), {})
    ask = ASK_RE.search(text)
    if ask and parse_amount(text) and not any(sp["tactic"] == "payment_request" for sp in spans):
        spans.append({"type": "span", "tactic": "payment_request", "start": ask.start(), "end": ask.end(), "text": ask.group(0)})
    found = sorted({sp["tactic"] for sp in spans})
    k = len(found)
    score = 0.1 if k == 0 else min(0.97, 1 - 0.6 ** k)  # 1 tactic=0.40, 2=0.64, 3=0.78, 5=0.92
    signals.append({"signal": "message_tactics", "label": "Manipulation tactics", "score": round(score, 3),
                    "why": ("message uses " + ", ".join(TACTIC_LABEL[t].lower() for t in found)) if found else "no manipulation tactics found",
                    "evidence": spans, "source": "llm" if llm else "lexicon"})
    p = classifier_prob(text)
    if p is not None:
        signals.append({"signal": "message_classifier", "label": "Scam-language classifier", "score": round(p, 3),
                        "why": f"wording {'resembles' if p >= .5 else 'does not resemble'} known scam messages (p {p:.2f})",
                        "evidence": [{"type": "metric", "text": "trained on SMS Spam Collection + bilingual Indian scam corpus; see eval/message_clf_report.md"}]})

    amount = extras.get("amount_inr") or parse_amount(text)
    new_ben = extras.get("new_beneficiary") or "new_beneficiary" in found
    gift = re.search(r"gift ?cards?|bitcoin|crypto|usdt", text, re.I)
    types = scam_types(text)
    kinds = {t["type"] for t in types}
    digital_arrest = bool(extras.get("digital_arrest")) or ("fear_threat" in found and (
        "payment_request" in found or re.search(r"stay on|don'?t disconnect", text, re.I)))
    if digital_arrest:
        types.insert(0, {"type": "digital_arrest", "label": "Digital arrest / fake police",
                         "advice": "Real police, CBI or courts never arrest anyone over a video call. Hang up and call 1930."})
    if (sum(t in found for t in ("authority", "urgency", "secrecy", "new_beneficiary", "channel_switch")) >= 2 and "payment_request" in found) or gift:
        types.insert(0, {"type": "ceo_fraud", "label": "Impersonation money ask (boss, friend, relative)", "advice": "Call the person back on a number you already know before moving any money."})
    paying = bool(kinds & {"investment", "lottery_prize", "sextortion", "advance_fee"}) or ("payment_request" in found and not (NOTICE_RE.search(text) and not ASK_RE.search(text))) or extras.get("action") == "payment"
    asks_link = facts.get("has_link") and (re.search(LINK_CUE, text, re.I) or types or found)
    if kinds & {"malware_apk", "remote_access"} or extras.get("action") == "install_app":
        action = "install_app"
    elif "refund_upi" not in kinds and (extras.get("action") == "credentials" or kinds & {"account_takeover", "bank_impersonation", "otp_ask"} or (
            "credential_request" in found and (not SAFE_NOTICE.search(text) or kinds & CREDENTIAL_TYPES))):
        action = "credentials"
    elif paying or "refund_upi" in kinds:
        over = amount is not None and approval_limit is not None and amount > approval_limit
        action = "payment_high" if (over or new_ben or gift or kinds & {"investment", "job_task", "lottery_prize", "refund_upi"}) else "payment"
    elif "personal_data" in kinds or extras.get("action") == "personal_info":
        action = "personal_info"
    elif asks_link or extras.get("action") == "click_link":
        action = "click_link"
    elif re.search(r"\bcall\b.{0,30}(\+?\d[\d -]{8,}\d|officer|helpline|us|immediately|back)|\b(press|dial) \d\b", text, re.I) and (types or found):
        action = "call_back"
    elif extras.get("action") == "information" or re.search(r"\b(send|share|forward) (me )?(the )?(file|data|list|document|report|details)", text, re.I):
        action = "information"
    else:
        action = "none"

    if types:
        signals.append({"signal": "scam_pattern", "label": "Known scam pattern", "score": 0.93 if len(types) > 1 else 0.85,
                        "why": "matches the " + " and ".join(t["label"].lower() for t in types[:2]) + " pattern",
                        "evidence": [{"type": "pattern", "text": f"{t['label']}: {t['advice']}"} for t in types]})
    facts |= {"action": action, "amount_inr": amount, "new_beneficiary": bool(new_ben),
              "channel_switch": "channel_switch" in found, "digital_arrest": digital_arrest,
              "scam_pattern": bool(types),
              # a pattern backed by scam wording, a risky link or two manipulation tactics is no longer a maybe
              "scam_strong": bool(types) and ((p or 0) >= 0.6 or len(found) >= 2 or any(
                  x["signal"] == "link_risk" and x["score"] >= 0.6 for x in signals))}
    return signals, facts, {"text": text, "highlights": spans, "tactics": found, "header": header, "scam_types": types}


def demo():
    ceo = ("From CFO Rajesh: This is urgent and confidential. Transfer ₹45,00,000 to our new vendor account "
           "within 30 minutes. Don't discuss with anyone, message me on WhatsApp.")
    s, f, info = analyze(ceo, approval_limit=1_000_000)
    t = next(x for x in s if x["signal"] == "message_tactics")
    assert {"urgency", "secrecy", "payment_request", "new_beneficiary", "channel_switch"} <= set(info["tactics"]), info["tactics"]
    assert t["score"] > 0.9 and f["action"] == "payment_high" and f["amount_inr"] == 4_500_000, (t, f)

    # informal asks with no banking words still ask for money
    for ask in ("i need 10000 rs urgently i lost my wallet can u plz send me", "bro need 10k urgently, gpay kar do"):
        assert analyze(ask, approval_limit=0)[1]["action"] == "payment_high", ask
    for ok in ("We need 500 copies of the brochure for the event.", "Your salary of Rs 85,000 has been credited."):
        assert analyze(ok)[1]["action"] == "none", ok

    benign = "Happy birthday team! Cake in the pantry at 4."
    s, f, _ = analyze(benign)
    assert f["action"] == "none" and next(x for x in s if x["signal"] == "message_tactics")["score"] == 0.1

    arrest = "Main CBI officer bol raha hoon. Aapke naam pe money laundering case hai. Video call pe raho, disconnect mat karna, warna arrest. Turant 2 lakh UPI karo."
    _, f, _ = analyze(arrest)
    assert f["digital_arrest"] and f["amount_inr"] == 200000, f

    eml = (b"From: \"Rajesh Kumar\" <rajesh@acrne.com>\r\nReply-To: pay@gmail.com\r\nSubject: Urgent wire\r\n"
           b"Authentication-Results: mx.acme.com; spf=fail; dkim=none; dmarc=fail\r\n\r\nPlease wire the funds today.")
    s, f, _ = analyze(eml_bytes=eml)
    names = {x["signal"] for x in s}
    assert {"lookalike_domain", "header_auth"} <= names and f["sender_domain"] == "acrne.com", s
    assert lookalike_of("acme-payments.co") == "acme.com" and lookalike_of("acme.com") is None and lookalike_of("google.com") is None
    # every scam type, not only money: (message, expected type, expected action)
    os.environ["LINK_LOOKUPS"] = "0"  # offline: no RDAP or short-link lookups in the self-check
    scams = [
        ("Dear customer your SBI account will be blocked today. Update KYC at http://sbi-kyc-update.xyz/login", "kyc_phishing", "click_link"),
        ("Your India Post parcel is on hold due to incomplete address. Update within 12 hrs: indiapost-redelivery.top/in", "delivery_customs", "click_link"),
        ("Dear consumer your electricity will be disconnected tonight at 9.30 pm. Call officer 9876500011 immediately.", "utility_disconnect", "call_back"),
        ("Congratulations! You have won Rs 25,00,000 in KBC lucky draw. Pay Rs 12,500 processing fee to claim.", "lottery_prize", "payment_high"),
        ("Part time job: earn Rs 3000 daily by liking YouTube videos. Join our Telegram for tasks.", "job_task", "payment_high"),
        ("Guaranteed 40% returns in 30 days! Join our stock tips WhatsApp group, deposit 10000 today.", "investment", "payment_high"),
        ("Pre-approved instant loan of Rs 5 lakh. Download our app: https://cashnow-loans.in/app.apk", "malware_apk", "install_app"),
        ("Hello sir, Microsoft here, your computer has virus. Install AnyDesk and give me the code.", "remote_access", "install_app"),
        ("I sent Rs 5000 to you by mistake, please return. Scan this QR to receive the refund and enter UPI PIN.", "refund_upi", "payment_high"),
        ("Hi, I sent you a 6 digit code by mistake, can you please forward it to me?", "account_takeover", "credentials"),
        ("We have recordings of your video call. Pay Rs 50,000 or it will be sent to all your contacts.", "sextortion", "payment_high"),
        ("Hi mom this is my new number, phone broke. Need Rs 20,000 urgently for a bill, can you send?", "family_emergency", "payment"),
        ("Your traffic e-challan of Rs 500 is pending. Pay now at echallan-parivahan.cc to avoid court.", "challan_refund", "payment"),
        ("For the job offer please send your Aadhaar card, PAN card and a selfie on this number.", "personal_data", "personal_info"),
    ]
    for text, kind, act in scams:
        _, f, info = analyze(text, approval_limit=0 if act == "payment_high" else None)
        assert kind in {t["type"] for t in info["scam_types"]}, (kind, info["scam_types"], text)
        assert act == "none" or f["action"] == act, (act, f["action"], text)
    for ok in ("482913 is your OTP for Rs 499 at Swiggy. Do not share this OTP with anyone. - HDFC Bank",
               "Your Flipkart order will be delivered today between 2 pm and 6 pm. Track at https://www.flipkart.com/orders",
               "Reminder: your electricity bill of Rs 1,240 is due on 15 Nov. Pay via the official app. Ignore if already paid.",
               "My son had a small accident at school, I'll be working from home today.",
               "Slides for tomorrow are at https://docs.google.com/presentation/d/abc"):
        _, f, info = analyze(ok)
        assert not info["scam_types"] and not f.get("dangerous_link"), (ok, info["scam_types"], f)
    s, f, _ = analyze("Update KYC: http://sbi-kyc-update.xyz/login")
    assert f["dangerous_link"] and next(x for x in s if x["signal"] == "link_risk")["score"] >= STRONG_LINK
    assert link_risk("https://www.onlinesbi.sbi/", online=False)[0] is None and link_risk("http://192.168.4.20/pay", online=False)[0] >= .85
    assert find_urls("mail rajesh@acme.com or pay rajesh.vendor@okhdfcbank, see bit.ly/x9") == ["bit.ly/x9"], find_urls("mail rajesh@acme.com or pay rajesh.vendor@okhdfcbank, see bit.ly/x9")
    if _clf() is not None:
        assert classifier_prob(ceo) > 0.9 and classifier_prob(benign) < 0.5
    print("message ok", "(with trained classifier)" if _clf() is not None else "(classifier not trained yet)")


if __name__ == "__main__":
    demo()
