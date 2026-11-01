import { AnimatePresence, motion } from "framer-motion";
import { useState } from "react";

const AFTER = [
  ["₹45,00,000 transfer held", "Finance can't release it until the case closes."],
  ["Case marked as a confirmed attack", "It moves to the top of the security queue with every piece of evidence."],
  ["CERT-In report drafted", "Pre-filled with indicators, ready to send inside the 6-hour window."],
  ["Voiceprint added to the campaign", "If the same cloned voice calls anyone else, it's linked automatically."],
];

export default function PhoneVerify() {
  const [answer, setAnswer] = useState(null);
  return (
    <div className="grid md:grid-cols-[18rem_1fr] gap-12 items-center">
      <div className="mx-auto w-72 rounded-[2.8rem] bg-night text-ink p-3 shadow-[0_40px_80px_-30px_rgb(35_22_94/0.6)]">
        <div className="rounded-[2.2rem] dusk h-[31rem] flex flex-col overflow-hidden">
          <div className="glass-strong px-4 py-3 text-sm font-bold">TrustCheck security bot</div>
          <div className="flex-1 p-3 flex flex-col justify-end gap-2 text-[0.84rem]">
            <div className="glass-strong rounded-2xl rounded-bl-sm p-3">
              Someone using your name (<b>Rajesh Kumar</b>) just asked Priya in Finance for <b>₹45,00,000</b> to a new account, via WhatsApp.
              <p className="mt-2 font-semibold">Did YOU send this request?</p>
            </div>
            <AnimatePresence mode="wait">
              {!answer ? (
                <motion.div key="ask" className="grid grid-cols-2 gap-1.5" exit={{ opacity: 0, y: 6 }}>
                  <button onClick={() => setAnswer("yes")} className="glass-strong rounded-full py-2.5 font-bold text-low">YES, it was me</button>
                  <button onClick={() => setAnswer("no")} className="glass-strong rounded-full py-2.5 font-bold text-high">NO, not me</button>
                </motion.div>
              ) : (
                <motion.div key="done" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
                  className="glass-strong rounded-2xl rounded-bl-sm p-3">
                  {answer === "no" ? "Recorded: NOT you. The payment is on hold and security has been alerted." : "Recorded: you confirmed the request. Priya can go ahead."}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>

      <div className="min-h-[22rem]">
        {!answer && (
          <p className="text-xl text-white/85 max-w-md">
            This is the message the <i>real</i> CFO gets on the phone number he enrolled, not on the channel the attacker controls.
            Tap an answer on the phone.
          </p>
        )}
        {answer === "yes" && <p className="text-xl max-w-md">Released. The case closes as verified, and the employee knows the check came from the real person.</p>}
        {answer === "no" && (
          <ol className="space-y-3">
            {AFTER.map(([h, d], i) => (
              <motion.li key={h} initial={{ opacity: 0, x: -12 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.25 + i * 0.35 }}
                className="grid grid-cols-[2rem_1fr] gap-4 glass-strong text-ink rounded-[1.5rem] p-4">
                <span className="orb size-8 bg-night text-white text-sm font-bold tnum">{i + 1}</span>
                <span><b className="block text-lg">{h}</b><span className="text-ink-soft">{d}</span></span>
              </motion.li>
            ))}
          </ol>
        )}
        {answer && <button onClick={() => setAnswer(null)} className="mt-6 bg-white/80 text-ink border border-white rounded-full px-5 py-2.5 font-semibold">Reset the phone</button>}
      </div>
    </div>
  );
}
