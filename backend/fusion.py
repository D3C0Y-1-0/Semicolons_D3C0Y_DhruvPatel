"""Risk fusion: log-odds evidence x impact of the request + hard policy rules.

R = 100 * sigmoid(b + sum(w_i * logit(s_i))) * I, then rule floors.
Run `python fusion.py` to check the three worked examples from the plan.
"""
import math

from detectors.identity import inr

PRIOR = 0.05  # assumed share of flagged communications that are attacks
BIAS = math.log(PRIOR / (1 - PRIOR))  # -2.944

# Starting weights from the plan. Refit with logistic regression on labelled scenarios (eval/).
WEIGHTS = {
    "audio_spoof": 1.0,
    "voice_mismatch": 0.8,
    "face_video": 0.8,
    "face_mismatch": 0.6,
    "lip_sync": 0.5,
    "image_synthetic": 0.6,
    "image_univfd": 0.7,
    "message_tactics": 0.6,
    "message_classifier": 0.4,
    "context_anomaly": 1.0,
    "lookalike_domain": 0.7,
    "header_auth": 0.6,
    "bad_url": 1.2,
    "known_mule": 1.5,  # pays to or calls an account/number already caught in an attack
    "link_risk": 1.0,   # shortener, brand impersonation, .apk, bare IP, days-old domain
    "scam_pattern": 0.8,  # matches a known scam type (KYC, parcel, job, loan, lottery, sextortion...)
}

IMPACT = {
    "payment_high": 1.0,   # above approval limit, new beneficiary, gift cards, crypto
    "install_app": 0.9,    # APK or screen-sharing app: the attacker gets the whole phone
    "credentials": 0.8,    # passwords, OTP, PIN
    "payment": 0.7,        # within limit, known beneficiary
    "click_link": 0.7,     # phishing page: the usual first step to credentials or a payment
    "personal_info": 0.6,  # Aadhaar, PAN, selfie: loans and SIMs opened in your name
    "call_back": 0.5,      # "call this officer": moves you to a voice scam
    "information": 0.4,    # share internal docs or data
    "none": 0.2,           # greeting, update, social
}
RISKY = ("payment", "payment_high", "credentials", "install_app")

BANDS = [(60, "HIGH"), (30, "MEDIUM"), (0, "LOW")]
FLOOR = {"HIGH": 60, "MEDIUM": 30}


def logit(s):
    s = min(max(s, 1e-4), 1 - 1e-4)
    return math.log(s / (1 - s))


def band_of(r):
    return next(name for cut, name in BANDS if r >= cut)


def money_floor(amount):
    """The HIGH floor grows with the money at stake: 60 up to ₹10,000, 75 at ₹1 lakh, 90 from ₹10 lakh."""
    if not amount or amount <= 10_000:
        return FLOOR["HIGH"]
    return round(min(90.0, 60 + 15 * math.log10(amount / 10_000)), 1)


def rules(facts):
    """Hard policy floors. Each returns (rule text, floor value) when it fires."""
    fired = []
    risky_action = facts.get("action") in RISKY
    amount = facts.get("amount_inr") if facts.get("action") in ("payment", "payment_high") else None
    high = money_floor(amount)
    at_stake = f"; {inr(amount)} at stake sets the minimum to {high:g}" if high > FLOOR["HIGH"] else ""
    if risky_action and (facts.get("unregistered_channel") or facts.get("new_beneficiary")):
        fired.append(("Payment or credential request from an unregistered channel or to a new beneficiary" + at_stake, high))
    if facts.get("known_mule"):
        fired.append(("Names a bank account, UPI id or number already on the mule blocklist" + at_stake, high))
    if facts.get("bad_url"):
        fired.append(("Link on a known phishing or malware list", FLOOR["HIGH"]))
    elif facts.get("dangerous_link"):
        fired.append(("Link fakes a bank or brand, installs an app, hides behind an IP or is days old", FLOOR["HIGH"]))
    if facts.get("scam_strong"):
        fired.append(("Matches a known scam pattern and the wording, link or tactics back it up" + at_stake, high))
    elif facts.get("scam_pattern"):
        fired.append(("Matches a known scam pattern", FLOOR["MEDIUM"]))
    elif facts.get("scam_wording_ask"):
        fired.append(("Scam-like wording asking for money or a code: verify before acting", FLOOR["MEDIUM"]))
    if facts.get("digital_arrest"):
        fired.append(("'Digital arrest' pattern: claims to be police/CBI/court and demands payment or staying on call" + at_stake, high))
    if facts.get("audio_both_high"):
        fired.append(("Both audio models score the voice as synthetic (>= 0.9)", FLOOR["MEDIUM"]))
    if facts.get("voice_mismatch_enrolled"):
        fired.append(("Voice does not match the enrolled voiceprint of the claimed person", FLOOR["MEDIUM"]))
    return fired


