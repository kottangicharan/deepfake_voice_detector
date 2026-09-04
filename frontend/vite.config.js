import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/cases": "http://127.0.0.1:8123",
      "/score": "http://127.0.0.1:8123",
      "/enroll": "http://127.0.0.1:8123",
      "/stream": { target: "ws://127.0.0.1:8123", ws: true },
    },
  },
});
