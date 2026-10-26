import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// During `npm run dev` the SPA talks to the compose stack through Nginx.
// In production the SPA is served by the same Nginx, so relative URLs just work.
const target = process.env.VITE_API_TARGET ?? "http://localhost:8080";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": { target, changeOrigin: true },
      "/health": { target, changeOrigin: true },
    },
  },
});
