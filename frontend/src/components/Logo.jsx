import { useId } from "react";

// The TrustCheck mark: a check whose rising stroke is a voice waveform, drawn in the risk heat scale on the
// indigo tile. Same drawing as public/logo.svg (the favicon); ids are made unique so several can share a page.
export default function Logo({ size = 32, className = "", title = "TrustCheck" }) {
  const id = useId().replace(/:/g, "");
  return (
    <svg viewBox="0 0 64 64" width={size} height={size} className={`shrink-0 ${className}`} {...(title ? { role: "img", "aria-label": title } : { "aria-hidden": true })}>
      <defs>
        <linearGradient id={`${id}t`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#33208f" /><stop offset="0.55" stopColor="#1d1356" /><stop offset="1" stopColor="#0e0930" />
        </linearGradient>
        <radialGradient id={`${id}s`} cx="0.28" cy="0.18" r="0.75">
          <stop offset="0" stopColor="#ffffff" stopOpacity="0.22" /><stop offset="0.5" stopColor="#ffffff" stopOpacity="0" />
        </radialGradient>
        <linearGradient id={`${id}h`} x1="14" y1="40" x2="52" y2="14" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#26c6da" /><stop offset="0.3" stopColor="#7c3aed" /><stop offset="0.6" stopColor="#ff2d6f" />
          <stop offset="0.82" stopColor="#ff8a1f" /><stop offset="1" stopColor="#ffd84a" />
        </linearGradient>
        <filter id={`${id}g`} x="-30%" y="-30%" width="160%" height="160%">
          <feGaussianBlur stdDeviation="2.2" result="b" /><feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>
      </defs>
      <rect width="64" height="64" rx="15" fill={`url(#${id}t)`} />
      <rect width="64" height="64" rx="15" fill={`url(#${id}s)`} />
      <rect x="0.75" y="0.75" width="62.5" height="62.5" rx="14.25" fill="none" stroke="#ffffff" strokeOpacity="0.14" strokeWidth="1.5" />
      <g fill="none" stroke={`url(#${id}h)`} strokeLinecap="round" filter={`url(#${id}g)`} transform="translate(-1 4)">
        <path d="M14 34 L24 44" strokeWidth="5.6" />
        <path d="M29.5 33.6 V42.6 M35.5 23.2 V40.2 M41.5 19.8 V30.8 M47.5 8.3 V29.3 M53 8.4 V17.4" strokeWidth="3.6" />
      </g>
    </svg>
  );
}
