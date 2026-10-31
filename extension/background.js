// Relays between the popup and the offscreen recorder; shows the band on the toolbar badge.
const COLORS = { LOW: "#3e7c59", MEDIUM: "#a8690f", HIGH: "#b42318" };

async function ensureOffscreen() {
  if (await chrome.offscreen.hasDocument()) return;
  await chrome.offscreen.createDocument({ url: "offscreen.html", reasons: ["USER_MEDIA"], justification: "Record call tab audio for deepfake checks" });
}

chrome.runtime.onMessage.addListener((msg) => {
  if (msg.to !== "background") return;
  if (msg.type === "start") {
    ensureOffscreen().then(() => chrome.runtime.sendMessage({ ...msg, to: "offscreen" }));
    chrome.storage.session.set({ running: true, state: null, warned: false });
  }
  if (msg.type === "stop") {
    chrome.runtime.sendMessage({ to: "offscreen", type: "stop" });
    chrome.storage.session.set({ running: false });
    chrome.action.setBadgeText({ text: "" });
  }
  if (msg.type === "update") {
    const s = msg.state;
    chrome.action.setBadgeText({ text: String(Math.round(s.risk)) });
    chrome.action.setBadgeBackgroundColor({ color: COLORS[s.band] });
    chrome.storage.session.get("warned").then(({ warned }) => {
      if (s.band === "HIGH" && !warned) {
        chrome.notifications.create({ type: "basic", iconUrl: "icon.png", title: "TrustCheck: HIGH risk on this call",
          message: (s.challenge ? s.challenge + " " : "") + "Don't pay or share anything until you verify." });
        chrome.storage.session.set({ warned: true });
      }
    });
    chrome.storage.session.set({ state: s });
  }
});
