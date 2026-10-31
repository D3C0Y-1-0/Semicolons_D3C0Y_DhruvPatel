"""Full-pipeline check on hand-written messages that were never training data. Run from backend/:
    python ../eval/run_holdout.py ../eval/holdout_messages_v3.csv
Prints each message's band and a summary: attacks caught (HIGH, and HIGH or MEDIUM), genuine left LOW.
See eval/message_holdout_report.md for how the three sets were used (only the numbers measured before a fix count).
"""
import csv
import sys

sys.path.insert(0, ".")
import app  # noqa: E402

rows = list(csv.DictReader(open(sys.argv[1], encoding="utf-8")))
res = []
for r in rows:
    a = app.run_analysis(None, r["text"], None, r.get("claimed_person_id") or None, r.get("channel") or None)
    res.append((r["label"], a["band"], a["risk"], [t["type"] for t in a["scam_types"]], r["text"][:70]))
for label, band, risk, types, text in res:
    miss = (label == "attack" and band == "LOW") or (label == "benign" and band != "LOW")
    print("MISS" if miss else "    ", f"{label:6} {band:6} {risk:5.1f}", types, "|", text.encode("ascii", "replace").decode())
att, ben = [x for x in res if x[0] == "attack"], [x for x in res if x[0] == "benign"]
print(f"attacks HIGH {sum(x[1] == 'HIGH' for x in att)}/{len(att)}, HIGH or MEDIUM {sum(x[1] != 'LOW' for x in att)}/{len(att)}; "
      f"genuine LOW {sum(x[1] == 'LOW' for x in ben)}/{len(ben)}, false HIGH {sum(x[1] == 'HIGH' for x in ben)}/{len(ben)}")
