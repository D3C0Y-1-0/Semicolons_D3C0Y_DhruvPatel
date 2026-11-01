"""Who can release a held request: python test_answer_rules.py (throwaway database, no network).

The rules answer "what if the person's phone is hacked or their login leaked": one tap of YES releases only a small
request. Above the approval limit, or when the YES comes impossibly fast, it takes a video YES or a second approver.
"""
import os
import tempfile
import time

os.environ.update(TRUSTCHECK_DB=os.path.join(tempfile.mkdtemp(), "rules.db"), TELEGRAM_BOT_TOKEN="", SMTP_USER="", SMTP_PASS="")
import db  # noqa: E402
import notify  # noqa: E402

db.add_person(id="cfo", name="Rajesh Kumar", approval_limit=1_000_000)
db.add_person(id="ceo", name="Ananya Iyer", approval_limit=5_000_000)


def case(amount, asked_ago=60):
    cid, _ = db.save_case({"band": "HIGH", "risk": 99, "action": "payment", "facts": {"amount_inr": amount}, "signals": []}, "cfo")
    return db.update_case(cid, status="verifying", result_patch={"asked_at": time.time() - asked_ago})["id"]


small, big, fast = case(50_000), case(4_500_000), case(50_000, asked_ago=2)

assert notify.record_answer(small, "yes", "link")["status"] == "verified"               # small: one YES is enough

c = notify.record_answer(big, "yes", "link")                                              # big: a tap is not enough
assert c["status"] == "verifying" and "approval limit" in c["result"]["needs"]["why"][0]
assert notify.record_answer(big, "yes", "manual")["status"] == "verifying"                # nor a second tap
assert notify.record_answer(big, "yes", "approver", approver="ceo")["status"] == "verified"  # second approver releases

big2 = case(4_500_000)
notify.record_answer(big2, "yes", "telegram")
assert notify.record_answer(big2, "yes", "video")["status"] == "verified"                 # or a video YES

big3 = case(4_500_000)
assert notify.record_answer(big3, "yes", "approver", approver="ceo")["status"] == "verifying"  # approver alone isn't enough
assert notify.record_answer(big3, "no", "link")["status"] == "confirmed_attack"           # and NO from anyone blocks

c = notify.record_answer(fast, "yes", "link")                                             # YES 2 s after asking: suspicious
assert c["status"] == "verifying" and "faster than a person" in c["result"]["needs"]["why"][-1]

big4 = case(4_500_000)
assert notify.record_answer(big4, "no", "approver", approver="ceo")["status"] == "confirmed_attack"  # approver's NO blocks
assert notify.record_answer(big4, "yes", "video")["status"] == "confirmed_attack"         # a decided case stays decided
print("answer rules ok: small 1 tap, big needs video or 2 people, fast YES held, any NO blocks")
