import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  use: {
    baseURL: "http://localhost:3000",
    headless: true,
  },
  webServer: {
    command: "npm run build && cd .. && uv run insight-blueprint --project /tmp/test-project",
    url: "http://localhost:3000",
    reuseExistingServer: true,
  },
});
