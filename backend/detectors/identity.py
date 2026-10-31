"""Org Trust Graph checks: does this request fit the claimed person's channels, hours, limits and biometrics?"""
import math
import os

VOICE_THRESHOLD = float(os.getenv("VOICE_THRESHOLD", "0.40"))  # ponytail: tune on your own enrolled pairs (eval/)
FACE_THRESHOLD = float(os.getenv("FACE_THRESHOLD", "0.40"))


def inr(n):
    """45,00,000 style grouping."""
    s = f"{int(round(n))}"
    head, tail = s[:-3], s[-3:]
    while len(head) > 2:
        tail, head = head[-2:] + "," + tail, head[:-2]
    return "₹" + (head + "," + tail if head else tail)


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def mismatch_score(sim, threshold):
    """Map similarity to P(not the same person): 0.5 at threshold, steep around it."""
    return round(1 / (1 + math.exp(15 * (sim - threshold))), 3)


def biometric_signals(person, voice_emb=None, face_emb=None):
    out, facts = [], {}
    if not person:
        return out, facts
    if voice_emb and person.get("voice_emb"):
        sim = cosine(voice_emb, person["voice_emb"])
        s = mismatch_score(sim, VOICE_THRESHOLD)
        out.append({"signal": "voice_mismatch", "label": "Voiceprint vs enrolled", "score": s,
                    "why": f"voice {'does not match' if s >= .5 else 'matches'} {person['name']}'s voiceprint ({sim:.2f} vs {VOICE_THRESHOLD:.2f})",
                    "evidence": [{"type": "metric", "text": f"cosine similarity {sim:.2f}, threshold {VOICE_THRESHOLD:.2f}"}]})
        facts["voice_mismatch_enrolled"] = s >= 0.5
    if face_emb and person.get("face_emb"):
        sim = cosine(face_emb, person["face_emb"])
        s = mismatch_score(sim, FACE_THRESHOLD)
        out.append({"signal": "face_mismatch", "label": "Face vs enrolled", "score": s,
                    "why": f"face {'does not match' if s >= .5 else 'matches'} {person['name']}'s enrolled photo ({sim:.2f})",
                    "evidence": [{"type": "metric", "text": f"cosine similarity {sim:.2f}, threshold {FACE_THRESHOLD:.2f}"}]})
    return out, facts


def context_signal(person, channel=None, sender=None, hour=None, action="none", amount=None):
    """Behaviour baseline checks. Each failed check is one evidence line in plain words."""
    if not person:
        return [], {}
    checks = []  # (probability this alone indicates an attack, plain-words reason)
    channels = [c.lower() for c in (person.get("channels") or [])]
    facts = {}
    if channel and channels and channel.lower() not in channels:
        checks.append((0.5, f"{person['name']} has never used {channel} for work (registered: {', '.join(channels)})"))
        facts["unregistered_channel"] = True
    if sender and person.get("email") and "@" in sender and sender.lower() != person["email"].lower():
        checks.append((0.6, f"sent from {sender}, not {person['name']}'s registered {person['email']}"))
        facts["unregistered_channel"] = True
    if sender and person.get("phone") and "@" not in sender and sender.replace(" ", "")[-10:] != person["phone"].replace(" ", "")[-10:]:
        checks.append((0.6, f"call or message from {sender}, not {person['name']}'s registered number"))
        facts["unregistered_channel"] = True
    if hour is not None and not (person.get("work_start", 9) <= hour < person.get("work_end", 19)):
        checks.append((0.3, f"arrived at {hour}:00, outside {person['name']}'s usual hours"))
    limit = person.get("approval_limit") or 0
    if amount and limit and amount > limit:
        checks.append((0.4, f"amount {inr(amount)} is above the {inr(limit)} approval limit, needs a second approver"))
        facts["over_limit"] = True
    usual = person.get("usual_requests") or []
    if action != "none" and usual and action.replace("_high", "") not in usual:
        checks.append((0.4, f"{person['name']} does not normally make {action.replace('_high', '')} requests"))

    if checks:
        s = 1.0
        for p, _ in checks:
            s *= 1 - p
        score, why = round(1 - s, 3), "; ".join(r for _, r in checks)
    else:
        score, why = 0.2, f"channel, timing and request fit {person['name']}'s normal pattern"
    return [{"signal": "context_anomaly", "label": "Context vs Trust Graph", "score": score, "why": why,
             "evidence": [{"type": "context", "text": r} for _, r in checks]}], facts


if __name__ == "__main__":
    cfo = {"name": "Rajesh", "email": "rajesh@acme.com", "phone": "9876543210", "channels": ["email", "teams"],
           "work_start": 9, "work_end": 19, "approval_limit": 1_000_000, "usual_requests": ["information"],
           "voice_emb": [1, 0, 0], "face_emb": None}
    sig, f = context_signal(cfo, channel="whatsapp", sender="+91 9000000000", hour=23, action="payment_high", amount=4_500_000)
    assert sig[0]["score"] > 0.9 and f["unregistered_channel"] and f["over_limit"], sig
    sig, _ = context_signal(cfo, channel="email", sender="rajesh@acme.com", hour=11, action="information")
    assert sig[0]["score"] == 0.2
    b, f = biometric_signals(cfo, voice_emb=[0.2, 0.98, 0])
    assert b[0]["score"] > 0.9 and f["voice_mismatch_enrolled"]
    assert inr(4_500_000) == "₹45,00,000" and inr(999) == "₹999" and inr(10_000_000) == "₹1,00,00,000"
    print("identity ok")
