import path from "node:path";
import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";
import { viteSingleFile } from "vite-plugin-singlefile";

const root = path.dirname(fileURLToPath(import.meta.url));
// The artifact helper stages the artifact's own source here and sets both paths.
const artifact = process.env.ARTIFACT_DIR;
if (!artifact) {
  throw new Error("ARTIFACT_DIR is not set. Run skills/show-me/scripts/artifact.py instead of vite directly.");
}

export default defineConfig({
  root,
  base: "./",
  plugins: [react(), tailwindcss(), viteSingleFile()],
  resolve: {
    alias: {
      "@artifact": artifact,
      "@": path.join(root, "src"),
    },
  },
  build: {
    outDir: process.env.ARTIFACT_OUT_DIR || path.join(root, ".builds", "default"),
    emptyOutDir: true,
  },
  server: {
    port: Number(process.env.PORT || 5174),
  },
});