def fuse(signals, action="none", facts=None):
    """signals: list of {signal, score, ...}. Missing modalities are simply absent (no penalty)."""
    facts = dict(facts or {}, action=action)
    rows, total = [], 0.0
    for s in signals:
        if s.get("score") is None:  # detector unavailable
            continue
        w = WEIGHTS.get(s["signal"], 0.5)
        c = w * logit(s["score"])
        total += c
        rows.append({**s, "weight": w, "contribution": round(c, 3)})

    t = 1 / (1 + math.exp(-(BIAS + total)))
    impact = IMPACT[action]
    risk = 100 * t * impact
    fired = rules(facts)
    for _, floor in fired:
        risk = max(risk, floor)

    rows.sort(key=lambda r: -abs(r["contribution"]))
    return {
        "risk": round(risk, 1),
        "band": band_of(risk),
        "threat_probability": round(t, 4),
        "impact": impact,
        "action": action,
        "prior_logodds": round(BIAS, 3),
        "signals": rows,
        "rules_fired": [r for r, _ in fired],
    }


def demo():
    sig = lambda name, s: {"signal": name, "score": s}
    # A: Arup-style fake CFO call + email asking for a wire
    a = fuse([sig("audio_spoof", .88), sig("voice_mismatch", .85), sig("face_video", .74),
              sig("message_tactics", .92), sig("context_anomaly", .90), sig("lookalike_domain", .95)],
             action="payment_high", facts={"unregistered_channel": True})
    assert a["risk"] == 99.9 and a["band"] == "HIGH", a
    # B: same fake, harmless birthday message
    b = fuse([sig("audio_spoof", .88), sig("voice_mismatch", .85), sig("face_video", .74),
              sig("message_tactics", .10)], action="none")
    assert b["risk"] == 9.8 and b["band"] == "LOW", b
    # C: perfect fake fools every detector; maths says 17.3, Rule 1 lifts to HIGH
    c_signals = [sig("audio_spoof", .30), sig("voice_mismatch", .20), sig("face_video", .40),
                 sig("message_tactics", .92), sig("context_anomaly", .90)]
    assert fuse(c_signals, action="payment_high")["risk"] == 17.3
    c = fuse(c_signals, action="payment_high", facts={"unregistered_channel": True, "new_beneficiary": True})
    assert c["risk"] == 60 and c["band"] == "HIGH" and c["rules_fired"], c
    # the floor grows with the money at stake
    ask = lambda amt: fuse([sig("message_tactics", .4)], action="payment_high", facts={"unregistered_channel": True, "amount_inr": amt})["risk"]
    assert (ask(10_000), ask(100_000), ask(1_000_000), ask(50_000_000)) == (60, 75, 90, 90), [ask(a) for a in (1e4, 1e5, 1e6, 5e7)]
    # not only money: a phishing link or a scam pattern is HIGH even with no amount
    assert fuse([sig("link_risk", .95)], "click_link", {"dangerous_link": True})["band"] == "HIGH"
    assert fuse([sig("scam_pattern", .85)], "none", {"scam_pattern": True})["risk"] == 30
    assert fuse([sig("scam_pattern", .85)], "call_back", {"scam_pattern": True, "scam_strong": True})["risk"] == 60
    assert fuse([sig("message_classifier", .82)], "payment", {"scam_wording_ask": True})["band"] == "MEDIUM"
    # unavailable detector is ignored, not penalised
    assert fuse([{"signal": "audio_spoof", "score": None}])["risk"] == fuse([])["risk"]
    print("fusion ok: A=99.9 HIGH, B=9.8 LOW, C=17.3 -> HIGH by rule")


if __name__ == "__main__":
    demo()
