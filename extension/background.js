// Relays between the popup and the offscreen recorder; shows the band on the toolbar badge.
const COLORS = { LOW: "#2f8f7a", MEDIUM: "#b7791f", HIGH: "#c2341f" };

async function ensureOffscreen() {
  if (await chrome.offscreen.hasDocument()) return;
  await chrome.offscreen.createDocument({ url: "offscreen.html", reasons: ["USER_MEDIA"], justification: "Record call tab audio for deepfake checks" });
}

// A fresh offscreen page may not be listening yet ("Receiving end does not exist"): retry for ~2 s.
async function sendToOffscreen(msg, tries = 20) {
  try { await chrome.runtime.sendMessage({ ...msg, to: "offscreen" }); } catch (e) {
    if (!tries) throw e;
    await new Promise((r) => setTimeout(r, 100));
    return sendToOffscreen(msg, tries - 1);
  }
}

chrome.runtime.onMessage.addListener((msg) => {
  if (msg.to !== "background") return;
  if (msg.type === "start") {
    ensureOffscreen().then(() => sendToOffscreen(msg));
    chrome.storage.session.set({ running: true, state: null, warned: false });
  }
  if (msg.type === "stop") {
    chrome.runtime.sendMessage({ to: "offscreen", type: "stop" }).catch(() => {}); // no offscreen page = nothing to stop
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
