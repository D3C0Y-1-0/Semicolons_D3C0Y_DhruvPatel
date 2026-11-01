import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { useEffect, useState } from "react";
import Dock from "../components/Dock.jsx";
import Icon from "../components/Icons.jsx";
import MathsLab from "./MathsLab.jsx";
import PhoneVerify from "./PhoneVerify.jsx";
import {
  Chapter, WorldDefs, HERO_LAYERS, HERO_LIP, PROBLEM_LAYERS, PROBLEM_LIP, MATHS_LAYERS, MATHS_LIP,
  HOW_LAYERS, HOW_LIP, VERIFY_LAYERS, VERIFY_LIP, INDIA_LAYERS, INDIA_LIP, DAWN_LAYERS,
} from "./World.jsx";

// What the floating call card says as the scan crosses the voice
const CALL = {
  scanning: { risk: 4, line: "Listening to the call…" },
  flagging: { risk: 61, line: "0:41 to 0:52: harmonics too regular for a human voice" },
  verdict: { risk: 99, line: "Cloned voice, and the request breaks payment policy" },
  hold: { risk: 99, line: "Cloned voice, and the request breaks payment policy" },
};

const LEDGER = [
  ["US$25M", "paid out by one finance employee in Hong Kong (Feb 2024) after a video call in which every colleague, including the CFO, was a deepfake."],
  ["₹1,935 cr", "lost by Indians to “digital arrest” scams in 2024, across 1.23 lakh complaints: fake police and CBI officers on video calls."],
  ["41%", "of CISOs surveyed by Gartner in September 2026 had already seen a deepfake in an employee audio call."],
];

const PIPELINE = [
  ["Listen and look", "Is the voice cloned? Is the face swapped? Do the lips follow the words?", "pellav2 voice detector, GenD face detector (WACV 2026), lip-sync check"],
  ["Read", "Urgency, secrecy, authority, a new bank account, a request for an OTP, in English, Hindi or Hinglish.", "Tactic tagger with a bilingual lexicon, email header and lookalike-domain forensics"],
  ["Recognise", "Does this match the real person: their voiceprint and face, their channels, hours and approval limits?", "ECAPA voiceprints, ArcFace face match, Org Trust Graph"],
  ["Weigh", "Evidence in log-odds, multiplied by how much damage the request could do, with policy rules as a floor.", "Every point of the score is traceable"],
  ["Verify", "Before anything moves, the real person confirms on the phone they enrolled. A NO holds the payment.", "YES/NO by email or QR, payment hold, CERT-In draft, campaign clustering"],
];

const NAV = [["The problem", "#problem"], ["The maths", "#maths"], ["How it works", "#how"], ["Verify", "#verify"]];

// text rises into place as each chapter arrives
function Reveal({ children, delay = 0, className = "" }) {
  return (
    <motion.div className={className} initial={{ opacity: 0, y: 46 }} whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-12% 0px" }} transition={{ duration: 1.1, ease: [0.2, 0.8, 0.2, 1], delay }}>
      {children}
    </motion.div>
  );
}

const Kicker = ({ n, children }) => (
  <p className="flex items-center gap-3 text-sm font-semibold tracking-[0.18em] uppercase text-white/70">
    <span className="tnum">{n}</span><span className="h-px w-10 bg-white/50" />{children}
  </p>
);
const Title = ({ children, className = "" }) => (
  <h2 className={`font-display font-semibold tracking-[-0.02em] leading-[0.95] text-white text-[clamp(2.6rem,6.4vw,6rem)] drop-shadow-[0_4px_30px_rgb(10_6_40/0.45)] ${className}`}>{children}</h2>
);

function useCallPhase() {
  const reduced = useReducedMotion();
  const [phase, setPhase] = useState(reduced ? "hold" : "scanning");
  useEffect(() => {
    if (reduced) return;
    const start = performance.now();
    const id = setInterval(() => {
      const t = ((performance.now() - start) / 1000) % 7.5;
      setPhase(t < 4.1 ? "scanning" : t < 5.3 ? "flagging" : "verdict");
    }, 200);
    return () => clearInterval(id);
  }, [reduced]);
  return phase;
}

