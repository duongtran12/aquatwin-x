import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";


export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          graph: ["cytoscape"],
          charts: ["recharts"],
        },
      },
    },
  },
  server: {
    port: 5173,
  },
});
