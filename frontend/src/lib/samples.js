// One-click scenarios for the demo. Names match the seeded Trust Graph (backend/seed.py).
export const SAMPLES = [
  {
    name: "Fake CFO wire",
    channel: "whatsapp",
    sender: "+91 90000 12345",
    text: "Hi Priya, Rajesh here (CFO). I'm in a board meeting so can't call. This is urgent and confidential: transfer ₹45,00,000 to our new vendor account below within 30 minutes. Don't discuss with anyone, just message me here on WhatsApp once done.\nA/c 5021 0098 7712, IFSC HDFC0001234",
  },
  {
    name: "Digital arrest (Hinglish)",
    channel: "phone",
    sender: "+91 70000 55511",
    text: "Main CBI officer bol raha hoon. Aapke naam pe money laundering case hai aur arrest warrant nikla hai. Video call pe raho, disconnect mat karna. Turant 2 lakh UPI karo verification ke liye, warna police ghar aa jayegi.",
  },
  {
    name: "CEO asks for OTP",
    channel: "sms",
    sender: "+91 81234 00000",
    text: "Ananya here. Locked out of the bank portal before the audit, need the OTP you just received immediately. Keep this between us please.",
  },
  {
    name: "Harmless update",
    channel: "email",
    sender: "rajesh@acme.com",
    text: "Hi team, the quarterly review moves to Thursday 3 pm. Please send me the updated report by Wednesday. Thanks, Rajesh",
  },
];
