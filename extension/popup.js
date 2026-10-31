const $ = (id) => document.getElementById(id);
let running = false;

async function loadPeople() {
  try {
    const people = await (await fetch($("api").value + "/people")).json();
    $("claimed").innerHTML = '<option value="">Unknown</option>' + people.map((p) => `<option value="${p.id}">${p.name.replace(/</g, "&lt;")}</option>`).join("");
  } catch { $("err").textContent = "Backend not reachable. Start it with: uvicorn app:app --port 8000"; }
}

function show(s) {
  if (!s) return;
  $("out").hidden = false;
  $("band").className = s.band;
  $("band").textContent = `${s.band} ${Math.round(s.risk)}`;
  $("summary").textContent = s.summary;
  $("challenge").hidden = !s.challenge;
  $("challenge").textContent = s.challenge ? "Try now: " + s.challenge : "";
}

function setRunning(r) { running = r; $("toggle").textContent = r ? "Stop listening" : "Listen to this tab"; }

$("toggle").onclick = async () => {
  $("err").textContent = "";
  if (running) { chrome.runtime.sendMessage({ to: "background", type: "stop" }); return setRunning(false); }
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  try {
    const streamId = await chrome.tabCapture.getMediaStreamId({ targetTabId: tab.id });
    chrome.runtime.sendMessage({ to: "background", type: "start", streamId, api: $("api").value, claimed: $("claimed").value });
    setRunning(true);
  } catch (e) { $("err").textContent = e.message; }
};

chrome.storage.session.get(["running", "state"]).then(({ running, state }) => { setRunning(!!running); show(state); });
chrome.storage.session.onChanged.addListener((c) => c.state && show(c.state.newValue));
$("api").onchange = loadPeople;
loadPeople();
