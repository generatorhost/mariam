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
  'command-center-responsive-action-panels-smoke.json',
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

async function inspectActionPanels(page) {
  return page.evaluate(() => {
    const viewportWidth = window.innerWidth;
    const panels = Array.from(document.querySelectorAll('.mission-actions')).filter((panel) => {
      const rect = panel.getBoundingClientRect();
      return rect.width > 0 && rect.height > 0;
    });
    return panels.map((panel, panelIndex) => {
      const panelRect = panel.getBoundingClientRect();
      const controls = Array.from(panel.querySelectorAll('button, a')).map((control) => {
        const rect = control.getBoundingClientRect();
        return {
          text: control.textContent?.replace(/\s+/g, ' ').trim() || '',
          tag: control.tagName.toLowerCase(),
          visible: rect.width > 0 && rect.height > 0,
          width: Math.round(rect.width),
          height: Math.round(rect.height),
          left: Math.round(rect.left),
          right: Math.round(rect.right),
          top: Math.round(rect.top),
          bottom: Math.round(rect.bottom),
          within_viewport: rect.left >= 0 && rect.right <= viewportWidth,
          usable_tap_target: rect.height >= 32 && rect.width >= 44,
        };
      });
      return {
        panel_index: panelIndex,
        visible: panelRect.width > 0 && panelRect.height > 0,
        width: Math.round(panelRect.width),
        height: Math.round(panelRect.height),
        left: Math.round(panelRect.left),
        right: Math.round(panelRect.right),
        within_viewport: panelRect.left >= 0 && panelRect.right <= viewportWidth,
        control_count: controls.length,
        controls,
      };
    });
  });
}

async function inspectPageControls(page) {
  return page.evaluate(() => Array.from(document.querySelectorAll('button, a')).map((control) => {
    const rect = control.getBoundingClientRect();
    return {
      text: control.textContent?.replace(/\s+/g, ' ').trim() || '',
      tag: control.tagName.toLowerCase(),
      visible: rect.width > 0 && rect.height > 0,
      width: Math.round(rect.width),
      height: Math.round(rect.height),
      within_viewport_width: rect.left >= 0 && rect.right <= window.innerWidth,
      usable_tap_target: rect.height >= 32 && rect.width >= 44,
    };
  }).filter((control) => control.visible));
}

