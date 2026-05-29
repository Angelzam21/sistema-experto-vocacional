// @ts-check
const { defineConfig, devices } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests',
  testMatch: '**/*.spec.js',
  timeout: 30_000,
  retries: 0,
  use: {
    baseURL: 'http://localhost:8501',
    headless: true,
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
  // Arranca la app Streamlit antes de los tests; la reutiliza si ya está corriendo.
  webServer: {
    command: 'python -m streamlit run app.py --server.port 8501 --server.headless true',
    url: 'http://localhost:8501',
    reuseExistingServer: true,
    timeout: 30_000,
  },
  snapshotDir: './tests/snapshots',
});
