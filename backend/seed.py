"""Demo Trust Graph so the pitch works on a fresh laptop: python seed.py
Re-run any time; it upserts by fixed ids. Enrol real voices/faces from the People page afterwards."""
import db

PEOPLE = [
    dict(id="cfo-rajesh", name="Rajesh Kumar", role="CFO", email="rajesh@acme.com", phone="9876543210",
         channels=["email", "teams"], work_start=9, work_end=19, approval_limit=1_000_000,
         usual_requests=["information", "payment"]),
    dict(id="ceo-ananya", name="Ananya Iyer", role="CEO", email="ananya@acme.com", phone="9820012345",
         channels=["email", "teams", "meet"], work_start=8, work_end=20, approval_limit=5_000_000,
         usual_requests=["information"]),
    dict(id="hr-farhan", name="Farhan Shaikh", role="HR Lead", email="farhan@acme.com", phone="9930098765",
         channels=["email", "teams"], work_start=10, work_end=18, approval_limit=0,
         usual_requests=["information"]),
]

if __name__ == "__main__":
    for p in PEOPLE:
        db.add_person(**p)
    print("seeded:", ", ".join(p["name"] for p in PEOPLE))
