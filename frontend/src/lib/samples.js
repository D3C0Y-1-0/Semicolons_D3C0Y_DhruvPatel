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
    name: "KYC phishing link",
    channel: "sms",
    sender: "VM-SBIUPD",
    text: "Dear customer, your SBI YONO account will be blocked today due to pending PAN KYC. Update now to avoid suspension: http://sbi-kyc-update.xyz/login",
  },
  {
    name: "Parcel fee link",
    channel: "sms",
    sender: "+91 63000 44120",
    text: "India Post: your parcel is on hold due to incomplete address. Pay Rs 25 redelivery fee within 12 hours at indiapost-redelivery.top/in or it will be returned.",
  },
  {
    name: "Part-time job (Hinglish)",
    channel: "whatsapp",
    sender: "+91 75500 98123",
    text: "Hello ji, part time job hai! YouTube videos like karo aur daily Rs 3000 earn karo. Pehle Rs 999 registration pay karo, Telegram pe tasks milenge. Limited seats, jaldi reply karo.",
  },
  {
    name: "Harmless update",
    channel: "email",
    sender: "rajesh@acme.com",
    text: "Hi team, the quarterly review moves to Thursday 3 pm. Please send me the updated report by Wednesday. Thanks, Rajesh",
  },
];
