// Browser interaction tests. Uses the system Google Chrome (no browser download) with software WebGL.
// The suite starts its own FIREWISE server on port 8767 with a throwaway state store.
import { defineConfig } from "@playwright/test";
import os from "node:os";
import path from "node:path";

const PORT = 8767;
const STATE = path.join(os.tmpdir(), `firewise-e2e-${Date.now()}.sqlite`);

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  expect: { timeout: 15_000 },
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    channel: "chrome",
    viewport: { width: 1600, height: 1000 },
    launchOptions: { args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"] },
  },
  webServer: {
    command: `cd .. && FIREWISE_STATE_DB=${STATE} .venv/bin/uvicorn api.main:app --host 127.0.0.1 --port ${PORT} --log-level warning`,
    url: `http://127.0.0.1:${PORT}/api/health`,
    reuseExistingServer: false,
    timeout: 60_000,
  },
});
