// Same maths as backend/fusion.py, so the landing page demo runs with no backend.
export const BIAS = Math.log(0.05 / 0.95);
export const WEIGHTS = {
  audio_spoof: 1.0, voice_mismatch: 0.8, face_video: 0.8, face_mismatch: 0.6, lip_sync: 0.5, image_synthetic: 0.6, image_univfd: 0.7,
  message_tactics: 0.6, message_classifier: 0.4, context_anomaly: 1.0, lookalike_domain: 0.7, header_auth: 0.6, bad_url: 1.2,
};
export const IMPACT = { payment_high: 1.0, credentials: 0.8, payment: 0.7, information: 0.4, none: 0.2 };
export const IMPACT_LABEL = {
  payment_high: "Large payment / new account", credentials: "Password or OTP", payment: "Routine payment",
  information: "Share documents", none: "No action asked",
};

const logit = (s) => { const x = Math.min(Math.max(s, 1e-4), 1 - 1e-4); return Math.log(x / (1 - x)); };
export const bandOf = (r) => (r >= 60 ? "HIGH" : r >= 30 ? "MEDIUM" : "LOW");

export function fuse(signals, action = "none", facts = {}) {
  const rows = signals.filter((s) => s.score != null).map((s) => {
    const weight = WEIGHTS[s.signal] ?? 0.5;
    return { ...s, weight, contribution: Math.round(weight * logit(s.score) * 1000) / 1000 };
  });
  const total = rows.reduce((a, r) => a + r.weight * logit(r.score), 0);
  const t = 1 / (1 + Math.exp(-(BIAS + total)));
  let risk = 100 * t * IMPACT[action];
  const rules = [];
  const risky = ["payment", "payment_high", "credentials"].includes(action);
  if (risky && (facts.unregistered_channel || facts.new_beneficiary)) rules.push("Payment or credential request from an unregistered channel or to a new beneficiary");
  if (facts.digital_arrest) rules.push("'Digital arrest' pattern");
  if (rules.length) risk = Math.max(risk, 60);
  risk = Math.round(risk * 10) / 10;
  rows.sort((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution));
  return { risk, band: bandOf(risk), threat: t, impact: IMPACT[action], action, signals: rows, rules_fired: rules, prior_logodds: Math.round(BIAS * 1000) / 1000 };
}
