import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  retries: 1,
  timeout: 30000,
  expect: {
    timeout: 5000,
  },
  use: {
    baseURL: "http://localhost:3000",
    headless: true,
    screenshot: "only-on-failure",
  },
  webServer: {
    command: "npm run build && npx vite preview --port 3000",
    url: "http://localhost:3000",
    reuseExistingServer: true,
    timeout: 30000,
  },
});
