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
from email import policy
from urllib.parse import urlparse

ORG_DOMAINS = [d.strip().lower() for d in os.getenv("ORG_DOMAINS", "acme.com").split(",") if d.strip()]

TACTICS = {
    "urgency": [r"\burgent(ly)?\b", r"\bimmediately\b", r"\basap\b", r"\bright now\b", r"\bwithin \d+ ?(min|mins|minutes|hours?|hrs?)\b",
                r"\btoday itself\b", r"\bjaldi\b", r"\bturant\b", r"\babhi ke abhi\b", r"तुरंत", r"जल्दी", r"अभी",
                r"\b(lost|forgot|left) my (wallet|purse|card|phone)\b", r"\bemergency\b", r"\bstuck (at|in)\b", r"\bin (big )?trouble\b"],
    "secrecy": [r"\bconfidential\b", r"\bdon'?t (tell|share|discuss)\b", r"\bkeep (this|it) (between us|quiet|private)\b",
                r"\bdo not (tell|discuss|share)\b", r"\bkisi(ko| ko) mat batana\b", r"\bsecret\b", r"किसी को मत", r"गोपनीय"],
    "authority": [r"\b(ceo|cfo|coo|md|managing director|director|chairman|boss)\b", r"\bon behalf of\b", r"\bsir has asked\b",
                  r"\bmanagement has (asked|approved)\b"],
    "payment_request": [r"\b(wire|transfer|neft|rtgs|imps|upi|remit)\b", r"\bpayment\b", r"\binvoice\b", r"\bbeneficiary\b",
                        r"₹\s?[\d,]+", r"\brs\.?\s?[\d,]+", r"\binr\s?[\d,]+", r"\b\d+(\.\d+)?\s?(lakh|lac|crore|cr)\b",
                        r"\b[\d,]+(\.\d+)?\s?(rs|rupees?|rupay|rupaye|rupiya|bucks)\b", r"\b[\d,]+\s?/-", r"\b\d+(\.\d+)?\s?k\s?(rs|rupees?|inr)\b",
                        r"\bsend (me )?(some )?(money|cash|funds?|the amount)\b", r"\b(lend|loan) me\b", r"\b(gpay|google pay|phone ?pe|paytm)\b",
                        r"\bpaise? (bhejo|transfer|chahiye|de do)\b", r"पैसे", r"भुगतान", r"\bgift ?cards?\b", r"\b(bitcoin|crypto|usdt)\b"],
    "credential_request": [r"\botp\b", r"\bpassword\b", r"\bpin\b", r"\blog ?in (details|credentials)\b", r"\bverify your account\b",
                           r"\b(anydesk|teamviewer|quick ?support|rustdesk)\b", r"\bremote access\b", r"\bcvv\b"],
    "channel_switch": [r"\bwhats ?app\b", r"\bpersonal (number|phone|email)\b", r"\bcall me on\b", r"\btelegram\b",
                       r"\bswitch to\b", r"\bnot on (email|teams)\b", r"\bnew number\b"],
    "new_beneficiary": [r"\bnew (account|vendor|bank details|beneficiary)\b", r"\b(updated|changed) (bank|account) details\b",
                        r"\baccount (has )?changed\b"],
    "fear_threat": [r"\barrest(ed)?\b", r"\bdigital arrest\b", r"\b(cbi|ncb|ed|narcotics|customs|cyber cell)\b", r"\bpolice\b",
                    r"\bcourt\b", r"\bwarrant\b", r"\bmoney laundering\b", r"\bstay on (the )?(call|video)\b", r"\bdon'?t disconnect\b",
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


def url_checks(text):
    signals, facts, ev = [], {}, []
    for url in URL_RE.findall(text or ""):
        host = urlparse(url if url.startswith("http") else "http://" + url).hostname or ""
        if host in BLOCKLIST or safe_browsing_bad(url):
            facts["bad_url"] = True
            ev.append({"type": "url", "text": url, "verdict": "known bad"})
        elif lookalike_of(host):
            ev.append({"type": "url", "text": url, "verdict": f"imitates {lookalike_of(host)}"})
    if facts.get("bad_url"):
        signals.append({"signal": "bad_url", "label": "Known malicious link", "score": 0.97, "why": "a link is on a phishing list", "evidence": ev})
    elif ev:
        signals.append({"signal": "lookalike_domain", "label": "Lookalike link", "score": 0.9, "why": "a link imitates your domain", "evidence": ev})
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
"action":"payment"|"credentials"|"information"|"none","amount_inr":number or null,"new_beneficiary":bool,"digital_arrest":bool}
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
    if "credential_request" in found or extras.get("action") == "credentials":
        action = "credentials"
    elif ("payment_request" in found and not (NOTICE_RE.search(text) and not ASK_RE.search(text))) or extras.get("action") == "payment":
        over = amount is not None and approval_limit is not None and amount > approval_limit
        action = "payment_high" if (over or new_ben or gift) else "payment"
    elif extras.get("action") == "information" or re.search(r"\b(send|share|forward) (me )?(the )?(file|data|list|document|report|details)", text, re.I):
        action = "information"
    else:
        action = "none"

    facts |= {"action": action, "amount_inr": amount, "new_beneficiary": bool(new_ben),
              "channel_switch": "channel_switch" in found,
              "digital_arrest": bool(extras.get("digital_arrest")) or ("fear_threat" in found and (
                  "payment_request" in found or re.search(r"stay on|don'?t disconnect", text, re.I)))}
    return signals, facts, {"text": text, "highlights": spans, "tactics": found, "header": header}


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
    if _clf() is not None:
        assert classifier_prob(ceo) > 0.9 and classifier_prob(benign) < 0.5
    print("message ok", "(with trained classifier)" if _clf() is not None else "(classifier not trained yet)")


if __name__ == "__main__":
    demo()
