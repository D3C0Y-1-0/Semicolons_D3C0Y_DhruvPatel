"""SQLite store: Org Trust Graph (people) and cases. Embeddings only, never raw media."""
import json
import secrets
import sqlite3
import time
import uuid
from pathlib import Path

DB_PATH = Path(__file__).parent / "trustcheck.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS people (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, role TEXT, email TEXT, phone TEXT,
  telegram_chat_id TEXT, channels TEXT,          -- JSON list, e.g. ["email","teams"]
  work_start INTEGER DEFAULT 9, work_end INTEGER DEFAULT 19,
  approval_limit REAL DEFAULT 0, usual_requests TEXT,  -- JSON list of action types
  voice_emb TEXT, face_emb TEXT                   -- JSON float lists
);
CREATE TABLE IF NOT EXISTS cases (
  id TEXT PRIMARY KEY, created REAL, band TEXT, risk REAL, status TEXT,
  claimed_person_id TEXT, summary TEXT, result TEXT,  -- full analysis JSON
  voice_emb TEXT, campaign TEXT                      -- same cloned voice across cases = one campaign
);
CREATE TABLE IF NOT EXISTS mules (                   -- accounts, IFSC, UPI ids, phones scammers used
  kind TEXT, value TEXT, first_case TEXT, first_seen REAL, hits INTEGER DEFAULT 1, source TEXT,
  PRIMARY KEY (kind, value)
);
"""
CAMPAIGN_SIM = 0.60  # ponytail: tune on eval; ECAPA same-speaker pairs usually sit well above this


def conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.executescript(SCHEMA)
    for col in ("code_secret", "family_emails"):  # added after the first release: Human 2FA secret, family alert emails (JSON)
        try:
            c.execute(f"ALTER TABLE people ADD COLUMN {col} TEXT")
        except sqlite3.OperationalError:
            pass
    return c


def _person(row):
    if not row:
        return None
    p = dict(row)
    for k in ("channels", "usual_requests", "voice_emb", "face_emb", "family_emails"):
        p[k] = json.loads(p[k]) if p.get(k) else None
    return p


def add_person(**p):
    """Insert, or update when id exists: fields passed as None (e.g. no new voice sample) keep their stored value."""
    pid = p.get("id") or uuid.uuid4().hex[:8]
    old = get_person(pid) or {}
    p = {**old, **{k: v for k, v in p.items() if v is not None}}
    for k in ("channels", "usual_requests", "voice_emb", "face_emb", "family_emails"):
        if p.get(k) is not None:
            p[k] = json.dumps(p[k])
    p.setdefault("code_secret", secrets.token_hex(16))
    cols = ["id", "name", "role", "email", "phone", "telegram_chat_id", "channels", "work_start",
            "work_end", "approval_limit", "usual_requests", "voice_emb", "face_emb", "code_secret", "family_emails"]
    vals = [pid] + [p.get(k) for k in cols[1:]]
    with conn() as c:
        c.execute(f"INSERT OR REPLACE INTO people ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})", vals)
    return pid


def get_person(pid):
    with conn() as c:
        return _person(c.execute("SELECT * FROM people WHERE id=?", (pid,)).fetchone())


def list_people():
    with conn() as c:
        rows = [_person(r) for r in c.execute("SELECT * FROM people ORDER BY name")]
    for r in rows:  # never send embeddings or the code-word secret to the browser
        r["voice_enrolled"], r["face_enrolled"] = bool(r.pop("voice_emb")), bool(r.pop("face_emb"))
        r.pop("code_secret", None)
    return rows


def find_person_by_domain_or_name(text):
    """Best-effort: which enrolled person does this message claim to be?"""
    text = (text or "").lower()
    with conn() as c:
        for r in c.execute("SELECT * FROM people"):
            first = r["name"].split()[0].lower()
            if r["name"].lower() in text or (len(first) > 3 and first in text):
                return _person(r)
    return None


def _cos(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na, nb = sum(x * x for x in a) ** .5, sum(y * y for y in b) ** .5
    return dot / (na * nb) if na and nb else 0.0


def save_case(result, claimed_person_id=None, voice_emb=None):
    """Returns (case_id, campaign) where campaign = {id, size} when this voice was seen in earlier risky cases."""
    cid = uuid.uuid4().hex[:10]
    campaign = None
    with conn() as c:
        if voice_emb and result["band"] != "LOW":
            for r in c.execute("SELECT id, voice_emb, campaign FROM cases WHERE voice_emb IS NOT NULL AND band != 'LOW' ORDER BY created"):
                if _cos(voice_emb, json.loads(r["voice_emb"])) >= CAMPAIGN_SIM:
                    campaign = r["campaign"] or r["id"]
                    c.execute("UPDATE cases SET campaign=? WHERE id=?", (campaign, r["id"]))
                    break
        c.execute("INSERT INTO cases VALUES (?,?,?,?,?,?,?,?,?,?)",
                  (cid, time.time(), result["band"], result["risk"], "open", claimed_person_id,
                   result.get("summary", ""), json.dumps(result), json.dumps(voice_emb) if voice_emb else None, campaign))
        size = c.execute("SELECT COUNT(*) FROM cases WHERE campaign=?", (campaign,)).fetchone()[0] if campaign else 0
    return cid, ({"id": campaign, "size": size} if campaign else None)


def stats():
    with conn() as c:
        bands = dict(c.execute("SELECT band, COUNT(*) FROM cases GROUP BY band").fetchall())
        status = dict(c.execute("SELECT status, COUNT(*) FROM cases GROUP BY status").fetchall())
        campaigns = c.execute("SELECT campaign, COUNT(*) n FROM cases WHERE campaign IS NOT NULL GROUP BY campaign ORDER BY n DESC").fetchall()
        people = c.execute("SELECT COUNT(*) FROM people").fetchone()[0]
        protected, types = 0.0, {}
        for (raw,) in c.execute("SELECT result FROM cases WHERE band != 'LOW' AND status != 'verified'"):
            r = json.loads(raw)  # ponytail: full scan of risky cases; add columns if the queue grows past a few thousand
            if r.get("action") in ("payment", "payment_high"):
                protected += (r.get("facts") or {}).get("amount_inr") or 0
            for t in r.get("scam_types") or []:
                types[t["label"]] = types.get(t["label"], 0) + 1
    return {"bands": bands, "status": status, "people": people,
            "campaigns": [{"id": r[0], "size": r[1]} for r in campaigns],
            "money_held": protected, "scam_types": sorted(types.items(), key=lambda kv: -kv[1])}


def update_case(cid, **fields):
    with conn() as c:
        row = c.execute("SELECT result FROM cases WHERE id=?", (cid,)).fetchone()
        if not row:
            return None
        result = json.loads(row["result"])
        result.update(fields.get("result_patch", {}))
        c.execute("UPDATE cases SET status=COALESCE(?, status), result=? WHERE id=?",
                  (fields.get("status"), json.dumps(result), cid))
    return get_case(cid)


def get_case(cid):
    with conn() as c:
        r = c.execute("SELECT * FROM cases WHERE id=?", (cid,)).fetchone()
    if not r:
        return None
    d = dict(r)
    d.pop("voice_emb")  # biometric data never leaves the server
    d["result"] = json.loads(d["result"])
    return d


def list_cases(limit=100):
    with conn() as c:
        return [{k: r[k] for k in ("id", "created", "band", "risk", "status", "claimed_person_id", "summary", "campaign")}
                for r in c.execute("SELECT * FROM cases ORDER BY created DESC LIMIT ?", (limit,))]


def person_by_chat(chat_id):
    with conn() as c:
        return _person(c.execute("SELECT * FROM people WHERE telegram_chat_id=?", (str(chat_id),)).fetchone())


def code_secret(pid):
    """The person's Human 2FA secret, created on first use for people enrolled before the feature existed."""
    p = get_person(pid)
    if not p:
        return None
    if not p.get("code_secret"):
        p["code_secret"] = secrets.token_hex(16)
        with conn() as c:
            c.execute("UPDATE people SET code_secret=? WHERE id=?", (p["code_secret"], pid))
    return p["code_secret"]


def add_mules(items, case_id, source):
    with conn() as c:
        for i in items:
            c.execute("INSERT INTO mules (kind, value, first_case, first_seen, source) VALUES (?,?,?,?,?) "
                      "ON CONFLICT(kind, value) DO UPDATE SET hits = hits + 1", (i["kind"], i["value"], case_id, time.time(), source))


def find_mules(items):
    if not items:
        return []
    with conn() as c:
        return [dict(r) for i in items for r in c.execute("SELECT * FROM mules WHERE kind=? AND value=?", (i["kind"], i["value"]))]


def list_mules():
    with conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM mules ORDER BY first_seen DESC")]
