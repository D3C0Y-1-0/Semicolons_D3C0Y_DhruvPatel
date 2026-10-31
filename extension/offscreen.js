// Captures the tab's audio, keeps it audible, and streams 3 s Opus chunks to the backend.
let stopAll = () => {};

chrome.runtime.onMessage.addListener(async (msg) => {
  if (msg.to !== "offscreen") return;
  if (msg.type === "stop") return stopAll();
  if (msg.type !== "start") return;
  stopAll();
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: { mandatory: { chromeMediaSource: "tab", chromeMediaSourceId: msg.streamId } },
  });
  const ctx = new AudioContext();
  ctx.createMediaStreamSource(stream).connect(ctx.destination); // capturing mutes the tab otherwise
  const qs = `channel=meet${msg.claimed ? `&claimed_person_id=${msg.claimed}` : ""}`;
  const ws = new WebSocket(`${msg.api.replace(/^http/, "ws")}/live/${crypto.randomUUID()}?${qs}`);
  const rec = new MediaRecorder(stream, { mimeType: "audio/webm;codecs=opus" });
  rec.ondataavailable = (e) => ws.readyState === 1 && e.data.size && ws.send(e.data);
  ws.onopen = () => rec.start(3000);
  ws.onmessage = (e) => chrome.runtime.sendMessage({ to: "background", type: "update", state: JSON.parse(e.data) });
  stopAll = () => {
    if (rec.state !== "inactive") rec.stop();
    stream.getTracks().forEach((t) => t.stop());
    ctx.close();
    ws.close();
    stopAll = () => {};
  };
});
