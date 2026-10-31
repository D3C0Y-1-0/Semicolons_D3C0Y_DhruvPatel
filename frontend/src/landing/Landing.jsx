import { AnimatePresence, motion } from "framer-motion";
import { lazy, Suspense, useState } from "react";
import Dock from "../components/Dock.jsx";
import Icon from "../components/Icons.jsx";
import MathsLab from "./MathsLab.jsx";
import PhoneVerify from "./PhoneVerify.jsx";

const Spectrogram3D = lazy(() => import("../components/Spectrogram3D.jsx"));

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
  ["Verify", "Before anything moves, the real person confirms on the phone they enrolled. A NO holds the payment.", "Telegram YES/NO, payment hold, CERT-In draft, campaign clustering"],
];

function Hero() {
  const [phase, setPhase] = useState("scanning");
  const call = CALL[phase];
  const hot = phase !== "scanning";
  return (
    <section className="relative min-h-[100svh] px-3 sm:px-6 pt-16 pb-28 lg:pb-24 flex flex-col">
      {/* outer corners, like a print */}
      <div className="absolute inset-x-4 sm:inset-x-8 top-4 flex justify-between text-sm sm:text-base">
        <a href="#/" className="text-xl font-extrabold tracking-tight">TrustCheck</a>
        <span className="text-ink-soft font-semibold">Team Semicolons, D3COY 2026</span>
      </div>

      <div className="frame dusk relative flex-1 max-w-[88rem] w-full mx-auto overflow-hidden min-h-[40rem]">
        <Suspense fallback={null}>
          <Spectrogram3D onPhase={setPhase} className="absolute inset-x-0 bottom-0 top-[28%]" />
        </Suspense>

        {/* top bar: what this call claims */}
        <div className="relative z-10 flex items-start justify-between gap-3 p-3 sm:p-5">
          <a href="#how" className="glass-strong rounded-full pl-5 pr-2 py-2 font-semibold hidden sm:inline-flex items-center gap-3">
            How it works<span className="orb size-8 bg-night text-white"><Icon name="arrow" className="size-4" /></span>
          </a>
          <dl className="glass-strong rounded-full px-5 py-2.5 hidden md:flex gap-7 text-sm">
            {[["phone", "Arrived via", "WhatsApp video"], ["user", "Claims to be", "Rajesh Kumar, CFO"], ["rupee", "Asking for", "₹45,00,000"]].map(([ic, k, v]) => (
              <div key={k} className="flex items-center gap-2.5">
                <Icon name={ic} className="size-4 text-ink-soft" />
                <div><dt className="text-[0.7rem] text-ink-soft leading-none">{k}</dt><dd className="font-bold">{v}</dd></div>
              </div>
            ))}
          </dl>
          <a href="#/app/check" className="glass-strong rounded-full pl-5 pr-2 py-2 font-semibold inline-flex items-center gap-3 ml-auto md:ml-0">
            Open console<span className="orb size-8 bg-night text-white"><Icon name="arrow" className="size-4" /></span>
          </a>
        </div>

        <motion.h1 className="relative z-[5] text-center text-white font-semibold tracking-[-0.04em] leading-[0.92] px-4 mt-4 sm:mt-6 text-[clamp(2.4rem,6.3vw,6.6rem)] drop-shadow-[0_2px_30px_rgb(35_22_94/0.25)]"
          initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.9, ease: [0.2, 0.8, 0.2, 1] }}>
          <span className={`block opacity-90 ${phase === "flagging" ? "glitching" : ""}`}>The voice sounds like your CFO.</span>
          <span className={`block transition-colors duration-700 ${hot ? "text-night" : "text-white/70"}`}>The request doesn't.</span>
        </motion.h1>

        {/* bottom-left: the pitch, with a cut-out corner */}
        <div className="absolute z-10 left-0 bottom-0 w-[min(26rem,100%)] glass-strong rounded-tr-[2.75rem] p-6 sm:p-7 hidden lg:block">
          <h2 className="text-xl font-bold">Check before you act</h2>
          <p className="mt-2 text-sm text-ink-soft leading-relaxed">TrustCheck checks the voice, the face, the words and what's actually being asked, then makes you verify with the real person before money or data moves.</p>
          <div className="mt-5 flex items-end justify-between gap-4">
            <p><span className="block text-5xl font-extrabold tracking-tight tnum">₹1,935 cr</span><span className="text-sm font-semibold">lost to digital-arrest scams in 2024</span></p>
            <a href="#problem" aria-label="Read about the problem" className="orb size-12 bg-white border border-rule hover:bg-sheet shrink-0"><Icon name="arrow" /></a>
          </div>
        </div>

        {/* right: the call being scanned, live */}
        <div className="absolute z-10 right-3 sm:right-5 bottom-24 lg:bottom-5 w-[min(21rem,calc(100%-1.5rem))] glass rounded-[2rem] p-5 sm:p-6">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-lg font-bold leading-tight">Incoming: Rajesh Kumar</p>
              <p className="text-sm text-ink-soft flex items-center gap-1.5 mt-1"><Icon name="phone" className="size-4" />WhatsApp video, +91 90000 12345</p>
            </div>
            <span className={`orb size-11 shrink-0 font-extrabold tnum text-sm text-white transition-colors duration-500 ${call.risk >= 60 ? "bg-high" : "bg-night"}`} aria-label={`Risk ${call.risk}`}>{call.risk}</span>
          </div>
          <AnimatePresence mode="wait">
            <motion.p key={call.line} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
              className={`mt-4 text-sm font-semibold min-h-[2.5rem] ${hot ? "text-high" : "text-ink-soft"}`} aria-live="polite">{call.line}</motion.p>
          </AnimatePresence>
          <ul className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
            <li className="flex items-center gap-2"><Icon name="live" className="size-4 text-ink-soft" />Voice {hot ? "0.99 fake" : "checking"}</li>
            <li className="flex items-center gap-2"><Icon name="alert" className="size-4 text-ink-soft" />New account</li>
            <li className="flex items-center gap-2"><Icon name="rupee" className="size-4 text-ink-soft" />Over ₹10 lakh limit</li>
            <li className="flex items-center gap-2"><Icon name="phone" className="size-4 text-ink-soft" />Unusual channel</li>
          </ul>
        </div>
      </div>

      <div className="absolute inset-x-4 sm:inset-x-8 bottom-8 flex justify-between items-center text-sm sm:text-base">
        <span className="font-semibold text-ink-soft hidden lg:inline">PS 02: deepfake-enabled social engineering</span>
        <a href="#problem" className="ml-auto border border-ink/40 rounded-full px-5 py-1.5 font-semibold hover:bg-white/50 hidden lg:inline-block">Scroll down</a>
      </div>
    </section>
  );
}

