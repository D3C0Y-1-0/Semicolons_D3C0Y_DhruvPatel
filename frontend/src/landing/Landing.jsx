import { AnimatePresence, motion } from "framer-motion";
import { lazy, Suspense, useState } from "react";
import { Stamp } from "../components/Verdict.jsx";
import MathsLab from "./MathsLab.jsx";
import PhoneVerify from "./PhoneVerify.jsx";

const Spectrogram3D = lazy(() => import("../components/Spectrogram3D.jsx"));

const CAPTION = {
  scanning: "Listening to the call…",
  flagging: "0:41–0:52: harmonics too regular for a human voice",
  verdict: "Voice cloned, and the request breaks payment policy",
  hold: "Voice cloned, and the request breaks payment policy",
};

const LEDGER = [
  ["US$25 million", "paid out by one finance employee in Hong Kong (Feb 2024) after a video call in which every colleague, including the CFO, was a deepfake."],
  ["₹1,935 crore", "lost by Indians to “digital arrest” scams in 2024 alone, across 1.23 lakh complaints: fake police and CBI officers on video calls (MHA reply in the Rajya Sabha)."],
  ["41%", "of CISOs surveyed by Gartner in September 2026 had already seen a deepfake in an employee audio call in the past year."],
];

const PIPELINE = [
  ["Listen and look", "Is the voice cloned? Is the face swapped? Do the lips follow the words?", "pellav2 voice detector, GenD face detector (WACV 2026), lip-sync check"],
  ["Read", "Urgency, secrecy, authority, a new bank account, a request for an OTP, in English, Hindi or Hinglish.", "Claude tactic tagger with an offline bilingual fallback, email header and lookalike-domain forensics"],
  ["Recognise", "Does this match the real person: their enrolled voiceprint and face, their channels, hours and approval limits?", "ECAPA voiceprints, ArcFace face match, Org Trust Graph"],
  ["Weigh", "Evidence in log-odds, multiplied by how much damage the request could do, with policy rules as a floor.", "Explainable fusion engine: every point of the score is traceable"],
  ["Verify", "Before anything moves, the real person confirms on the phone they enrolled. A NO holds the payment and files the report.", "Telegram verification, payment hold, CERT-In draft, campaign clustering"],
];

function Hero() {
  const [phase, setPhase] = useState("scanning");
  const flagged = phase === "verdict" || phase === "hold";
  return (
    <section className="relative min-h-[100svh] bg-night text-paper overflow-hidden flex flex-col">
      <Suspense fallback={null}>
        <Spectrogram3D onPhase={setPhase} className="absolute inset-0 top-[18%]" />
      </Suspense>
      <div className="absolute inset-0 bg-[linear-gradient(180deg,#0d1730_8%,transparent_45%,transparent_70%,#0d1730_100%)] pointer-events-none" />
      <div className="absolute inset-0 bg-[linear-gradient(90deg,#0d1730_0%,rgb(13_23_48/0.85)_30%,transparent_62%)] pointer-events-none" />

      <nav className="relative z-10 max-w-7xl w-full mx-auto px-5 sm:px-8 py-5 flex items-center gap-8">
        <span className="wide text-xl font-extrabold">TrustCheck</span>
        <div className="hidden md:flex gap-6 text-paper/75 text-sm">
          <a href="#how" className="hover:text-paper">How it works</a>
          <a href="#maths" className="hover:text-paper">The maths</a>
          <a href="#verify" className="hover:text-paper">Verification</a>
        </div>
        <a href="#/app/check" className="ml-auto bg-paper text-night font-semibold px-4 py-2 rounded hover:bg-mint">Open the console</a>
      </nav>

      <div className="relative z-10 max-w-7xl w-full mx-auto px-5 sm:px-8 pt-[6vh] sm:pt-[9vh]">
        <motion.h1 className="wide font-extrabold leading-[0.95] text-[clamp(2.6rem,7.2vw,6.6rem)] max-w-[14ch]"
          initial="h" animate="s" variants={{ s: { transition: { staggerChildren: 0.12 } } }}>
          {["The voice sounds", "like your CFO.", "The request doesn't."].map((l, i) => (
            <motion.span key={l} className={`block ${i === 2 ? "text-mint" : ""}`}
              variants={{ h: { opacity: 0, y: 28 }, s: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 120, damping: 18 } } }}>{l}</motion.span>
          ))}
        </motion.h1>
        <motion.p className="mt-6 text-lg sm:text-xl text-paper/80 max-w-xl" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.6 }}>
          TrustCheck checks the voice, the face, the words and what's actually being asked, then makes you verify with the real person before money or data moves.
        </motion.p>
        <motion.div className="mt-8 flex flex-wrap gap-3" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.8 }}>
          <a href="#/app/check" className="bg-mint text-night font-bold px-5 py-3 rounded hover:bg-paper">Check a suspicious message</a>
          <a href="#maths" className="border border-paper/40 px-5 py-3 rounded font-semibold hover:border-paper">See how the score works</a>
        </motion.div>
      </div>

      <div className="relative z-10 mt-auto max-w-7xl w-full mx-auto px-5 sm:px-8 pb-8 flex items-end justify-between gap-6">
        <p className="hidden sm:block text-sm text-paper/60 max-w-xs">The landscape is a voice, sliced by frequency. The scan turns the cloned stretch red.</p>
        <div className="ml-auto text-right min-h-[9rem] min-w-[14rem] flex flex-col items-end justify-end gap-3">
          <AnimatePresence>{flagged && <motion.div exit={{ opacity: 0 }}><Stamp band="HIGH" risk={99} size="text-5xl" className="!text-[#ff7a5c] bg-night/40" /></motion.div>}</AnimatePresence>
          <AnimatePresence mode="wait">
            <motion.p key={CAPTION[phase]} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
              className={`text-sm font-semibold ${phase === "scanning" ? "text-paper/70" : "text-[#ff8f74]"}`} aria-live="polite">{CAPTION[phase]}</motion.p>
          </AnimatePresence>
        </div>
      </div>
    </section>
  );
}

