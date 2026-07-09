import { chromium, expect } from '@playwright/test';
import { spawn } from 'node:child_process';
import { mkdir, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const frontendUrl = process.env.MARIAM_VERIFY_FRONTEND_URL || 'http://127.0.0.1:5173';
const apiBaseUrl = process.env.MARIAM_VERIFY_API_BASE_URL || 'http://127.0.0.1:8000';
const artifactPath = resolve(
  root,
  'artifacts',
  'frontend-regression',
  'command-center-all-buttons-smoke.json',
);

const sections = [
  'status',
  'data-platform',
  'verification',
  'roadmap',
  'missions',
  'seed-dna',
  'agent-society',
  'plugins',
  'governance',
];

async function waitForHttp(url, attempts = 30) {
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    try {
      const response = await fetch(url);
      if (response.ok) return true;
    } catch {
      // Retry while the local server starts.
    }
    await new Promise((resolveAttempt) => setTimeout(resolveAttempt, 500));
  }
  return false;
}

async function ensureFrontendServer() {
  if (await waitForHttp(frontendUrl, 2)) {
    return { started: false, process: null };
  }
  const child = spawn(
    process.platform === 'win32' ? 'npm.cmd' : 'npm',
    ['run', 'dev', '--', '--host', '127.0.0.1', '--port', '5173'],
    {
      cwd: resolve(root, 'frontend'),
      env: {
        ...process.env,
        VITE_MARIAM_API_BASE_URL: apiBaseUrl,
      },
      stdio: 'ignore',
      windowsHide: true,
    },
  );
  if (!(await waitForHttp(frontendUrl, 40))) {
    child.kill();
    throw new Error(`Frontend dev server did not become ready at ${frontendUrl}`);
  }
  return { started: true, process: child };
}

async function visibleEnabledButtonLabels(page, sectionId) {
  return page.locator(`#${sectionId} button:visible:not([disabled])`).evaluateAll((buttons) => (
    buttons.map((button, index) => ({
      index,
      text: button.textContent?.replace(/\s+/g, ' ').trim() || `button-${index}`,
    }))
  ));
}

async function clickFirstMatchingButton(page, sectionId, label) {
  const button = page
    .locator(`#${sectionId} button:visible:not([disabled])`)
    .filter({ hasText: label })
    .first();
  if ((await button.count()) === 0) {
    return false;
  }
  await button.scrollIntoViewIfNeeded();
  await button.click({ timeout: 5000 });
  return true;
}

async function inspectVisibleErrorBanners(page) {
  return page.locator('[data-testid="command-center-error-banner"]:visible').evaluateAll((banners) => (
    banners.map((banner) => banner.textContent?.replace(/\s+/g, ' ').trim() || 'visible error banner')
  ));
}

async function runAllButtonsSmoke() {
  const frontendServer = await ensureFrontendServer();
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1366, height: 900 } });
  const consoleErrors = [];
  const failedApiResponses = [];

  page.on('pageerror', (error) => consoleErrors.push(String(error)));
  page.on('console', (message) => {
    if (message.type() === 'error') {
      consoleErrors.push(message.text());
    }
  });
  page.on('response', (response) => {
    const url = response.url();
    const status = response.status();
    if (status >= 400 && (url.startsWith(apiBaseUrl) || url.includes('/api/'))) {
      failedApiResponses.push({ status, url });
    }
  });

  try {
    await page.goto(frontendUrl, { waitUntil: 'domcontentloaded' });
    await expect(page.getByRole('heading', { name: 'Mariam AI Enterprise OS' })).toBeVisible();

    const clicks = [];
    const visitedSections = new Set();
    for (const sectionId of sections) {
      await page.goto(`${frontendUrl}/#${sectionId}`, { waitUntil: 'domcontentloaded' });
      await page.waitForTimeout(600);
      visitedSections.add(sectionId);
      const labels = await visibleEnabledButtonLabels(page, sectionId);
      for (const { text } of labels) {
        const beforeConsoleErrors = consoleErrors.length;
        const beforeFailedApiResponses = failedApiResponses.length;
        let clicked = true;
        let skippedAfterStateChange = false;
        let clickError = null;
        try {
          clicked = await clickFirstMatchingButton(page, sectionId, text);
          skippedAfterStateChange = !clicked;
          if (clicked) {
            await page.waitForTimeout(750);
          }
        } catch (error) {
          clicked = false;
          clickError = String(error).slice(0, 500);
        }
        const visibleErrorBanners = await inspectVisibleErrorBanners(page);
        clicks.push({
          section: sectionId,
          label: text,
          clicked,
          skipped_after_state_change: skippedAfterStateChange,
          click_error: clickError,
          new_console_errors: consoleErrors.length - beforeConsoleErrors,
          new_failed_api_responses: failedApiResponses.length - beforeFailedApiResponses,
          visible_error_banners: visibleErrorBanners,
          passed: (clicked || skippedAfterStateChange)
            && clickError === null
            && consoleErrors.length === beforeConsoleErrors
            && failedApiResponses.length === beforeFailedApiResponses
            && visibleErrorBanners.length === 0,
        });
      }
    }

    const failedClicks = clicks.filter((click) => !click.passed);
    const checks = {
      all_sections_visited: sections.every((sectionId) => visitedSections.has(sectionId)),
      enabled_buttons_found: clicks.length >= 40,
      all_enabled_buttons_clicked: failedClicks.length === 0,
      no_browser_console_errors: consoleErrors.length === 0,
      no_failed_api_responses: failedApiResponses.length === 0,
      no_visible_error_banners: clicks.every((click) => click.visible_error_banners.length === 0),
    };

    return {
      title: 'Mariam Command Center All Buttons Smoke',
      status: Object.values(checks).every(Boolean) ? 'ready' : 'blocked',
      generated_at: new Date().toISOString(),
      data_platform: 'DB MARIAM',
      frontend_url: frontendUrl,
      api_base_url: apiBaseUrl,
      sections,
      visited_sections: Array.from(visitedSections),
      button_click_count: clicks.length,
      failed_click_count: failedClicks.length,
      clicks,
      failed_clicks: failedClicks,
      console_errors: consoleErrors,
      failed_api_responses: failedApiResponses,
      frontend_server_started_by_script: frontendServer.started,
      checks,
    };
  } finally {
    await page.close();
    await browser.close();
    if (frontendServer.started && frontendServer.process) {
      frontendServer.process.kill();
    }
  }
}

const report = await runAllButtonsSmoke();
await mkdir(dirname(artifactPath), { recursive: true });
await writeFile(artifactPath, JSON.stringify(report, null, 2), 'utf-8');
console.log(JSON.stringify(report, null, 2));
if (report.status !== 'ready') {
  process.exit(1);
}
