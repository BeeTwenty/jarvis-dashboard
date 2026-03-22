const { chromium } = require('playwright');
const path = require('path');

const BASE_URL = 'http://192.168.0.2:3000';
const OUT_DIR = path.join(__dirname);

const sleep = ms => new Promise(r => setTimeout(r, ms));

async function main() {
  console.log('Launching browser...');
  const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });

  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
    isMobile: true,
    hasTouch: true,
    deviceScaleFactor: 2,
    userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15',
  });

  const page = await context.newPage();

  const pages = [
    { name: 'overview', path: '/', wait: '.page-body' },
    { name: 'system', path: '/system', wait: '.page-body' },
    { name: 'docker', path: '/docker', wait: '.page-body' },
    { name: 'torrents', path: '/torrents', wait: '.page-body' },
    { name: 'media', path: '/media', wait: '.page-body' },
    { name: 'discover', path: '/discover', wait: '.page-body' },
    { name: 'movie-detail', path: '/discover/movie/27205', wait: '.page-body', fullPage: true },
    { name: 'files', path: '/files', wait: '.page-body' },
  ];

  for (const p of pages) {
    console.log(`\nCapturing ${p.name} (mobile)...`);
    try {
      await page.goto(`${BASE_URL}${p.path}`, { waitUntil: 'networkidle', timeout: 30000 });
    } catch {
      await page.goto(`${BASE_URL}${p.path}`, { waitUntil: 'load', timeout: 15000 }).catch(() => {});
    }
    await sleep(2500);

    // Viewport screenshot
    const file = path.join(OUT_DIR, `mobile-${p.name}.png`);
    await page.screenshot({ path: file, fullPage: p.fullPage || false });
    console.log(`  Saved: mobile-${p.name}.png`);

    // Also take a full-page scroll capture for every page
    const fileFull = path.join(OUT_DIR, `mobile-${p.name}-full.png`);
    await page.screenshot({ path: fileFull, fullPage: true });
    console.log(`  Saved: mobile-${p.name}-full.png (full scroll)`);
  }

  await context.close();
  await browser.close();
  console.log('\n=== Done! All mobile screenshots saved ===');
}

main().catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});
