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
  'command-center-export-button-click-smoke.json',
);
const screenshotDir = resolve(root, 'artifacts', 'frontend-regression');

async function requestJson(path, options = {}) {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    method: options.method || 'GET',
    headers: { 'Content-Type': 'application/json' },
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  if (!response.ok) {
    throw new Error(`${options.method || 'GET'} ${path} failed with ${response.status}`);
  }
  return response.json();
}

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

async function seedGovernanceDecision() {
  const assignmentResponse = await requestJson('/api/audit/approval-assignments', {
    method: 'POST',
    body: {
      assigned_by: 'browser-click-smoke',
      assignee_id: 'browser-click-reviewer',
      target_type: 'artifact',
      target_id: 'browser-click-smoke-artifact',
      approval_role: 'quality-reviewer',
      reason: 'Create reviewer assignment before browser export click smoke.',
      evidence: { verification: 'command-center-export-button-click-smoke' },
    },
  });
  const assignmentAuditId = assignmentResponse.audit_record.audit_id;
  const history = await requestJson('/api/audit/governance-assignment-history');
  const assignment = history.history_report.assignments.find(
    (item) => item.audit_id === assignmentAuditId,
  );
  if (!assignment) {
    throw new Error('Seeded governance assignment was not returned by assignment history.');
  }
  await requestJson('/api/audit/reviewer-decisions', {
    method: 'POST',
    body: {
      decided_by: 'browser-click-reviewer',
      reviewer_id: 'browser-click-reviewer',
      target_type: 'artifact',
      target_id: 'browser-click-smoke-artifact',
      assignment_id: assignment.assignment_id,
      decision: 'approved',
      reason: 'Approve artifact to verify browser-level export click smoke.',
      evidence: { verification: 'command-center-export-button-click-smoke' },
    },
  });
}

async function runClickSmoke() {
  await requestJson('/api/health');
  await seedGovernanceDecision();
  const frontendServer = await ensureFrontendServer();
  await mkdir(screenshotDir, { recursive: true });

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
    await page.goto(`${frontendUrl}/#governance`, { waitUntil: 'domcontentloaded' });
    await expect(page.getByRole('heading', { name: 'Governance Audit' })).toBeVisible();
    const reviewerExportButton = page.getByRole('button', { name: 'Export Reviewer Decision Evidence' });
    await expect(reviewerExportButton).toBeEnabled();
    await page.screenshot({
      path: resolve(screenshotDir, 'command-center-export-click-smoke-governance-before.png'),
      fullPage: true,
    });
    await reviewerExportButton.click();
    await expect(page.getByText('Reviewer Decision Evidence Export Ready')).toBeVisible();
    const reviewerExportRendered = await page.getByText('Reviewer Decision Evidence Export Ready').isVisible();

    await page.goto(`${frontendUrl}/#missions`, { waitUntil: 'domcontentloaded' });
    await expect(page.getByRole('heading', { name: 'Mission Flow' })).toBeVisible();
    const deliveryExportButton = page.getByRole('button', { name: 'Export Delivery Governance Evidence' });
    await expect(deliveryExportButton).toBeEnabled();
    await deliveryExportButton.click();
    await expect(page.getByText('Delivery Governance Evidence Export Ready')).toBeVisible();
    const deliveryExportRendered = await page.getByText('Delivery Governance Evidence Export Ready').isVisible();
    await page.screenshot({
      path: resolve(screenshotDir, 'command-center-export-click-smoke-after.png'),
      fullPage: true,
    });

    const pageText = await page.locator('body').innerText();
    const checks = {
      browser_opened_command_center: pageText.includes('Mariam'),
      reviewer_export_button_clicked: reviewerExportRendered,
      reviewer_export_success_rendered: reviewerExportRendered,
      delivery_export_button_clicked: true,
      delivery_export_success_rendered: deliveryExportRendered,
      db_mariam_visible: pageText.includes('DB MARIAM'),
      no_browser_console_errors: consoleErrors.length === 0,
    };
    return {
      title: 'Mariam Command Center Export Button Browser Click Smoke',
      status: Object.values(checks).every(Boolean) ? 'ready' : 'blocked',
      generated_at: new Date().toISOString(),
      data_platform: 'DB MARIAM',
      frontend_url: frontendUrl,
      api_base_url: apiBaseUrl,
      interaction_path: [
        'Open Command Center #governance in Chromium',
        'Click Export Reviewer Decision Evidence',
        'Verify Reviewer Decision Evidence Export Ready',
        'Open Command Center #missions in Chromium',
        'Click Export Delivery Governance Evidence',
        'Verify Delivery Governance Evidence Export Ready',
      ],
      screenshots: [
        'artifacts/frontend-regression/command-center-export-click-smoke-governance-before.png',
        'artifacts/frontend-regression/command-center-export-click-smoke-after.png',
      ],
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

const report = await runClickSmoke();
await mkdir(dirname(artifactPath), { recursive: true });
await writeFile(artifactPath, JSON.stringify(report, null, 2), 'utf-8');
console.log(JSON.stringify(report, null, 2));
if (report.status !== 'ready') {
  process.exit(1);
}