async function runViewportSmoke(browser, viewport) {
  const page = await browser.newPage({
    viewport: { width: viewport.width, height: viewport.height },
  });
  const consoleErrors = [];
  page.on('pageerror', (error) => consoleErrors.push(String(error)));
  page.on('console', (message) => {
    if (message.type() === 'error') {
      consoleErrors.push(message.text());
    }
  });

  try {
    await page.goto(`${frontendUrl}/#missions`, { waitUntil: 'domcontentloaded' });
    await expect(page.getByRole('heading', { name: 'Mariam AI Enterprise OS' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Mission Flow' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Start CRM Mission' })).toBeVisible({ timeout: 30000 });

    const visitedControlLabels = new Set((await inspectPageControls(page)).map((control) => control.text));
    const visitedActionPanels = [];
    visitedActionPanels.push(...(await inspectActionPanels(page)).map((panel) => ({
      section: 'missions',
      ...panel,
    })));
    const missionStart = page.getByRole('button', { name: 'Start CRM Mission' });
    await expect(missionStart).toBeEnabled({ timeout: 30000 });
    await missionStart.click();
    await page.waitForFunction(
      () => !/Starting\.\.\.|Approving\.\.\.|Rejecting\.\.\.|Loading\.\.\./.test(document.body.innerText),
      { timeout: 30000 },
    );
    await expect(page.getByRole('button', { name: 'Approve Mission' })).toBeVisible({ timeout: 30000 });
    await expect(page.getByRole('button', { name: 'Reject Mission' })).toBeVisible({ timeout: 30000 });
    await expect(page.getByRole('button', { name: 'Export Delivery Governance Evidence' })).toBeVisible({ timeout: 30000 });
    (await inspectPageControls(page)).forEach((control) => visitedControlLabels.add(control.text));
    visitedActionPanels.push(...(await inspectActionPanels(page)).map((panel) => ({
      section: 'missions_after_start',
      ...panel,
    })));

    await page.getByRole('link', { name: 'Governance' }).click();
    await expect(page).toHaveURL(/#governance$/);
    await page.waitForFunction(
      () => !/Recording\.\.\.|Assigning\.\.\.|Routing\.\.\.|Exporting\.\.\.|Refreshing\.\.\.|Escalating\.\.\.|Loading\.\.\./.test(document.body.innerText),
      { timeout: 30000 },
    );
    await expect(page.getByRole('button', { name: 'Assign Approval' })).toBeVisible({ timeout: 30000 });
    await expect(page.getByRole('button', { name: 'Route Notification' })).toBeVisible({ timeout: 30000 });
    await expect(page.getByRole('button', { name: 'Export Reviewer Decision Evidence' })).toBeVisible({ timeout: 30000 });
    (await inspectPageControls(page)).forEach((control) => visitedControlLabels.add(control.text));
    visitedActionPanels.push(...(await inspectActionPanels(page)).map((panel) => ({
      section: 'governance',
      ...panel,
    })));

    await page.getByRole('link', { name: 'Plugins' }).click();
    await expect(page).toHaveURL(/#plugins$/);
    await expect(page.getByRole('button', { name: 'Register CRM Plugin' })).toBeVisible({ timeout: 30000 });
    await expect(page.getByRole('button', { name: 'Open Live Plugin Workspace' })).toBeVisible({ timeout: 30000 });
    (await inspectPageControls(page)).forEach((control) => visitedControlLabels.add(control.text));
    visitedActionPanels.push(...(await inspectActionPanels(page)).map((panel) => ({
      section: 'plugins',
      ...panel,
    })));

    const actionPanels = visitedActionPanels;
    const pageControls = await inspectPageControls(page);
    const flattenedControls = actionPanels.flatMap((panel) => panel.controls);
    const requiredControls = [
      'Start CRM Mission',
      'Approve Mission',
      'Reject Mission',
      'Export Delivery Governance Evidence',
      'Assign Approval',
      'Route Notification',
      'Export Reviewer Decision Evidence',
      'Register CRM Plugin',
      'Open Live Plugin Workspace',
    ];
    const presentControlLabels = Array.from(visitedControlLabels);
    const missingControls = requiredControls.filter((label) => !presentControlLabels.includes(label));
    const checks = {
      viewport_size_applied: page.viewportSize()?.width === viewport.width
        && page.viewportSize()?.height === viewport.height,
      action_panels_visible: actionPanels.length >= 1 && actionPanels.every((panel) => panel.visible),
      action_panels_within_viewport: actionPanels.every((panel) => panel.within_viewport),
      controls_visible: flattenedControls.length >= 6
        && flattenedControls.every((control) => control.visible),
      controls_within_viewport: flattenedControls.every((control) => control.within_viewport),
      controls_have_usable_tap_targets: flattenedControls.every((control) => control.usable_tap_target),
      required_controls_present: missingControls.length === 0,
      no_horizontal_overflow: await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1),
      no_browser_console_errors: consoleErrors.length === 0,
    };
    return {
      ...viewport,
      status: Object.values(checks).every(Boolean) ? 'ready' : 'blocked',
      required_controls: requiredControls,
      missing_controls: missingControls,
      page_control_count: pageControls.length,
      action_panels: actionPanels,
      checks,
      console_errors: consoleErrors,
    };
  } finally {
    await page.close();
  }
}

async function runResponsiveActionPanelsSmoke() {
  const frontendServer = await ensureFrontendServer();
  const browser = await chromium.launch({ headless: true });
  const viewports = [
    { name: 'tablet', width: 900, height: 900 },
    { name: 'mobile', width: 390, height: 844 },
  ];

  try {
    const results = [];
    for (const viewport of viewports) {
      results.push(await runViewportSmoke(browser, viewport));
    }
    const checks = {
      tablet_action_panels_ready: results.some((result) => result.name === 'tablet' && result.status === 'ready'),
      mobile_action_panels_ready: results.some((result) => result.name === 'mobile' && result.status === 'ready'),
      all_required_controls_present: results.every((result) => result.checks.required_controls_present),
      all_controls_within_viewport: results.every((result) => result.checks.controls_within_viewport),
      all_controls_have_usable_tap_targets: results.every(
        (result) => result.checks.controls_have_usable_tap_targets,
      ),
      no_horizontal_overflow: results.every((result) => result.checks.no_horizontal_overflow),
      no_browser_console_errors: results.every((result) => result.checks.no_browser_console_errors),
    };
    return {
      title: 'Mariam Command Center Responsive Action Panels Smoke',
      status: Object.values(checks).every(Boolean) ? 'ready' : 'blocked',
      generated_at: new Date().toISOString(),
      data_platform: 'DB MARIAM',
      frontend_url: frontendUrl,
      api_base_url: apiBaseUrl,
      viewports: results,
      frontend_server_started_by_script: frontendServer.started,
      checks,
    };
  } finally {
    await browser.close();
    if (frontendServer.started && frontendServer.process) {
      frontendServer.process.kill();
    }
  }
}

const report = await runResponsiveActionPanelsSmoke();
await mkdir(dirname(artifactPath), { recursive: true });
await writeFile(artifactPath, JSON.stringify(report, null, 2), 'utf-8');
console.log(JSON.stringify(report, null, 2));
if (report.status !== 'ready') {
  process.exit(1);
}
