// Same maths as backend/fusion.py, so the landing page demo runs with no backend.
export const BIAS = Math.log(0.05 / 0.95);
export const WEIGHTS = {
  audio_spoof: 1.0, voice_mismatch: 0.8, face_video: 0.8, face_mismatch: 0.6, lip_sync: 0.5, image_synthetic: 0.6, image_univfd: 0.7,
  message_tactics: 0.6, message_classifier: 0.4, context_anomaly: 1.0, lookalike_domain: 0.7, header_auth: 0.6, bad_url: 1.2, known_mule: 1.5,
  link_risk: 1.0, scam_pattern: 0.8,
};
export const IMPACT = { payment_high: 1.0, install_app: 0.9, credentials: 0.8, payment: 0.7, click_link: 0.7, personal_info: 0.6, call_back: 0.5, information: 0.4, none: 0.2 };
export const IMPACT_LABEL = {
  payment_high: "Large payment / new account", credentials: "Password or OTP", payment: "Routine payment",
  install_app: "Install an app", click_link: "Click a link", personal_info: "Share ID / personal data", call_back: "Call a number",
  information: "Share documents", none: "No action asked",
};

const logit = (s) => { const x = Math.min(Math.max(s, 1e-4), 1 - 1e-4); return Math.log(x / (1 - x)); };
export const bandOf = (r) => (r >= 60 ? "HIGH" : r >= 30 ? "MEDIUM" : "LOW");
// The HIGH floor grows with the money at stake: 60 up to ₹10,000, 75 at ₹1 lakh, 90 from ₹10 lakh (same as fusion.py)
export const moneyFloor = (amt) => (!amt || amt <= 10000 ? 60 : Math.round(Math.min(90, 60 + 15 * Math.log10(amt / 10000)) * 10) / 10);

export function fuse(signals, action = "none", facts = {}) {
  const rows = signals.filter((s) => s.score != null).map((s) => {
    const weight = WEIGHTS[s.signal] ?? 0.5;
    return { ...s, weight, contribution: Math.round(weight * logit(s.score) * 1000) / 1000 };
  });
  const total = rows.reduce((a, r) => a + r.weight * logit(r.score), 0);
  const t = 1 / (1 + Math.exp(-(BIAS + total)));
  let risk = 100 * t * IMPACT[action];
  const rules = [];
  const high = moneyFloor(["payment", "payment_high"].includes(action) ? facts.amount_inr : null);
  const floor = (text, value) => { rules.push(text); risk = Math.max(risk, value); };
  const risky = ["payment", "payment_high", "credentials", "install_app"].includes(action);
  if (risky && (facts.unregistered_channel || facts.new_beneficiary)) floor("Payment or credential request from an unregistered channel or to a new beneficiary", high);
  if (facts.known_mule) floor("Names a bank account, UPI id or number already on the mule blocklist", high);
  if (facts.bad_url) floor("Link on a known phishing or malware list", 60);
  else if (facts.dangerous_link) floor("Link fakes a bank or brand, installs an app, hides behind an IP or is days old", 60);
  if (facts.digital_arrest) floor("'Digital arrest' pattern", high);
  if (facts.scam_strong) floor("Matches a known scam pattern and the wording, link or tactics back it up", high);
  else if (facts.scam_pattern) floor("Matches a known scam pattern", 30);
  risk = Math.round(risk * 10) / 10;
  rows.sort((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution));
  return { risk, band: bandOf(risk), threat: t, impact: IMPACT[action], action, signals: rows, rules_fired: rules, prior_logodds: Math.round(BIAS * 1000) / 1000 };
}

// Self-check, same worked examples as backend/fusion.py: node src/lib/fusion.js (never runs in the browser)
if (typeof process !== "undefined" && process.argv?.[1]?.endsWith("fusion.js")) {
  const sig = (signal, score) => ({ signal, score });
  const ok = (cond, msg) => { if (!cond) throw new Error(msg); };
  const a = fuse([sig("audio_spoof", 0.88), sig("voice_mismatch", 0.85), sig("face_video", 0.74), sig("message_tactics", 0.92),
    sig("context_anomaly", 0.9), sig("lookalike_domain", 0.95)], "payment_high", { unregistered_channel: true });
  ok(a.risk === 99.9 && a.band === "HIGH", `A ${a.risk}`);
  const b = fuse([sig("audio_spoof", 0.88), sig("voice_mismatch", 0.85), sig("face_video", 0.74), sig("message_tactics", 0.1)], "none");
  ok(b.risk === 9.8 && b.band === "LOW", `B ${b.risk}`);
  const c = [sig("audio_spoof", 0.3), sig("voice_mismatch", 0.2), sig("face_video", 0.4), sig("message_tactics", 0.92), sig("context_anomaly", 0.9)];
  ok(fuse(c, "payment_high").risk === 17.3, `C maths ${fuse(c, "payment_high").risk}`);
  ok(fuse(c, "payment_high", { unregistered_channel: true, new_beneficiary: true }).risk === 60, "C rule");
  const ask = (amt) => fuse([sig("message_tactics", 0.4)], "payment_high", { unregistered_channel: true, amount_inr: amt }).risk;
  ok([1e4, 1e5, 1e6, 5e7].map(ask).join() === "60,75,90,90", `money floor ${[1e4, 1e5, 1e6, 5e7].map(ask)}`);
  ok(fuse([sig("link_risk", 0.95)], "click_link", { dangerous_link: true }).band === "HIGH", "link");
  ok(fuse([sig("scam_pattern", 0.85)], "none", { scam_pattern: true }).risk === 30, "pattern");
  ok(fuse([sig("scam_pattern", 0.85)], "call_back", { scam_pattern: true, scam_strong: true }).risk === 60, "strong pattern");
  console.log("fusion.js ok: A=99.9 HIGH, B=9.8 LOW, C=17.3 -> HIGH by rule");
}
