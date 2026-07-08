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
  'command-center-responsive-navigation-smoke.json',
);
const preferenceStorageKey = 'mariam.commandCenter.preferences.v1';

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

async function clickNavLink(page, label, hash) {
  const link = page.getByRole('link', { name: label });
  await expect(link).toBeVisible();
  await link.click();
  await expect(page).toHaveURL(new RegExp(`${hash}$`));
  const activeSection = await page.evaluate((storageKey) => {
    const rawPreferences = localStorage.getItem(storageKey);
    return rawPreferences ? JSON.parse(rawPreferences).activeSection : null;
  }, preferenceStorageKey);
  return {
    label,
    hash,
    url: page.url(),
    active_section: activeSection,
  };
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
    await page.goto(`${frontendUrl}/#status`, { waitUntil: 'domcontentloaded' });
    await expect(page.getByRole('heading', { name: 'Mariam AI Enterprise OS' })).toBeVisible();
    await expect(page.getByRole('navigation', { name: 'Command Center sections' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'DB MARIAM' })).toBeVisible();

    const interactions = [];
    interactions.push(await clickNavLink(page, 'DB MARIAM', '#data-platform'));
    await expect(page.locator('#data-platform')).toBeVisible();
    await expect(page.getByRole('heading', { name: 'DB MARIAM', exact: true })).toBeVisible();
    interactions.push(await clickNavLink(page, 'Verification', '#verification'));
    await expect(page.locator('#verification')).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Verification Report' })).toBeVisible();
    interactions.push(await clickNavLink(page, 'Governance', '#governance'));
    await expect(page.locator('#governance')).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Governance Audit' })).toBeVisible();

    const state = await page.evaluate(() => {
      const nav = document.querySelector('.sidebar-nav');
      const workspace = document.querySelector('#workspace');
      const activeLink = document.querySelector('.sidebar-nav a[aria-current="page"]');
      const bodyText = document.body.innerText;
      const rawPreferences = localStorage.getItem('mariam.commandCenter.preferences.v1');
      const preferences = rawPreferences ? JSON.parse(rawPreferences) : {};
      return {
        active_section: preferences.activeSection || null,
        nav_visible: Boolean(nav && nav.getBoundingClientRect().width > 0),
        workspace_visible: Boolean(workspace && workspace.getBoundingClientRect().width > 0),
        active_link_text: activeLink?.textContent?.replace(/\s+/g, ' ').trim() || '',
        db_mariam_visible: bodyText.includes('DB MARIAM'),
        official_terms_visible: bodyText.includes('Mariam Living Enterprise OS Core')
          && bodyText.includes('Mariam Data Platform'),
      };
    });
    const checks = {
      viewport_size_applied: page.viewportSize()?.width === viewport.width
        && page.viewportSize()?.height === viewport.height,
      command_center_navigation_visible: state.nav_visible,
      workspace_visible: state.workspace_visible,
      navigation_hash_updates: interactions.every((item) => item.url.endsWith(item.hash)),
      active_section_persisted: state.active_section === 'governance',
      active_link_updates: state.active_link_text.includes('Governance'),
      db_mariam_visible: state.db_mariam_visible,
      official_terms_visible: state.official_terms_visible,
      no_browser_console_errors: consoleErrors.length === 0,
    };
    return {
      ...viewport,
      status: Object.values(checks).every(Boolean) ? 'ready' : 'blocked',
      interactions,
      state,
      checks,
      console_errors: consoleErrors,
    };
  } finally {
    await page.close();
  }
}

async function runResponsiveNavigationSmoke() {
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
      tablet_navigation_ready: results.some((result) => result.name === 'tablet' && result.status === 'ready'),
      mobile_navigation_ready: results.some((result) => result.name === 'mobile' && result.status === 'ready'),
      all_viewports_update_hash: results.every((result) => result.checks.navigation_hash_updates),
      all_viewports_persist_active_section: results.every((result) => result.checks.active_section_persisted),
      all_viewports_show_db_mariam: results.every((result) => result.checks.db_mariam_visible),
      all_viewports_show_official_terms: results.every((result) => result.checks.official_terms_visible),
      no_browser_console_errors: results.every((result) => result.checks.no_browser_console_errors),
    };
    return {
      title: 'Mariam Command Center Responsive Navigation Smoke',
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

const report = await runResponsiveNavigationSmoke();
await mkdir(dirname(artifactPath), { recursive: true });
await writeFile(artifactPath, JSON.stringify(report, null, 2), 'utf-8');
console.log(JSON.stringify(report, null, 2));
if (report.status !== 'ready') {
  process.exit(1);
}
