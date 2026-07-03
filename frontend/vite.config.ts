import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

// /api, /media 는 백엔드로 프록시 — 프론트는 상대 경로만 쓴다.
// 원격 GPU pod 토폴로지(Phase 1): VITE_API_TARGET=https://<pod-id>-8000.proxy.runpod.net
const target = process.env.VITE_API_TARGET ?? "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@shared": path.resolve(__dirname, "../shared") },
  },
  server: {
    fs: { allow: [".", "../shared"] },
    proxy: {
      "/api": { target, changeOrigin: true },
      "/media": { target, changeOrigin: true },
    },
  },
});
