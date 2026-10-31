import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// css.postcss inline: stops Vite picking up a stray postcss.config.js from a parent folder (Tailwind v4 runs as a plugin)
export default defineConfig({ plugins: [react(), tailwindcss()], css: { postcss: {} } });
