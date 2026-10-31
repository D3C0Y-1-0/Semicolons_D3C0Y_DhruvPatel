"""Clean slate before a demo: python reset_demo.py
Clears every case and the mule blocklist, keeps the Trust Graph exactly as enrolled (emails, phones, Telegram ids,
voiceprints). seed.py would put the demo emails and phones back over the ones you set. Safe while the backend runs."""
import db

if __name__ == "__main__":
    with db.conn() as c:
        cases = c.execute("DELETE FROM cases").rowcount
        mules = c.execute("DELETE FROM mules").rowcount
        people = c.execute("SELECT COUNT(*) FROM people").fetchone()[0]
    print(f"cleared {cases} cases and {mules} blocklist entries; kept {people} people")
