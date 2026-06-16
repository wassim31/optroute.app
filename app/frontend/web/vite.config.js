import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const API_PROXY_TARGET = "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "../static",
    emptyOutDir: true,
  },
  server: {
    proxy: {
      "/config": API_PROXY_TARGET,
      "/optimize": API_PROXY_TARGET,
      "/addresses": API_PROXY_TARGET,
    },
  },
});
