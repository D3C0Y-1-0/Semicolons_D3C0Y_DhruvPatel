"""CERT-In incident report draft. CERT-In directions (April 2022) require reporting within 6 hours.
ponytail: field list follows the general incident form; check it against CERT-In's current form before submitting."""
import datetime as dt

from detectors.identity import inr


def cert_in_draft(case, org=None):
    r = case["result"]
    when = dt.datetime.fromtimestamp(case["created"]).strftime("%Y-%m-%d %H:%M (server local time)")
    indicators = []
    for s in r.get("signals", []):
        if s.get("contribution", 0) > 0:
            indicators.append(f"- {s['label']}: {s['why']} (score {s['score']:.2f})")
            indicators += [f"    - {e.get('text', '')}" for e in s.get("evidence", [])[:3] if e.get("text")]
    facts = r.get("facts", {})
    return f"""# CERT-In incident report (DRAFT, review before sending)

**Report to:** incident@cert-in.org.in (within 6 hours of noticing the incident)
**Reporting organisation:** {org or "<organisation name, address, contact>"}
**Case ID:** {case['id']}
**Date and time detected:** {when}
**Incident type:** Social engineering / impersonation using AI-generated (deepfake) media
**Status:** {case['status']}

## Description
{r.get('summary', '')}

Risk assessment: **{r['band']}** ({r['risk']}/100). Requested action: {r.get('action')}.
Amount involved: {inr(facts["amount_inr"]) if facts.get('amount_inr') else "none stated"}.
Channel: {r.get('channel') or "unknown"}. Sender: {facts.get('sender_email') or r.get('sender') or "unknown"}.

## Indicators observed
{chr(10).join(indicators) or "- none"}

## Policy rules triggered
{chr(10).join("- " + x for x in r.get("rules_fired", [])) or "- none"}

## Actions taken
- Requested action placed on hold pending out-of-band verification
- Verification result: {r.get('verification', {}).get('answer', 'pending')}
- Sender identifiers blocked: <fill in>
- Affected employee briefed: <fill in>

## Affected systems
<email gateway / collaboration tool / phone line>

## Contact
<name, designation, phone, email of reporting officer>
"""
