const { chromium } = require('playwright');
const path = require('path');

const BASE_URL = 'http://localhost:3000';
const OUT_DIR = path.join(__dirname);
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function main() {
  console.log('Launching browser...');
  const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
  const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
  const page = await context.newPage();

  // 1. Discover page — click Thriller mood, wait for results
  console.log('Loading Discover page...');
  await page.goto(`${BASE_URL}/discover`, { waitUntil: 'networkidle', timeout: 30000 }).catch(() => {});
  await sleep(2000);

  // Click Thriller mood
  console.log('Clicking Thriller mood...');
  const moods = await page.$$('[class*="moodCard"]');
  for (const m of moods) {
    const text = await m.textContent();
    if (text && text.includes('Thriller')) {
      await m.click();
      break;
    }
  }
  await sleep(3000);

  // Now click "Find Torrent" on the first result card
  console.log('Clicking Find Torrent on first result...');
  const torrentBtns = await page.$$('button');
  for (const btn of torrentBtns) {
    const text = await btn.textContent();
    if (text && text.includes('Find Torrent')) {
      await btn.click();
      break;
    }
  }
  await sleep(4000);

  // Screenshot the torrent search modal
  await page.screenshot({ path: path.join(OUT_DIR, 'discover-torrent-modal-dark.png') });
  console.log('Saved: discover-torrent-modal-dark.png');

  // 2. Movie detail page — click Find Torrent there too
  console.log('\nLoading Inception detail page...');
  await page.goto(`${BASE_URL}/discover/movie/27205`, { waitUntil: 'networkidle', timeout: 30000 }).catch(() => {});
  await sleep(3000);

  // Click Find Torrent
  const detailBtns = await page.$$('button');
  for (const btn of detailBtns) {
    const text = await btn.textContent();
    if (text && text.includes('Find Torrent')) {
      await btn.click();
      break;
    }
  }
  await sleep(4000);

  await page.screenshot({ path: path.join(OUT_DIR, 'detail-torrent-modal-dark.png') });
  console.log('Saved: detail-torrent-modal-dark.png');

  // 3. Discover page — Similar To with autocomplete
  console.log('\nCapturing Similar To autocomplete...');
  await page.goto(`${BASE_URL}/discover`, { waitUntil: 'networkidle', timeout: 30000 }).catch(() => {});
  await sleep(2000);

  // Click Similar To tab
  const tabs = await page.$$('[class*="tab"]');
  for (const tab of tabs) {
    const text = await tab.textContent();
    if (text && text.includes('Similar')) {
      await tab.click();
      break;
    }
  }
  await sleep(1000);

  // Type in the search input
  const input = await page.$('input[placeholder*="Type a movie"]') || await page.$('input[placeholder*="movie"]');
  if (input) {
    await input.fill('Incep');
    await sleep(2000);
    await page.screenshot({ path: path.join(OUT_DIR, 'discover-autocomplete-dark.png') });
    console.log('Saved: discover-autocomplete-dark.png');
  }

  // 4. Global search bar
  console.log('\nCapturing global search...');
  await page.goto(`${BASE_URL}/discover`, { waitUntil: 'networkidle', timeout: 30000 }).catch(() => {});
  await sleep(2000);

  const globalSearch = await page.$('input[placeholder*="Search any"]');
  if (globalSearch) {
    await globalSearch.fill('The Dark Knight');
    await sleep(3000);
    await page.screenshot({ path: path.join(OUT_DIR, 'discover-search-dark.png') });
    console.log('Saved: discover-search-dark.png');
  }

  // 5. From Library tab
  console.log('\nCapturing From Library...');
  await page.goto(`${BASE_URL}/discover`, { waitUntil: 'networkidle', timeout: 30000 }).catch(() => {});
  await sleep(2000);

  const libTab = await page.$$('[class*="tab"]');
  for (const tab of libTab) {
    const text = await tab.textContent();
    if (text && text.includes('Library')) {
      await tab.click();
      break;
    }
  }
  await sleep(1000);

  // Click Analyze button
  const analyzeBtn = await page.$('button:has-text("Analyze")');
  if (analyzeBtn) {
    await analyzeBtn.click();
    await sleep(4000);
  }
  await page.screenshot({ path: path.join(OUT_DIR, 'discover-library-dark.png') });
  console.log('Saved: discover-library-dark.png');

  // 6. Trending tab
  console.log('\nCapturing Trending...');
  await page.goto(`${BASE_URL}/discover`, { waitUntil: 'networkidle', timeout: 30000 }).catch(() => {});
  await sleep(2000);

  const trendTab = await page.$$('[class*="tab"]');
  for (const tab of trendTab) {
    const text = await tab.textContent();
    if (text && text.includes('Trending')) {
      await tab.click();
      break;
    }
  }
  await sleep(4000);
  await page.screenshot({ path: path.join(OUT_DIR, 'discover-trending-dark.png') });
  console.log('Saved: discover-trending-dark.png');

  await context.close();
  await browser.close();
  console.log('\n=== Done! All flow screenshots saved ===');
}

main().catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});