export default function Landing() {
  return (
    <div>
      <Hero />

      <section className="paper-grain">
        <div className="max-w-7xl mx-auto px-5 sm:px-8 py-24">
          <h2 className="wide text-4xl sm:text-5xl font-extrabold max-w-[18ch] leading-[1.02]">Spelling mistakes won't save anyone now.</h2>
          <p className="mt-5 text-lg text-ink-soft max-w-2xl">Generated voices and faces are good enough to pass a phone call. The old tells are gone, but the scam still has to ask for something, and that's where we catch it.</p>
          <dl className="mt-14 border-t-2 border-ink">
            {LEDGER.map(([n, d]) => (
              <div key={n} className="grid md:grid-cols-[minmax(0,22rem)_1fr] gap-x-10 gap-y-2 py-7 border-b border-rule">
                <dt className="wide text-4xl sm:text-5xl font-extrabold tnum">{n}</dt>
                <dd className="text-lg max-w-prose self-center">{d}</dd>
              </div>
            ))}
          </dl>
          <p className="mt-4 text-xs text-ink-soft">Sources: Arup case reporting (2024); Ministry of Home Affairs written reply, Rajya Sabha; D3COY problem statement citing Gartner (2026).</p>
        </div>
      </section>

      <section id="maths" className="bg-paper border-t border-rule">
        <div className="max-w-7xl mx-auto px-5 sm:px-8 py-24">
          <h2 className="wide text-4xl sm:text-5xl font-extrabold max-w-[20ch] leading-[1.02]">A perfect deepfake still has to ask for money.</h2>
          <p className="mt-5 text-lg text-ink-soft max-w-2xl mb-12">
            The risk is the evidence that something's fake, multiplied by the damage the request could do. Policy rules set a floor no detector can talk its way under.
            Pick “A perfect fake” and watch the maths say 17, then the rule say HIGH.
          </p>
          <MathsLab />
        </div>
      </section>

      <section id="how" className="bg-night text-paper">
        <div className="max-w-7xl mx-auto px-5 sm:px-8 py-24">
          <h2 className="wide text-4xl sm:text-5xl font-extrabold max-w-[18ch] leading-[1.02]">Five checks, one honest answer.</h2>
          <ol className="mt-14 border-t border-paper/25">
            {PIPELINE.map(([h, d, m], i) => (
              <li key={h} className="grid md:grid-cols-[4rem_16rem_1fr] gap-x-8 gap-y-2 py-7 border-b border-paper/15">
                <span className="wide text-3xl font-extrabold text-mint tnum">{i + 1}</span>
                <h3 className="wide text-2xl font-bold">{h}</h3>
                <div><p className="text-lg text-paper/90 max-w-prose">{d}</p><p className="text-sm text-paper/55 mt-2">{m}</p></div>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section id="verify" className="paper-grain">
        <div className="max-w-7xl mx-auto px-5 sm:px-8 py-24">
          <h2 className="wide text-4xl sm:text-5xl font-extrabold max-w-[18ch] leading-[1.02] mb-14">Don't detect harder. Ask the real person.</h2>
          <PhoneVerify />
        </div>
      </section>

      <section className="bg-paper border-t border-rule">
        <div className="max-w-7xl mx-auto px-5 sm:px-8 py-24 grid lg:grid-cols-2 gap-16">
          <div>
            <h2 className="wide text-3xl sm:text-4xl font-extrabold leading-[1.05]">Built for how India gets scammed.</h2>
            <p className="mt-5 text-lg text-ink-soft max-w-prose">Scams here switch between Hindi and English mid-sentence and arrive on WhatsApp, not email. TrustCheck reads them as they're written.</p>
            <blockquote className="mt-8 bg-sheet border border-rule rounded p-5 text-lg leading-[1.9]">
              Main <u className="decoration-high decoration-[3px] underline-offset-[5px] font-semibold">CBI officer</u> bol raha hoon. Aapke naam pe <u className="decoration-high decoration-[3px] underline-offset-[5px] font-semibold">money laundering</u> case hai.
              Video call pe raho, <u className="decoration-high decoration-[3px] underline-offset-[5px] font-semibold">disconnect mat karna</u>, warna <u className="decoration-high decoration-[3px] underline-offset-[5px] font-semibold">arrest</u>.
              <u className="decoration-high decoration-[3px] underline-offset-[5px] font-semibold">Turant</u> <u className="decoration-high decoration-[3px] underline-offset-[5px] font-semibold">2 lakh</u> UPI karo.
              <footer className="mt-3 text-sm text-high font-bold">HIGH: digital arrest pattern. Real police never arrest anyone over a video call.</footer>
            </blockquote>
          </div>
          <ul className="space-y-8 self-center">
            <li><b className="block text-xl">Forward it to the bot</b><span className="text-ink-soft text-lg">Anyone can forward a voice note or message to the Telegram bot and get a verdict back in English and Hindi, with the 1930 helpline.</span></li>
            <li><b className="block text-xl">CERT-In report in one click</b><span className="text-ink-soft text-lg">Incidents must be reported within 6 hours. TrustCheck pre-fills the draft with every indicator it found.</span></li>
            <li><b className="block text-xl">Biometrics stay put</b><span className="text-ink-soft text-lg">Only voice and face embeddings are kept, never recordings, in line with the DPDP Act 2023.</span></li>
          </ul>
        </div>
      </section>

      <section className="bg-sheet border-t border-rule">
        <div className="max-w-7xl mx-auto px-5 sm:px-8 py-20 grid md:grid-cols-[1fr_1.4fr] gap-12">
          <h2 className="wide text-3xl font-extrabold leading-[1.05]">Where it can be wrong</h2>
          <ul className="space-y-3 text-lg text-ink-soft max-w-prose">
            <li>New voice-cloning tools appear monthly; detectors trained before them will miss some. That's why no single detector decides.</li>
            <li>Phone and WhatsApp compression blur the evidence. We measure and report the drop instead of hiding it.</li>
            <li>A good clone can pass a voiceprint check. It still can't answer “YES” from the real person's phone.</li>
            <li>AI-written text can't be reliably detected, so we judge the manipulation, not who wrote it.</li>
          </ul>
        </div>
      </section>

      <footer className="bg-night text-paper">
        <div className="max-w-7xl mx-auto px-5 sm:px-8 py-20 flex flex-wrap items-end justify-between gap-8">
          <div>
            <p className="wide text-4xl sm:text-5xl font-extrabold max-w-[16ch] leading-[1.02]">Check before you act.</p>
            <p className="mt-4 text-paper/60">Team Semicolons, D3COY 2026, PS 02</p>
          </div>
          <a href="#/app/check" className="bg-mint text-night font-bold px-6 py-3.5 rounded hover:bg-paper">Open the console</a>
        </div>
      </footer>
    </div>
  );
}
