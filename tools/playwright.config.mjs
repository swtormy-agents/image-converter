// E2E checks for the converter pages (static site served from the repo root).
import { defineConfig, devices } from '@playwright/test';
export default defineConfig({
  testDir: 'e2e',
  fullyParallel: true,
  reporter: 'list',
  use: { baseURL: 'http://127.0.0.1:18731/' },
  webServer: { command: 'python3 -m http.server 18731 --bind 127.0.0.1 --directory ..', url: 'http://127.0.0.1:18731/index.html', reuseExistingServer: false },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
    { name: 'webkit', use: { ...devices['Desktop Safari'] } },
  ],
});
