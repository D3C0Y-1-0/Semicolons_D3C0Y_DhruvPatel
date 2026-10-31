// Small line icons for the round rail buttons. 24px grid, stroke follows currentColor.
const P = {
  home: "M4 11.5 12 5l8 6.5V20a1 1 0 0 1-1 1h-4.5v-6h-5v6H5a1 1 0 0 1-1-1z",
  check: "M12 3 5 6v5.5c0 4.2 3 7.8 7 9.5 4-1.7 7-5.3 7-9.5V6zM8.8 12.2l2.2 2.2 4.4-4.6",
  live: "M4 12h2M8 8v8M12 5v14M16 9v6M20 11v2",
  queue: "M4 6h16M4 12h16M4 18h10",
  people: "M9 11a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7zM3 20c.6-3.4 3-5.5 6-5.5s5.4 2.1 6 5.5M16 4.5a3.3 3.3 0 0 1 0 6.3M17.5 14.8c2 .6 3.2 2.4 3.5 5.2",
  arrow: "M7 17 17 7M9 7h8v8",
  phone: "M6.6 3.5 9 3l1.6 4-2 1.3a10 10 0 0 0 5.1 5.1l1.3-2 4 1.6-.5 2.4A2 2 0 0 1 16.6 17 13.6 13.6 0 0 1 3.5 6.9 2 2 0 0 1 6.6 3.5z",
  rupee: "M7 5h10M7 9h10M7 5h3a4 4 0 0 1 0 8H7l7 7",
  user: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4.5 20.5c.8-4 3.8-6.5 7.5-6.5s6.7 2.5 7.5 6.5",
  alert: "M12 4 2.8 19.5h18.4zM12 10v4.5M12 17.2v.3",
};

export default function Icon({ name, className = "size-5" }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden>
      <path d={P[name]} />
    </svg>
  );
}
