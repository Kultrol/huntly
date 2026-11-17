import { fileURLToPath } from "node:url";
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/responsive",
  testMatch: "**/*.pw.mjs",
  workers: 2,
  outputDir: "./test-results/responsive",
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  use: { baseURL: "http://127.0.0.1:5187", trace: "retain-on-failure" },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "webkit-touch", use: { ...devices["iPhone 13"] } },
  ],
  webServer: {
    command: "npm run dev -- --host 127.0.0.1 --port 5187 --strictPort",
    cwd: fileURLToPath(new URL("./", import.meta.url)),
    env: { VITE_API_URL: "/api" },
    url: "http://127.0.0.1:5187",
    reuseExistingServer: false,
  },
});
