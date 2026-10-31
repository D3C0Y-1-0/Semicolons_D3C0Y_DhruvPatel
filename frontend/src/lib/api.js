export const API = import.meta.env.VITE_API || "http://localhost:8000";
export const WS = API.replace(/^http/, "ws");

export async function api(path, opts = {}) {
  const res = await fetch(API + path, opts);
  const body = res.headers.get("content-type")?.includes("json") ? await res.json() : await res.text();
  if (!res.ok) throw new Error(body?.detail || body || res.statusText);
  return body;
}

export const form = (obj) => {
  const f = new FormData();
  for (const [k, v] of Object.entries(obj)) if (v !== undefined && v !== null && v !== "") f.append(k, v);
  return f;
};
