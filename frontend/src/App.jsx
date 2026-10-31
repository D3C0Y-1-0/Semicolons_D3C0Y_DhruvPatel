import { useEffect, useState } from "react";
import AppShell from "./app/AppShell.jsx";
import Landing from "./landing/Landing.jsx";

// Hash routes: #/ = landing, #/app/<page> = console. Plain section anchors (#maths) stay on the landing page.
const route = () => {
  const m = location.hash.match(/^#\/app\/(\w+)/);
  return m ? m[1] : null;
};

export default function App() {
  const [page, setPage] = useState(route());
  useEffect(() => {
    const on = () => { const p = route(); setPage(p); if (p || location.hash === "#/") window.scrollTo(0, 0); };
    addEventListener("hashchange", on);
    return () => removeEventListener("hashchange", on);
  }, []);
  return page ? <AppShell page={page} /> : <Landing />;
}
