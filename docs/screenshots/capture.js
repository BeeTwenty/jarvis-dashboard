// Playwright script to capture Jarvis Dashboard screenshots
// Install: npm install playwright
// Run:     node capture.js

const { chromium } = require('playwright');
const path = require('path');

const BASE_URL = 'http://localhost:3000';
const OUT_DIR = path.resolve(__dirname);
const DESKTOP = { width: 1920, height: 1080 };
const MOBILE = { width: 390, height: 844 };

// Pages to capture
const PAGES = [
  {
    name: 'overview',
    path: '/',
    waitFor: '.card, .overview-card, [class*="card"]',
    fullPage: false,
  },
  {
    name: 'system',
    path: '/system',
    waitFor: 'svg, canvas, [class*="gauge"], [class*="Gauge"]',
    fullPage: false,
  },
  {
    name: 'docker',
    path: '/docker',
    waitFor: '[class*="container"], [class*="card"]',
    fullPage: false,
  },
  {
    name: 'torrents',
    path: '/torrents',
    waitFor: '[class*="torrent"], [class*="card"], table',
    fullPage: false,
  },
  {
    name: 'media',
    path: '/media',
    waitFor: '[class*="media"], [class*="card"], [class*="stat"]',
    fullPage: false,
  },
  {
    name: 'discover',
    path: '/discover',
    waitFor: '[class*="mood"], [class*="Mood"], [class*="moodGrid"]',
    fullPage: false,
  },
  {
    name: 'files',
    path: '/files',
    waitFor: '[class*="file"], [class*="explorer"], table, [class*="row"]',
    fullPage: false,
  },
];

async function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function waitForContent(page, selector) {
  try {
    await page.waitForSelector(selector, { timeout: 8000 });
  } catch {
    // Selector not found, wait a bit and continue anyway
    console.log(`  [warn] Selector "${selector}" not found, continuing...`);
  }
  // Extra settle time for animations and data loading
  await sleep(1500);
}

async function getTheme(page) {
  return page.evaluate(() => {
    return document.documentElement.getAttribute('data-theme') ||
           document.body.getAttribute('data-theme') ||
           document.documentElement.classList.contains('dark') ? 'dark' :
           document.documentElement.classList.contains('light') ? 'light' :
           'unknown';
  });
}

async function setTheme(page, target) {
  // Click the theme toggle button to switch themes
  const currentTheme = await getTheme(page);
  console.log(`  Current theme: ${currentTheme}, target: ${target}`);

  // Determine if we need to toggle
  const isDark = currentTheme === 'dark' || currentTheme === 'unknown';
  const wantDark = target === 'dark';

  if ((isDark && wantDark) || (!isDark && !wantDark)) {
    return; // Already in the right mode
  }

  // Find and click the theme toggle
  const toggleBtn = await page.$('.theme-toggle, [aria-label*="Switch to"], button[class*="theme"]');
  if (toggleBtn) {
    await toggleBtn.click();
    await sleep(500);
    console.log(`  Toggled theme to ${target}`);
  } else {
    console.log('  [warn] Could not find theme toggle button');
  }
}

async function captureScreenshot(page, name, fullPage = false) {
  const filePath = path.join(OUT_DIR, `${name}.png`);
  await page.screenshot({ path: filePath, fullPage });
  console.log(`  Saved: ${name}.png`);
}

async function capturePage(page, pageConfig, theme) {
  const url = `${BASE_URL}${pageConfig.path}`;
  console.log(`\nNavigating to ${pageConfig.name} (${url})`);

  await page.goto(url, { waitUntil: 'networkidle', timeout: 15000 }).catch(() => {
    console.log(`  [warn] networkidle timeout, continuing...`);
  });

  await setTheme(page, theme);
  await waitForContent(page, pageConfig.waitFor);

  await captureScreenshot(page, `${pageConfig.name}-${theme}`, pageConfig.fullPage);
}

async function main() {
  console.log('Launching browser...');
  const browser = await chromium.launch({ headless: true });

  // ── Desktop screenshots ──
  console.log('\n=== Desktop Screenshots (1920x1080) ===');
  const desktopContext = await browser.newContext({ viewport: DESKTOP });
  const page = await desktopContext.newPage();

  // Dark mode captures
  console.log('\n--- Dark Mode ---');
  for (const pageConfig of PAGES) {
    await capturePage(page, pageConfig, 'dark');
  }

  // Discover: trigger thriller mood (dark)
  console.log('\nCapturing Discover - Thriller results (dark)...');
  await page.goto(`${BASE_URL}/discover`, { waitUntil: 'networkidle', timeout: 15000 }).catch(() => {});
  await setTheme(page, 'dark');
  await waitForContent(page, '[class*="mood"], [class*="Mood"]');

  // Click the Thriller mood card
  const thrillerBtn = await page.$('button:has-text("Thriller")');
  if (thrillerBtn) {
    await thrillerBtn.click();
    console.log('  Clicked Thriller mood');
    // Wait for recommendations to load
    try {
      await page.waitForSelector('[class*="recCard"], [class*="rec-card"], [class*="recGrid"]', { timeout: 10000 });
    } catch {
      console.log('  [warn] Recommendation cards not found, waiting...');
    }
    await sleep(2000);
    await captureScreenshot(page, 'discover-thriller-dark', false);
  } else {
    console.log('  [warn] Could not find Thriller button');
  }

  // Movie detail page (dark) - Inception
  console.log('\nCapturing Movie Detail - Inception (dark)...');
  await page.goto(`${BASE_URL}/discover/movie/27205`, { waitUntil: 'networkidle', timeout: 15000 }).catch(() => {});
  await setTheme(page, 'dark');
  await sleep(2000);
  await captureScreenshot(page, 'movie-detail-dark', true);

  // Light mode captures
  console.log('\n--- Light Mode ---');
  for (const pageConfig of PAGES) {
    await capturePage(page, pageConfig, 'light');
  }

  // Discover: trigger thriller mood (light)
  console.log('\nCapturing Discover - Thriller results (light)...');
  await page.goto(`${BASE_URL}/discover`, { waitUntil: 'networkidle', timeout: 15000 }).catch(() => {});
  await setTheme(page, 'light');
  await waitForContent(page, '[class*="mood"], [class*="Mood"]');

  const thrillerBtnLight = await page.$('button:has-text("Thriller")');
  if (thrillerBtnLight) {
    await thrillerBtnLight.click();
    try {
      await page.waitForSelector('[class*="recCard"], [class*="rec-card"], [class*="recGrid"]', { timeout: 10000 });
    } catch {}
    await sleep(2000);
    await captureScreenshot(page, 'discover-thriller-light', false);
  }

  // Movie detail page (light)
  console.log('\nCapturing Movie Detail - Inception (light)...');
  await page.goto(`${BASE_URL}/discover/movie/27205`, { waitUntil: 'networkidle', timeout: 15000 }).catch(() => {});
  await setTheme(page, 'light');
  await sleep(2000);
  await captureScreenshot(page, 'movie-detail-light', true);

  await desktopContext.close();
  await browser.close();

  console.log('\n=== Done! All screenshots saved to docs/screenshots/ ===');
  console.log(`Total files in ${OUT_DIR}:`);
}

main().catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});
