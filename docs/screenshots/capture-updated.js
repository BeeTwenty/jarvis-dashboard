const { chromium } = require('playwright');

const BASE = 'http://localhost:3000';
const OUT = __dirname;

(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });

  // Desktop dark mode
  const ctx = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    colorScheme: 'dark',
  });
  const page = await ctx.newPage();

  // Helper: wait for network idle + extra settle time
  async function settle(ms = 1500) {
    await page.waitForLoadState('networkidle').catch(() => {});
    await page.waitForTimeout(ms);
  }

  // 1. Discover page — default (mood tab)
  console.log('Capturing discover-dark.png ...');
  await page.goto(`${BASE}/discover`, { waitUntil: 'networkidle' });
  await settle(2000);
  await page.screenshot({ path: `${OUT}/discover-dark.png`, fullPage: true });

  // 2. Discover — Trending tab
  console.log('Capturing discover-trending-dark.png ...');
  await page.goto(`${BASE}/discover`, { waitUntil: 'networkidle' });
  await settle(2000);
  // Click "Trending" tab
  const trendingBtn = page.locator('button.segment-btn', { hasText: 'Trending' });
  await trendingBtn.click();
  await settle(3000);
  await page.screenshot({ path: `${OUT}/discover-trending-dark.png`, fullPage: true });

  // 3. Discover — From Library tab
  console.log('Capturing discover-library-dark.png ...');
  await page.goto(`${BASE}/discover`, { waitUntil: 'networkidle' });
  await settle(2000);
  const libraryBtn = page.locator('button.segment-btn', { hasText: 'From Library' });
  await libraryBtn.click();
  await settle(5000); // Library auto-loads, needs more time
  await page.screenshot({ path: `${OUT}/discover-library-dark.png`, fullPage: true });

  // 4. Movie detail page (pick a known TMDB ID — Inception: 27205)
  console.log('Capturing movie-detail-dark.png ...');
  await page.goto(`${BASE}/discover/movie/27205`, { waitUntil: 'networkidle' });
  await settle(3000);
  await page.screenshot({ path: `${OUT}/movie-detail-dark.png`, fullPage: true });

  // 5. Discover — Thriller mood
  console.log('Capturing discover-thriller-dark.png ...');
  await page.goto(`${BASE}/discover`, { waitUntil: 'networkidle' });
  await settle(2000);
  const thrillerBtn = page.locator('button', { hasText: 'Thriller' }).first();
  await thrillerBtn.click();
  await settle(4000);
  await page.screenshot({ path: `${OUT}/discover-thriller-dark.png`, fullPage: true });

  // --- Light mode versions ---
  const ctxLight = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    colorScheme: 'light',
  });
  const pageLight = await ctxLight.newPage();

  async function settleLight(ms = 1500) {
    await pageLight.waitForLoadState('networkidle').catch(() => {});
    await pageLight.waitForTimeout(ms);
  }

  // 6. Discover light
  console.log('Capturing discover-light.png ...');
  await pageLight.goto(`${BASE}/discover`, { waitUntil: 'networkidle' });
  await settleLight(2000);
  await pageLight.screenshot({ path: `${OUT}/discover-light.png`, fullPage: true });

  // 7. Movie detail light
  console.log('Capturing movie-detail-light.png ...');
  await pageLight.goto(`${BASE}/discover/movie/27205`, { waitUntil: 'networkidle' });
  await settleLight(3000);
  await pageLight.screenshot({ path: `${OUT}/movie-detail-light.png`, fullPage: true });

  // --- Mobile screenshots ---
  const ctxMobile = await browser.newContext({
    viewport: { width: 390, height: 844 },
    isMobile: true,
    deviceScaleFactor: 2,
    colorScheme: 'dark',
  });
  const pageMobile = await ctxMobile.newPage();

  async function settleMobile(ms = 1500) {
    await pageMobile.waitForLoadState('networkidle').catch(() => {});
    await pageMobile.waitForTimeout(ms);
  }

  // 8. Mobile discover
  console.log('Capturing mobile-discover.png ...');
  await pageMobile.goto(`${BASE}/discover`, { waitUntil: 'networkidle' });
  await settleMobile(2000);
  await pageMobile.screenshot({ path: `${OUT}/mobile-discover.png` });
  await pageMobile.screenshot({ path: `${OUT}/mobile-discover-full.png`, fullPage: true });

  // 9. Mobile movie detail
  console.log('Capturing mobile-movie-detail.png ...');
  await pageMobile.goto(`${BASE}/discover/movie/27205`, { waitUntil: 'networkidle' });
  await settleMobile(3000);
  await pageMobile.screenshot({ path: `${OUT}/mobile-movie-detail.png` });
  await pageMobile.screenshot({ path: `${OUT}/mobile-movie-detail-full.png`, fullPage: true });

  await browser.close();
  console.log('Done! All screenshots saved to', OUT);
})();
