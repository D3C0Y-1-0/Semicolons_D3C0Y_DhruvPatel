"""SQLite store: Org Trust Graph (people) and cases. Embeddings only, never raw media."""
import json
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
"""
CAMPAIGN_SIM = 0.60  # ponytail: tune on eval; ECAPA same-speaker pairs usually sit well above this


def conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.executescript(SCHEMA)
    return c


def _person(row):
    if not row:
        return None
    p = dict(row)
    for k in ("channels", "usual_requests", "voice_emb", "face_emb"):
        p[k] = json.loads(p[k]) if p[k] else None
    return p


def add_person(**p):
    """Insert, or update when id exists: fields passed as None (e.g. no new voice sample) keep their stored value."""
    pid = p.get("id") or uuid.uuid4().hex[:8]
    old = get_person(pid) or {}
    p = {**old, **{k: v for k, v in p.items() if v is not None}}
    for k in ("channels", "usual_requests", "voice_emb", "face_emb"):
        if p.get(k) is not None:
            p[k] = json.dumps(p[k])
    cols = ["id", "name", "role", "email", "phone", "telegram_chat_id", "channels", "work_start",
            "work_end", "approval_limit", "usual_requests", "voice_emb", "face_emb"]
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
    for r in rows:  # never send embeddings to the browser
        r["voice_enrolled"], r["face_enrolled"] = bool(r.pop("voice_emb")), bool(r.pop("face_emb"))
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
    return {"bands": bands, "status": status, "people": people,
            "campaigns": [{"id": r[0], "size": r[1]} for r in campaigns]}


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