// A section is its own framed panel on the misty backdrop
const Panel = ({ id, className = "", children }) => (
  <section id={id} className="px-3 sm:px-6 py-4">
    <div className={`frame max-w-[88rem] mx-auto overflow-hidden ${className}`}>{children}</div>
  </section>
);

export default function Landing() {
  return (
    <div className="pb-28">
      <Hero />
      <Dock current="home" />

      <Panel id="problem" className="bg-white/60 backdrop-blur-xl">
        <div className="p-6 sm:p-12 lg:p-16 grid lg:grid-cols-[1fr_1.3fr] gap-10 lg:gap-16">
          <div>
            <h2 className="text-4xl sm:text-6xl font-bold tracking-[-0.04em] leading-[0.95]">Spelling mistakes won't save anyone now.</h2>
            <p className="mt-6 text-lg text-ink-soft max-w-md">Generated voices and faces pass a phone call. The old tells are gone, but the scam still has to ask for something, and that's where we catch it.</p>
          </div>
          <dl className="grid gap-3">
            {LEDGER.map(([n, d], i) => (
              <div key={n} className={`rounded-[2rem] p-6 sm:p-7 grid sm:grid-cols-[11rem_1fr] gap-x-6 gap-y-1 items-center ${i === 0 ? "bg-night text-white" : "glass-strong"}`}>
                <dt className="text-4xl sm:text-5xl font-extrabold tracking-tight tnum">{n}</dt>
                <dd className={i === 0 ? "text-white/80" : "text-ink-soft"}>{d}</dd>
              </div>
            ))}
            <p className="text-xs text-ink-soft px-2">Sources: Arup case reporting (2024); Ministry of Home Affairs, Rajya Sabha reply; D3COY problem statement citing Gartner (2026).</p>
          </dl>
        </div>
      </Panel>

      <Panel id="maths" className="dusk">
        <div className="p-6 sm:p-12 lg:p-16">
          <h2 className="text-4xl sm:text-6xl font-bold tracking-[-0.04em] leading-[0.95] text-white max-w-[16ch] drop-shadow-[0_2px_24px_rgb(35_22_94/0.25)]">A perfect deepfake still has to ask for money.</h2>
          <p className="mt-5 text-lg text-ink max-w-2xl mb-10">The risk is the evidence that something's fake, multiplied by the damage the request could do. Policy rules set a floor no detector can talk its way under. Pick “A perfect fake”: the maths says 17, the rule says HIGH.</p>
          <MathsLab />
        </div>
      </Panel>

      <Panel id="how" className="bg-night text-white">
        <div className="p-6 sm:p-12 lg:p-16">
          <h2 className="text-4xl sm:text-6xl font-bold tracking-[-0.04em] leading-[0.95] max-w-[14ch]">Five checks, one honest answer.</h2>
          <ol className="mt-12 grid md:grid-cols-5 gap-3">
            {PIPELINE.map(([h, d, m], i) => (
              <li key={h} className="rounded-[1.75rem] bg-white/[0.07] border border-white/15 p-5 flex flex-col">
                <span className="orb size-10 bg-white text-night font-extrabold tnum">{i + 1}</span>
                <h3 className="mt-5 text-xl font-bold">{h}</h3>
                <p className="mt-2 text-white/80 text-sm leading-relaxed">{d}</p>
                <p className="mt-auto pt-4 text-xs text-white/55">{m}</p>
              </li>
            ))}
          </ol>
        </div>
      </Panel>

      <Panel id="verify" className="bg-white/60 backdrop-blur-xl">
        <div className="p-6 sm:p-12 lg:p-16">
          <h2 className="text-4xl sm:text-6xl font-bold tracking-[-0.04em] leading-[0.95] max-w-[16ch] mb-12">Don't detect harder. Ask the real person.</h2>
          <PhoneVerify />
        </div>
      </Panel>

      <Panel className="dusk">
        <div className="p-6 sm:p-12 lg:p-16 grid lg:grid-cols-2 gap-10 lg:gap-16">
          <div>
            <h2 className="text-4xl sm:text-5xl font-bold tracking-[-0.04em] leading-[0.95] text-white drop-shadow-[0_2px_24px_rgb(35_22_94/0.25)]">Built for how India gets scammed.</h2>
            <p className="mt-5 text-lg max-w-prose">Scams here switch between Hindi and English mid-sentence and arrive on WhatsApp, not email. TrustCheck reads them as they're written.</p>
            <blockquote className="mt-8 glass-strong rounded-[2rem] p-6 text-lg leading-[1.9]">
              Main <u className="decoration-high decoration-[3px] underline-offset-[5px] font-semibold">CBI officer</u> bol raha hoon. Aapke naam pe <u className="decoration-high decoration-[3px] underline-offset-[5px] font-semibold">money laundering</u> case hai.
              Video call pe raho, <u className="decoration-high decoration-[3px] underline-offset-[5px] font-semibold">disconnect mat karna</u>, warna <u className="decoration-high decoration-[3px] underline-offset-[5px] font-semibold">arrest</u>.
              <u className="decoration-high decoration-[3px] underline-offset-[5px] font-semibold">Turant</u> <u className="decoration-high decoration-[3px] underline-offset-[5px] font-semibold">2 lakh</u> UPI karo.
              <footer className="mt-3 text-sm text-high font-bold">HIGH: digital arrest pattern. Real police never arrest anyone over a video call.</footer>
            </blockquote>
          </div>
          <ul className="grid gap-3 self-center">
            {[["Forward it to the bot", "Anyone can forward a voice note or message to the Telegram bot and get a verdict back in English and Hindi, with the 1930 helpline."],
              ["CERT-In report in one click", "Incidents must be reported within 6 hours. TrustCheck pre-fills the draft with every indicator it found."],
              ["Biometrics stay put", "Only voice and face embeddings are kept, never recordings, in line with the DPDP Act 2023."]].map(([h, d]) => (
              <li key={h} className="glass rounded-[2rem] p-6"><b className="block text-xl">{h}</b><span className="text-ink-soft">{d}</span></li>
            ))}
          </ul>
        </div>
      </Panel>

      <Panel className="bg-white/60 backdrop-blur-xl">
        <div className="p-6 sm:p-12 lg:p-16 grid md:grid-cols-[1fr_1.4fr] gap-10">
          <h2 className="text-3xl sm:text-5xl font-bold tracking-[-0.04em] leading-[0.95]">Where it can be wrong</h2>
          <ul className="space-y-4 text-lg text-ink-soft max-w-prose">
            <li>New voice-cloning tools appear monthly; detectors trained before them will miss some. That's why no single detector decides.</li>
            <li>Phone and WhatsApp compression blur the evidence. We measure and report the drop instead of hiding it.</li>
            <li>A good clone can pass a voiceprint check. It still can't answer “YES” from the real person's phone.</li>
            <li>AI-written text can't be reliably detected, so we judge the manipulation, not who wrote it.</li>
          </ul>
        </div>
      </Panel>

      <Panel className="bg-night text-white">
        <div className="p-8 sm:p-14 flex flex-wrap items-end justify-between gap-8">
          <div>
            <p className="text-5xl sm:text-7xl font-bold tracking-[-0.04em] leading-[0.92]">Check before you act.</p>
            <p className="mt-4 text-white/60">Team Semicolons, D3COY 2026, PS 02</p>
          </div>
          <a href="#/app/check" className="bg-white text-night rounded-full pl-6 pr-2 py-2 font-bold inline-flex items-center gap-3 text-lg">
            Open the console<span className="orb size-10 bg-night text-white"><Icon name="arrow" /></span>
          </a>
        </div>
      </Panel>
    </div>
  );
}
