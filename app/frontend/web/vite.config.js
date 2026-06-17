import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

const API_PROXY_TARGET = "http://localhost:8000";
// API endpoints must always hit the network — never serve a cached/stale
// optimization result or config.
const API_PREFIXES = ["/config", "/optimize", "/addresses"];

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["icon.png", "icon-192.png", "icon-512.png", "icon-maskable-512.png"],
      manifest: {
        name: "OptRoute — Route Optimization",
        short_name: "OptRoute",
        description: "Plan the shortest delivery route in seconds.",
        theme_color: "#5b5ff5",
        background_color: "#eef0f8",
        display: "standalone",
        start_url: "/",
        icons: [
          { src: "/icon-192.png", sizes: "192x192", type: "image/png" },
          { src: "/icon-512.png", sizes: "512x512", type: "image/png" },
          { src: "/icon-maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
        ],
      },
      workbox: {
        navigateFallbackDenylist: [/^\/(config|optimize|addresses)/],
        runtimeCaching: [
          {
            urlPattern: ({ url }) => API_PREFIXES.some((p) => url.pathname.startsWith(p)),
            handler: "NetworkOnly",
          },
          {
            // Google Maps scripts/tiles: prefer network, fall back to cache offline.
            urlPattern: ({ url }) =>
              url.origin.includes("googleapis.com") || url.origin.includes("gstatic.com"),
            handler: "NetworkFirst",
            options: { cacheName: "gmaps", expiration: { maxEntries: 80, maxAgeSeconds: 86400 } },
          },
        ],
      },
    }),
  ],
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
