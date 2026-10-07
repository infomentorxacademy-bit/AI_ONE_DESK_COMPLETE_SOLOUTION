// vite.config.ts : build + dev-server settings.
//  * plugin-react       : lets Vite understand JSX/TSX.
//  * server.proxy       : in dev, every request to /api/... is forwarded to the FastAPI backend on port 8000,
//                         so the browser sees ONE origin (no CORS problems) and the code just calls "/api/...".
//  * test               : settings for `npm test` (Vitest runs component tests in a fake browser, jsdom).
import { defineConfig } from "vitest/config";   // same as vite's defineConfig, plus the `test` section
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": { target: process.env.VITE_API_TARGET ?? "http://127.0.0.1:8000", changeOrigin: true } },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    globals: true,
    css: false,
  },
});
