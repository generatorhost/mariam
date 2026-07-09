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
  'command-center-keyboard-focus-smoke.json',
);

async function waitForHttp(url, attempts = 30) {
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    try {
      const response = await fetch(url);
      if (response.ok) return true;
    } catch {
      // Retry while the local dev server starts.
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

async function activeElementSnapshot(page) {
  return page.evaluate(() => {
    const active = document.activeElement;
    if (!active) return null;
    const text = (active.textContent || active.getAttribute('aria-label') || active.id || active.tagName)
      .replace(/\s+/g, ' ')
      .trim();
    return {
      tag: active.tagName.toLowerCase(),
      text,
      id: active.id || '',
      href: active.getAttribute('href') || '',
      ariaLabel: active.getAttribute('aria-label') || '',
      testId: active.getAttribute('data-testid') || '',
    };
  });
}

function focusLabel(item) {
  if (!item) return '';
  return item.text || item.ariaLabel || item.href || item.id || item.tag;
}

async function runKeyboardFocusSmoke() {
  const frontendServer = await ensureFrontendServer();
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  const consoleErrors = [];
  page.on('pageerror', (error) => consoleErrors.push(String(error)));
  page.on('console', (message) => {
    if (message.type() === 'error') {
      consoleErrors.push(message.text());
    }
  });

  try {
    await page.goto(`${frontendUrl}/#status`, { waitUntil: 'domcontentloaded' });
    await expect(page.getByRole('heading', { name: 'Mariam AI Enterprise OS' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Refresh System Status' })).toBeEnabled();
    await page.getByRole('link', { name: 'Governance' }).click();
    await expect(page.getByRole('button', { name: 'Export Reviewer Decision Evidence' })).toBeEnabled();
    await page.getByRole('link', { name: 'Status' }).click();
    await page.keyboard.press('Home');

    const focusPath = [];
    for (let index = 0; index < 180; index += 1) {
      await page.keyboard.press('Tab');
      const snapshot = await activeElementSnapshot(page);
      const label = focusLabel(snapshot);
      if (
        label
        && snapshot.tag !== 'body'
        && !focusPath.some((item) => focusLabel(item) === label && item.href === snapshot.href)
      ) {
        focusPath.push(snapshot);
      }
    }

    const labels = focusPath.map(focusLabel);
    const expectedFocusTargets = [
      'Skip to Command Center workspace',
      'Status',
      'DB MARIAM',
      'Verification',
      'Roadmap',
      'Missions',
      'Seed DNA',
      'Agent Society',
      'Plugins',
      'Governance',
      'Architecture Library',
      'Refresh System Status',
      'Refresh Actor Context',
      'Enforce Permission Gate',
      'Enforce Human Identity',
      'Refresh Readiness',
    ];
    const missingFocusTargets = expectedFocusTargets.filter(
      (target) => !labels.some((label) => label.includes(target)),
    );
    const navOrder = [
      'Status',
      'DB MARIAM',
      'Verification',
      'Roadmap',
      'Missions',
      'Seed DNA',
      'Agent Society',
      'Plugins',
      'Governance',
    ];
    const navIndexes = navOrder.map((target) => labels.findIndex((label) => label === target));
    const navOrderValid = navIndexes.every((index) => index >= 0)
      && navIndexes.every((index, position) => position === 0 || index > navIndexes[position - 1]);
    const checks = {
      skip_link_available: labels.includes('Skip to Command Center workspace'),
      primary_navigation_order_valid: navOrderValid,
      primary_actions_focusable: missingFocusTargets.length === 0,
      focus_path_has_minimum_depth: focusPath.length >= 15,
      focused_workspace_navigation: labels.includes('Seed DNA')
        && labels.includes('Agent Society')
        && labels.includes('Governance'),
      governance_section_action_reachable: true,
      no_browser_console_errors: consoleErrors.length === 0,
    };
    return {
      title: 'Mariam Command Center Keyboard Focus Smoke',
      status: Object.values(checks).every(Boolean) ? 'ready' : 'blocked',
      generated_at: new Date().toISOString(),
      data_platform: 'DB MARIAM',
      frontend_url: frontendUrl,
      api_base_url: apiBaseUrl,
      focus_path: focusPath,
      expected_focus_targets: expectedFocusTargets,
      missing_focus_targets: missingFocusTargets,
      nav_order: navOrder,
      nav_indexes: navIndexes,
      frontend_server_started_by_script: frontendServer.started,
      checks,
      console_errors: consoleErrors,
    };
  } finally {
    await browser.close();
    if (frontendServer.started && frontendServer.process) {
      frontendServer.process.kill();
    }
  }
}

const report = await runKeyboardFocusSmoke();
await mkdir(dirname(artifactPath), { recursive: true });
await writeFile(artifactPath, JSON.stringify(report, null, 2), 'utf-8');
console.log(JSON.stringify(report, null, 2));
if (report.status !== 'ready') {
  process.exit(1);
}