function Hero() {
  const phase = useCallPhase();
  const call = CALL[phase];
  const hot = phase !== "scanning";
  return (
    <Chapter z={7} layers={HERO_LAYERS} lip={HERO_LIP} bg="#1d1656" className="h-[100svh] min-h-[38rem]">
      <header className="flex items-center justify-between gap-6 px-5 sm:px-10 pt-6 text-white">
        <a href="#/" className="font-display text-2xl font-bold tracking-tight">TrustCheck</a>
        <nav aria-label="Sections" className="hidden md:flex gap-9 text-sm font-semibold text-white/80">
          {NAV.map(([l, h]) => <a key={h} href={h} className="hover:text-white">{l}</a>)}
        </nav>
        <a href="#/app/check" className="border border-white/70 rounded-md px-4 py-2 text-sm font-semibold hover:bg-white hover:text-night transition-colors">Open console</a>
      </header>

      <div className="px-5 sm:px-10 pt-[9vh] sm:pt-[11vh] max-w-[60rem]">
        <motion.p initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 1, delay: 0.2 }}
          className="flex items-center gap-3 text-white/85 font-semibold">
          <Icon name="live" className="size-5" />PS 02: deepfake-enabled social engineering
        </motion.p>
        <motion.h1 initial={{ opacity: 0, y: 40 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 1.2, ease: [0.2, 0.8, 0.2, 1] }}
          className="mt-5 font-display font-semibold text-white tracking-[-0.03em] leading-[0.88] text-[clamp(3.2rem,8vw,8.2rem)] drop-shadow-[0_6px_40px_rgb(20_10_60/0.45)]">
          Check before<br />you act.
        </motion.h1>
        <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 1, delay: 0.5 }} className="mt-6 text-white/90 max-w-md leading-relaxed">
          The voice sounds like your CFO. The request doesn't. TrustCheck checks the voice, the face, the words and what's actually being asked,
          then makes you verify with the real person before money or data moves.
        </motion.p>
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.9, delay: 0.7 }} className="mt-8 flex flex-wrap gap-3">
          <a href="#problem" className="bg-white text-night rounded-md px-5 py-3 font-bold inline-flex items-center gap-3 shadow-[0_14px_30px_-12px_rgb(10_6_40/0.6)]">
            Start the journey<Icon name="arrow" className="size-4 rotate-90" />
          </a>
          <a href="#/app/check" className="border border-white/70 text-white rounded-md px-5 py-3 font-bold hover:bg-white/15">Check a message</a>
        </motion.div>
      </div>

      {/* the call the person in the grass is taking, scanned live */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 1, delay: 1 }}
        className="absolute right-4 sm:right-[6%] top-[22vh] sm:top-[26vh] w-[min(20rem,calc(100%-2rem))] glass-strong text-ink rounded-[1.5rem] p-5 hidden sm:block">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-lg font-bold leading-tight">Incoming: Rajesh Kumar</p>
            <p className="text-sm text-ink-soft flex items-center gap-1.5 mt-1"><Icon name="phone" className="size-4" />WhatsApp video, +91 90000 12345</p>
          </div>
          <span className={`orb size-11 shrink-0 font-extrabold tnum text-sm text-white transition-colors duration-500 ${call.risk >= 60 ? "bg-high" : "bg-night"}`} aria-label={`Risk ${call.risk}`}>{call.risk}</span>
        </div>
        <AnimatePresence mode="wait">
          <motion.p key={call.line} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            className={`mt-3 text-sm font-semibold min-h-[2.5rem] ${hot ? "text-high" : "text-ink-soft"}`} aria-live="polite">{call.line}</motion.p>
        </AnimatePresence>
        <ul className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1.5 text-sm">
          <li className="flex items-center gap-2"><Icon name="live" className="size-4 text-ink-soft" />Voice {hot ? "0.99 fake" : "checking"}</li>
          <li className="flex items-center gap-2"><Icon name="alert" className="size-4 text-ink-soft" />New account</li>
          <li className="flex items-center gap-2"><Icon name="rupee" className="size-4 text-ink-soft" />Over ₹10 lakh</li>
          <li className="flex items-center gap-2"><Icon name="phone" className="size-4 text-ink-soft" />Unusual channel</li>
        </ul>
      </motion.div>
    </Chapter>
  );
}

