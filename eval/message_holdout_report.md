# Messages never seen in training: full-pipeline results

Three sets of realistic, hand-written messages (English, Hinglish, Hindi; SMS, WhatsApp, email, call notes), none taken from
the training templates or the self-checks. Each set was written **before** the system was scored on it, scored once, and only
then used to find gaps. So the honest number for each set is the one measured before any fix it prompted.
Scored with `python ../eval/run_holdout.py <set>` (no claimed person, offline lexicon, link lookups on).

| Set | Scams | Genuine | Scams HIGH (first measurement, unseen) | Genuine left LOW (first measurement) | What its misses taught |
| --- | --- | --- | --- | --- | --- |
| v1 `holdout_messages.csv` | 28 | 22 | 21/28 (75%) | 22/22 (100%) | Hinglish phrasings, "tell me the OTP", "loan … is pre-approved", fee-to-receive |
| v2 `holdout_messages_v2.csv` | 20 | 15 | 15/20 (75%), after the v1 fixes | 15/15 (100%) | "account will be deleted", "new supplier account", "bete", fee to send a "box", bait words in domains |
| v3 `holdout_messages_v3.csv` | 20 | 15 | **17/20 (85%)**, after the v2 fixes | **15/15 (100%)** | "share the code you receive", number disconnection, "could not be delivered" |
| v4 `holdout_messages_v4.csv` | 12 | 8 | **5/12 (42%)**, 6/12 flagged, after the v3 fixes and the semantic classifier | **8/8 (100%)** | bare links on .shop/.help/.online, Hinglish sextortion, "work-from-home" with hyphens, refundable "security deposit", parcel-with-drugs opener, "safe RBI account", accident + send money from a "friend" |

Across all four first measurements: **58/80 scams HIGH (73%), 60/60 genuine messages LOW, 0 false HIGH.**
v4 was written in a deliberately different style from the first three, and its low first score is the honest sign that the
offline rules miss scam styles nobody has written a pattern for (the Claude API path is the answer for those).
After the fixes, all four sets score 100% / 0 false alarms, but those are now development sets, so that is not a claim.

The v3 genuine set is deliberately hard: a real family money request ("Papa, can you send 2000 for books"), real bank
spend alerts, delivery OTPs, subscription renewals from the same brands the scams imitate. All stayed LOW.

Limits: one team wrote both the system and the test messages, so these sets are friendlier than real traffic; n is small
(68 scams, 52 genuine in total, over three rounds). Run a set written by someone else before quoting a number.
