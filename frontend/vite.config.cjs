const { defineConfig } = require("vite");
const react = require("@vitejs/plugin-react");

const backendTarget = process.env.VITE_BACKEND_PROXY_TARGET || "http://localhost:8000";

module.exports = defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      "/auth": { target: backendTarget, changeOrigin: true },
      "/documents": { target: backendTarget, changeOrigin: true },
      "/chat": { target: backendTarget, changeOrigin: true },
      "/health": { target: backendTarget, changeOrigin: true },
    },
  },
});
