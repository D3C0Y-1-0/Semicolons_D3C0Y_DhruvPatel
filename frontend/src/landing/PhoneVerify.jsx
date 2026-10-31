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
      <div className="mx-auto w-72 rounded-[2.6rem] bg-night p-3 shadow-[0_30px_60px_-20px_rgb(13_23_48/0.5)]">
        <div className="rounded-[2rem] bg-[#dfe9e5] h-[31rem] flex flex-col overflow-hidden">
          <div className="bg-sheet px-4 py-3 text-sm font-bold border-b border-rule">TrustCheck security bot</div>
          <div className="flex-1 p-3 flex flex-col justify-end gap-2 text-[0.84rem]">
            <div className="bg-sheet rounded-xl rounded-bl-sm p-3 shadow-sm">
              Someone using your name (<b>Rajesh Kumar</b>) just asked Priya in Finance for <b>₹45,00,000</b> to a new account, via WhatsApp.
              <p className="mt-2 font-semibold">Did YOU send this request?</p>
            </div>
            <AnimatePresence mode="wait">
              {!answer ? (
                <motion.div key="ask" className="grid grid-cols-2 gap-1.5" exit={{ opacity: 0, y: 6 }}>
                  <button onClick={() => setAnswer("yes")} className="bg-sheet rounded-lg py-2 font-semibold text-low">YES, it was me</button>
                  <button onClick={() => setAnswer("no")} className="bg-sheet rounded-lg py-2 font-semibold text-high">NO, not me</button>
                </motion.div>
              ) : (
                <motion.div key="done" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
                  className="bg-sheet rounded-xl rounded-bl-sm p-3 shadow-sm">
                  {answer === "no" ? "Recorded: NOT you. The payment is on hold and security has been alerted." : "Recorded: you confirmed the request. Priya can go ahead."}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>

      <div className="min-h-[22rem]">
        {!answer && (
          <p className="text-xl text-ink-soft max-w-md">
            This is the message the <i>real</i> CFO gets on the phone number he enrolled, not on the channel the attacker controls.
            Tap an answer on the phone.
          </p>
        )}
        {answer === "yes" && <p className="text-xl max-w-md">Released. The case closes as verified, and the employee knows the check came from the real person.</p>}
        {answer === "no" && (
          <ol className="space-y-5">
            {AFTER.map(([h, d], i) => (
              <motion.li key={h} initial={{ opacity: 0, x: -12 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.25 + i * 0.35 }}
                className="grid grid-cols-[2rem_1fr] gap-3">
                <span className="tnum font-bold text-high">{i + 1}</span>
                <span><b className="block text-lg">{h}</b><span className="text-ink-soft">{d}</span></span>
              </motion.li>
            ))}
          </ol>
        )}
        {answer && <button onClick={() => setAnswer(null)} className="mt-8 underline underline-offset-4">Reset the phone</button>}
      </div>
    </div>
  );
}
