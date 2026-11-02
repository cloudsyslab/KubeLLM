import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// FastAPI serves the built app from operator_ui/web/dist. Assets resolve from the
// site root so deep links such as /models/<id> load correctly.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: "/",
  resolve: {
    alias: { "@": decodeURIComponent(new URL("./src", import.meta.url).pathname) },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
    // The fixture snapshot is its own lazily loaded chunk of recorded data.
    chunkSizeWarningLimit: 900,
  },
});
