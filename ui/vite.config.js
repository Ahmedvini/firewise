import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// base: "/" when FastAPI serves the build (single origin); set VITE_BASE=/FIREWISE/ for GitHub Pages.
// In development, /api is proxied to the FastAPI backend so the same relative URLs work everywhere.
export default defineConfig({
  base: process.env.VITE_BASE || "/",
  plugins: [react()],
  server: {
    proxy: { "/api": { target: process.env.VITE_API_PROXY || "http://127.0.0.1:8000", changeOrigin: true } },
  },
});
