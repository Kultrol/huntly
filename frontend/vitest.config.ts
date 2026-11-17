import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import { configDefaults, defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  test: {
    exclude: [...configDefaults.exclude, "e2e/**", "tests/responsive/**"],
    // Concurrent jsdom workers can starve the lazy-route assertions on laptops.
    maxWorkers: 2,
    environment: "jsdom",
    setupFiles: ["./tests/setup.ts"],
    env: { VITE_API_URL: "http://localhost:8000" },
    clearMocks: true,
    restoreMocks: true,
    unstubGlobals: true,
  },
});
