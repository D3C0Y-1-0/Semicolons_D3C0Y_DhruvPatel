"""Mule-account registry and Decoy Mode.

Registry: bank accounts, IFSC codes, UPI ids and phone numbers that scammers asked someone to pay or call.
Every confirmed attack and every decoy conversation adds to it; any later message naming one of them is HIGH.

Decoy Mode: replies that play a cooperative, slightly confused victim, so the scammer reveals more of these.
The decoy only asks questions; it never sends money or real details.
ponytail: replies are templates; with ANTHROPIC_API_KEY set they could be generated per conversation.
"""
import re

import db

UPI_HANDLES = ("ok", "ybl", "ibl", "axl", "paytm", "upi", "apl", "icici", "sbi", "hdfcbank", "axisbank", "kotak",
               "yesbank", "fbl", "pt", "jupiteraxis", "slice", "freecharge")
PATTERNS = {
    "upi": re.compile(r"\b[\w.\-]{2,}@(?:%s)[a-z]*\b" % "|".join(UPI_HANDLES), re.I),
    "ifsc": re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b"),
    "account": re.compile(r"(?:a/?c|acct|account|khata)[^\d]{0,20}?((?:\d[ -]?){9,18})", re.I),
    "phone": re.compile(r"(?<!\d)(?:\+?91[ -]?)?([6-9]\d{4}[ -]?\d{5})(?!\d)"),
}
LABEL = {"account": "Bank account", "ifsc": "IFSC", "upi": "UPI ID", "phone": "Phone number"}


def _norm(kind, v):
    if kind in ("account", "phone"):
        return re.sub(r"\D", "", v)[-18:] if kind == "account" else re.sub(r"\D", "", v)[-10:]
    return v.upper() if kind == "ifsc" else v.lower()


def extract(text):
    """Identifiers a scammer could be paid or reached through, minus enrolled people's own numbers."""
    own = {re.sub(r"\D", "", p.get("phone") or "")[-10:] for p in db.list_people()}
    seen, out = set(), []
    for kind, rx in PATTERNS.items():
        for m in rx.finditer(text or ""):
            v = _norm(kind, m.group(1) if m.groups() else m.group(0))
            if (kind, v) in seen or (kind == "phone" and v in own):
                continue
            seen.add((kind, v))
            out.append({"kind": kind, "label": LABEL[kind], "value": v})
    return out


def signals(text):
    """(signals, facts, identifiers) for a message: a HIGH-forcing signal when it names a known mule."""
    ids = extract(text)
    known = db.find_mules(ids)
    if not known:
        return [], {}, ids
    why = ", ".join(f"{LABEL[k['kind']].lower()} {k['value']}" for k in known)
    return ([{"signal": "known_mule", "label": "Mule account blocklist", "score": 0.99,
              "why": f"names {why}, already used in a confirmed attack or caught by Decoy Mode",
              "evidence": [{"type": "mule", "text": f"{LABEL[k['kind']]} {k['value']}: first seen {k['source']}, seen {k['hits']} times"} for k in known]}],
            {"known_mule": True}, ids)


def harvest_case(case, source):
    """Add a case's identifiers to the registry (on a confirmed attack)."""
    ids = case["result"].get("identifiers") or []
    db.add_mules(ids, case["id"], source)
    return ids


# --- Decoy Mode ---------------------------------------------------------------------------------------------
ASK = {  # what to fish for next, in order; each line sounds like a victim fighting a bank form
    "account": ("Sir, the bank app logged me out. Can you send the account number once more, exactly as on the cheque?",
                "Sir, bank app logout ho gaya. Account number ek baar phir bhejo, cheque pe jaisa hai waisa."),
    "ifsc": ("It says IFSC is required for NEFT above 2 lakh. Which branch IFSC should I enter?",
             "NEFT ke liye IFSC maang raha hai, 2 lakh se upar. Kaunsi branch ka IFSC daalu?"),
    "name": ("What exact name should I write as the beneficiary? It bounces if it doesn't match the account.",
             "Beneficiary ka exact naam kya likhu? Match nahi hua toh payment bounce ho jayega."),
    "phone": ("The bank wants the beneficiary's mobile number for the confirmation OTP. Which number should I give?",
              "Bank beneficiary ka mobile number maang raha hai OTP ke liye. Kaunsa number du?"),
    "upi": ("RTGS is down till 4 pm. If you send a UPI ID, I can push the first part right now.",
            "RTGS 4 baje tak band hai. UPI ID bhej do, pehla hissa abhi bhej deta hoon."),
}
STALL = ("Done, it's showing 'pending approval from treasury'. My manager wants the vendor's GST number before he approves. Can you share it?",
         "Ho gaya, 'treasury approval pending' dikha raha hai. Manager vendor ka GST number maang rahe hain, bhej doge?")
HINGLISH = re.compile(r"\b(hai|karo|kar|aap|bhej|turant|nahi|raho|bol|hoon|paisa|jaldi)\b", re.I)


def decoy_turn(case, scammer_text=""):
    """Advance the decoy conversation stored on the case; returns the updated decoy state."""
    r = case["result"]
    state = r.get("decoy") or {"turns": [], "harvested": [], "asked": []}
    original = (r.get("message") or {}).get("text") or ""
    if not state["turns"]:  # first turn: whatever the scam message already gave away goes on the blocklist
        state["harvested"] = list(r.get("identifiers") or [])
        db.add_mules(state["harvested"], case["id"], "decoy (original message)")
    if scammer_text.strip():
        state["turns"].append({"who": "scammer", "text": scammer_text.strip()})
        have = {(h["kind"], h["value"]) for h in state["harvested"]}
        new = [i for i in extract(scammer_text) if (i["kind"], i["value"]) not in have]
        if re.search(r"\b(name|naam)\b", scammer_text, re.I) or (state["asked"][-1:] == ["name"] and not new):
            state.setdefault("got_name", True)
        state["harvested"] += new
        db.add_mules(new, case["id"], "decoy reply")
        state["new"] = new
    else:
        state["new"] = []
    hindi = bool(HINGLISH.search(original + " " + scammer_text))
    kinds = {h["kind"] for h in state["harvested"]}
    want = next((k for k in ASK if k not in state["asked"] and (k == "name" or k not in kinds)), None)
    line = (ASK[want] if want else STALL)[1 if hindi else 0]
    if want:
        state["asked"].append(want)
    state["turns"].append({"who": "decoy", "text": line})
    return state


def demo():
    msg = "transfer ₹45,00,000 to A/c 5021 0098 7712, IFSC HDFC0001234 or UPI rajesh.vendor@okhdfcbank, call +91 90000 12345"
    ids = {(i["kind"], i["value"]) for i in extract(msg)}
    assert ids >= {("account", "502100987712"), ("ifsc", "HDFC0001234"), ("upi", "rajesh.vendor@okhdfcbank"), ("phone", "9000012345")}, ids
    assert not any(k == "phone" and v.startswith("50") for k, v in ids), ids  # account digits aren't a phone number
    print("mules ok:", sorted(ids))


if __name__ == "__main__":
    demo()
