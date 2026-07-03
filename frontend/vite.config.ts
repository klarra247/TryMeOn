import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

// /api, /media 는 FastAPI(8000)로 프록시 — 프론트는 상대 경로만 쓴다.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@shared": path.resolve(__dirname, "../shared") },
  },
  server: {
    fs: { allow: [".", "../shared"] },
    proxy: {
      "/api": "http://localhost:8000",
      "/media": "http://localhost:8000",
    },
  },
});
