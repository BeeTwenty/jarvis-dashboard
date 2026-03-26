const { chromium } = require('playwright');

const BASE = 'http://192.168.0.2:3000';
const OUT = __dirname;

// LinkedIn optimal: 1080x1350 (4:5 portrait) or 1080x1080 (square)
const WIDTH = 1080;
const HEIGHT = 1350;

(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });

  const ctx = await browser.newContext({
    viewport: { width: WIDTH, height: HEIGHT },
    colorScheme: 'dark',
    deviceScaleFactor: 2,
  });
  const page = await ctx.newPage();

  async function settle(ms = 2000) {
    await page.waitForLoadState('networkidle').catch(() => {});
    await page.waitForTimeout(ms);
  }

  // 1. Overview — capture viewport only (no scroll)
  console.log('1. Overview...');
  await page.goto(BASE, { waitUntil: 'networkidle' });
  await settle(3000);
  await page.screenshot({ path: `${OUT}/linkedin-overview.png` });

  // 2. Discover trending — capture viewport
  console.log('2. Discover trending...');
  await page.goto(`${BASE}/discover`, { waitUntil: 'networkidle' });
  await settle(2000);
  const trendingBtn = page.locator('button.segment-btn', { hasText: 'Trending' });
  await trendingBtn.click();
  await settle(3000);
  await page.screenshot({ path: `${OUT}/linkedin-discover.png` });

  // 3. Movie detail (Inception)
  console.log('3. Movie detail...');
  await page.goto(`${BASE}/discover/movie/27205`, { waitUntil: 'networkidle' });
  await settle(3000);
  await page.screenshot({ path: `${OUT}/linkedin-detail.png` });

  // 4. Media page
  console.log('4. Media page...');
  await page.goto(`${BASE}/media`, { waitUntil: 'networkidle' });
  await settle(3000);
  await page.screenshot({ path: `${OUT}/linkedin-media.png` });

  await browser.close();
  console.log(`Done! 4 images saved at ${OUT}/linkedin-*.png (${WIDTH}x${HEIGHT} @2x)`);
})();