export default function Landing() {
  return (
    <div className="overflow-x-clip bg-[#0f0b2c] text-white">
      <WorldDefs />
      <Hero />
      <Dock current="home" />

      <Chapter id="problem" z={6} layers={PROBLEM_LAYERS} lip={PROBLEM_LIP} bg="#130f3a" className="min-h-[125svh]">
        <div className="px-5 sm:px-10 pt-[26vw] sm:pt-[22vw] lg:pt-[16vw] pb-[24vw] lg:ml-auto lg:w-[48%] lg:pr-[6%]">
          <Reveal><Kicker n="01">The problem</Kicker></Reveal>
          <Reveal delay={0.1}><Title className="mt-5">Spelling mistakes won't save anyone now.</Title></Reveal>
          <Reveal delay={0.2}><p className="mt-6 text-lg text-white/80 max-w-lg">Generated voices and faces pass a phone call. The old tells are gone, but the scam still has to ask for something, and that's where we catch it.</p></Reveal>
          <dl className="mt-12 divide-y divide-white/15 border-y border-white/15">
            {LEDGER.map(([n, d], i) => (
              <Reveal key={n} delay={0.15 * i} className="py-6 grid sm:grid-cols-[12.5rem_1fr] gap-x-6 gap-y-1 items-baseline">
                <dt className="font-display text-4xl sm:text-[2.7rem] font-semibold tnum text-[#ffcf8a] whitespace-nowrap">{n}</dt>
                <dd className="text-white/75 leading-relaxed">{d}</dd>
              </Reveal>
            ))}
          </dl>
          <p className="mt-4 text-xs text-white/50">Sources: Arup case reporting (2024); Ministry of Home Affairs, Rajya Sabha reply; D3COY problem statement citing Gartner (2026).</p>
        </div>
      </Chapter>

      <Chapter id="maths" z={5} layers={MATHS_LAYERS} lip={MATHS_LIP} bg="#0f0b2c" className="min-h-[130svh]">
        <div className="px-5 sm:px-10 pt-[20vw] lg:pt-[13vw] pb-[22vw] max-w-[88rem] mx-auto text-ink">
          <Reveal><Kicker n="02">The maths</Kicker></Reveal>
          <Reveal delay={0.1}><Title className="mt-5 max-w-[16ch]">A perfect deepfake still has to ask for money.</Title></Reveal>
          <Reveal delay={0.2}><p className="mt-6 text-lg text-white/80 max-w-2xl mb-12">The risk is the evidence that something's fake, multiplied by the damage the request could do. Policy rules set a floor no detector can talk its way under. Pick “A perfect fake”: the maths says 17, the rule says HIGH.</p></Reveal>
          <Reveal delay={0.25}><MathsLab /></Reveal>
        </div>
      </Chapter>

      <Chapter id="how" z={4} layers={HOW_LAYERS} lip={HOW_LIP} bg="#0f0b2c" className="min-h-[125svh]">
        <div className="px-5 sm:px-10 pt-[18vw] lg:pt-[12vw] pb-[42vw] max-w-[88rem] mx-auto">
          <Reveal><Kicker n="03">How it works</Kicker></Reveal>
          <Reveal delay={0.1}><Title className="mt-5 max-w-[14ch]">Five lanterns, one honest answer.</Title></Reveal>
          <ol className="mt-12 grid md:grid-cols-5 gap-8 md:gap-6">
            {PIPELINE.map(([h, d, m], i) => (
              <Reveal key={h} delay={0.12 * i} className="border-t border-white/30 pt-5">
                <span className="font-display text-5xl font-semibold text-[#ffd27a] tnum">{i + 1}</span>
                <h3 className="mt-3 text-xl font-bold">{h}</h3>
                <p className="mt-2 text-white/80 text-sm leading-relaxed">{d}</p>
                <p className="mt-3 text-xs text-white/55">{m}</p>
              </Reveal>
            ))}
          </ol>
        </div>
      </Chapter>

      <Chapter id="verify" z={3} layers={VERIFY_LAYERS} lip={VERIFY_LIP} bg="#130e38" className="min-h-[125svh]">
        <div className="px-5 sm:px-10 pt-[16vw] lg:pt-[11vw] pb-[20vw] max-w-[80rem] mx-auto">
          <Reveal className="text-center"><div className="flex justify-center"><Kicker n="04">Verify</Kicker></div></Reveal>
          <Reveal delay={0.1}><Title className="mt-5 text-center mx-auto max-w-[16ch]">Don't detect harder. Ask the real person.</Title></Reveal>
          <Reveal delay={0.2} className="mt-14"><PhoneVerify /></Reveal>
        </div>
      </Chapter>

      <Chapter id="india" z={2} layers={INDIA_LAYERS} lip={INDIA_LIP} bg="#1a1446" className="min-h-[125svh]">
        <div className="px-5 sm:px-10 pt-[16vw] lg:pt-[11vw] pb-[22vw] max-w-[88rem] mx-auto grid lg:grid-cols-2 gap-12 lg:gap-16">
          <div>
            <Reveal><Kicker n="05">Bharat-ready</Kicker></Reveal>
            <Reveal delay={0.1}><Title className="mt-5">Built for how India gets scammed.</Title></Reveal>
            <Reveal delay={0.2}><p className="mt-6 text-lg text-white/85 max-w-prose">Scams here switch between Hindi and English mid-sentence and arrive on WhatsApp, not email. TrustCheck reads them as they're written.</p></Reveal>
            <Reveal delay={0.3}>
              <blockquote className="mt-8 glass-strong rounded-[2rem] p-6 text-lg leading-[1.9] text-ink">
                Main <u className="decoration-high decoration-[3px] underline-offset-[5px] font-semibold">CBI officer</u> bol raha hoon. Aapke naam pe <u className="decoration-high decoration-[3px] underline-offset-[5px] font-semibold">money laundering</u> case hai.
                Video call pe raho, <u className="decoration-high decoration-[3px] underline-offset-[5px] font-semibold">disconnect mat karna</u>, warna <u className="decoration-high decoration-[3px] underline-offset-[5px] font-semibold">arrest</u>.
                <u className="decoration-high decoration-[3px] underline-offset-[5px] font-semibold">Turant</u> <u className="decoration-high decoration-[3px] underline-offset-[5px] font-semibold">2 lakh</u> UPI karo.
                <footer className="mt-3 text-sm text-high font-bold">HIGH: digital arrest pattern. Real police never arrest anyone over a video call.</footer>
              </blockquote>
            </Reveal>
          </div>
          <ul className="grid gap-8 self-end lg:pb-10">
            {[["Forward it to the bot", "Anyone can forward a voice note or message to the Telegram bot and get a verdict back in English and Hindi, with the 1930 helpline."],
              ["CERT-In report in one click", "Incidents must be reported within 6 hours. TrustCheck pre-fills the draft with every indicator it found."],
              ["Biometrics stay put", "Only voice and face embeddings are kept, never recordings, in line with the DPDP Act 2023."]].map(([h, d], i) => (
              <Reveal key={h} delay={0.15 * i} className="border-l-2 border-[#ffcf8a]/70 pl-5">
                <b className="block font-display text-2xl font-semibold">{h}</b><span className="text-white/80">{d}</span>
              </Reveal>
            ))}
          </ul>
        </div>
      </Chapter>

      <Chapter id="dawn" z={1} layers={DAWN_LAYERS} bg="#1e1850" className="min-h-[150svh]">
        <div className="px-5 sm:px-10 pt-[14vw] lg:pt-[9vw] max-w-[88rem] mx-auto grid md:grid-cols-[1fr_1.4fr] gap-10">
          <Reveal><Kicker n="06">Honest limits</Kicker><Title className="mt-5 !text-[clamp(2.2rem,4.6vw,4.2rem)]">Where it can be wrong</Title></Reveal>
          <ul className="space-y-4 text-lg text-white/85 max-w-prose md:pt-10">
            {["New voice-cloning tools appear monthly; detectors trained before them will miss some. That's why no single detector decides.",
              "Phone and WhatsApp compression blur the evidence. We measure and report the drop instead of hiding it.",
              "A good clone can pass a voiceprint check. It still can't answer “YES” from the real person's phone.",
              "AI-written text can't be reliably detected, so we judge the manipulation, not who wrote it."].map((t, i) => <Reveal key={i} delay={0.1 * i}><li>{t}</li></Reveal>)}
          </ul>
        </div>
        <div className="px-5 sm:px-10 pt-[30vh] pb-[24vh] text-center">
          <Reveal>
            <p className="font-display font-semibold tracking-[-0.03em] leading-[0.9] text-[clamp(3.2rem,9vw,8.5rem)] text-white drop-shadow-[0_6px_40px_rgb(120_40_80/0.45)]">Check before you act.</p>
            <p className="mt-4 text-night/80 font-semibold">Team Semicolons, D3COY 2026, PS 02</p>
            <a href="#/app/check" className="mt-8 bg-night text-white rounded-md pl-6 pr-2 py-2 font-bold inline-flex items-center gap-3 text-lg shadow-[0_20px_40px_-16px_rgb(35_22_94/0.7)]">
              Open the console<span className="orb size-10 bg-white text-night"><Icon name="arrow" /></span>
            </a>
          </Reveal>
        </div>
      </Chapter>
    </div>
  );
}
