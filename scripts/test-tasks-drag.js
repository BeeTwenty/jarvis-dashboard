const { chromium } = require('playwright');

const BASE = 'http://192.168.0.2:3000';
const OUT = '/mnt/z/tmp/jarvis-screenshots';

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  const errors = [];
  page.on('console', msg => {
    if (msg.type() === 'error') {
      errors.push({ time: new Date().toISOString(), text: msg.text() });
    }
  });
  page.on('pageerror', err => {
    errors.push({ time: new Date().toISOString(), text: `PAGE ERROR: ${err.message}` });
  });

  console.log('1. Opening tasks page...');
  await page.goto(`${BASE}/tasks`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);

  // Dump all classes to understand structure
  const allClasses = await page.evaluate(() => {
    return Array.from(document.querySelectorAll('[class]'))
      .map(el => typeof el.className === 'string' ? el.className : '')
      .filter(c => c && (c.includes('task') || c.includes('column') || c.includes('board') || c.includes('drag')))
      .slice(0, 30);
  });
  console.log('   Classes found:', allClasses.slice(0, 10));

  await page.screenshot({ path: `${OUT}/test-01-initial.png`, fullPage: true });

  // Create 3 test tasks
  console.log('2. Creating test tasks...');
  for (let i = 1; i <= 3; i++) {
    const addBtn = page.locator('button').filter({ hasText: 'Add task' }).first();
    await addBtn.click();
    await page.waitForTimeout(400);

    const textarea = page.locator('textarea');
    await textarea.fill(`Drag test ${i}`);
    await page.waitForTimeout(200);

    // Click the "Add" submit button (not "Add task")
    const submitBtn = page.locator('button').filter({ hasText: /^Add$/ });
    await submitBtn.click();
    await page.waitForTimeout(800);
  }

  await page.screenshot({ path: `${OUT}/test-02-created.png`, fullPage: true });

  // Now find the actual task card and column selectors
  const taskInfo = await page.evaluate(() => {
    // Find elements containing "Drag test" text
    const allEls = Array.from(document.querySelectorAll('div'));
    const cls = (el) => typeof el.className === 'string' ? el.className : '';
    const taskCards = allEls.filter(el => {
      const text = el.textContent || '';
      const c = cls(el);
      return text.includes('Drag test') && c && c.includes('task') && !c.includes('taskList');
    });
    const columns = allEls.filter(el => cls(el).includes('taskList'));
    return {
      taskCardClasses: taskCards.map(el => cls(el).substring(0, 80)),
      taskCardCount: taskCards.length,
      columnCount: columns.length,
      columnClasses: columns.map(el => cls(el).substring(0, 80)),
      // Find drag handles
      handleCount: document.querySelectorAll('[class*="dragHandle"], [class*="grip"], [title="Drag to move"]').length,
    };
  });
  console.log('   Task info:', JSON.stringify(taskInfo, null, 2));
  console.log(`   Errors so far: ${errors.length}`);

  // Use title="Drag to move" to find grip handles — these are the drag sources
  const handles = page.locator('[title="Drag to move"]');
  const handleCount = await handles.count();
  console.log(`   Found ${handleCount} drag handles`);

  // Find the 3 column drop zones (taskList)
  const columns = page.locator('[class*="taskList"]');
  const colCount = await columns.count();
  console.log(`   Found ${colCount} columns`);

  if (handleCount === 0 || colCount < 3) {
    console.log('ERROR: Cannot find drag handles or columns. Taking debug screenshot.');
    await page.screenshot({ path: `${OUT}/test-debug.png`, fullPage: true });
    // Dump full page HTML classes
    const html = await page.content();
    require('fs').writeFileSync(`${OUT}/test-debug.html`, html);
    await browser.close();
    return;
  }

  async function dragTo(source, target, label) {
    const srcBox = await source.boundingBox();
    const tgtBox = await target.boundingBox();
    if (!srcBox || !tgtBox) {
      console.log(`   SKIP ${label}: no bounding box`);
      return;
    }

    const srcX = srcBox.x + srcBox.width / 2;
    const srcY = srcBox.y + srcBox.height / 2;
    const tgtX = tgtBox.x + tgtBox.width / 2;
    const tgtY = tgtBox.y + tgtBox.height / 2;

    await page.mouse.move(srcX, srcY);
    await page.mouse.down();
    await page.waitForTimeout(150);

    // Move in steps
    const steps = 8;
    for (let s = 1; s <= steps; s++) {
      await page.mouse.move(
        srcX + (tgtX - srcX) * (s / steps),
        srcY + (tgtY - srcY) * (s / steps),
      );
      await page.waitForTimeout(20);
    }
    await page.waitForTimeout(100);
    await page.mouse.up();
    await page.waitForTimeout(600);
  }

  // Test 1: Drag first task from To Do -> In Progress
  console.log('\n3. Drag tests...');
  console.log('   Test 1: To Do -> In Progress');
  await dragTo(handles.first(), columns.nth(1), 'ToDo->InProgress');
  await page.screenshot({ path: `${OUT}/test-03-drag1.png`, fullPage: true });
  console.log(`   Errors: ${errors.length}`);

  // Test 2: Drag a task from To Do -> Done
  console.log('   Test 2: To Do -> Done');
  await page.waitForTimeout(300);
  let currentHandles = page.locator('[title="Drag to move"]');
  await dragTo(currentHandles.first(), columns.nth(2), 'ToDo->Done');
  await page.screenshot({ path: `${OUT}/test-04-drag2.png`, fullPage: true });
  console.log(`   Errors: ${errors.length}`);

  // Test 3: Drag from In Progress -> Done
  console.log('   Test 3: In Progress -> Done');
  await page.waitForTimeout(300);
  currentHandles = page.locator('[title="Drag to move"]');
  await dragTo(currentHandles.first(), columns.nth(2), 'InProg->Done');
  await page.screenshot({ path: `${OUT}/test-05-drag3.png`, fullPage: true });
  console.log(`   Errors: ${errors.length}`);

  // Test 4-8: Rapid back-and-forth drags
  console.log('\n4. Rapid drag tests...');
  for (let r = 0; r < 5; r++) {
    await page.waitForTimeout(200);
    currentHandles = page.locator('[title="Drag to move"]');
    const hc = await currentHandles.count();
    if (hc === 0) { console.log('   No handles left'); break; }
    const targetCol = columns.nth(r % 3);
    await dragTo(currentHandles.first(), targetCol, `rapid-${r}`);
    console.log(`   Rapid ${r + 1}: -> col ${r % 3}. Errors: ${errors.length}`);
  }

  await page.screenshot({ path: `${OUT}/test-06-rapid.png`, fullPage: true });

  // Test 5: Very fast successive drags (no wait between)
  console.log('\n5. Stress test - no delay between drags...');
  for (let r = 0; r < 3; r++) {
    currentHandles = page.locator('[title="Drag to move"]');
    const hc = await currentHandles.count();
    if (hc === 0) break;
    const targetCol = columns.nth((r + 1) % 3);
    await dragTo(currentHandles.nth(hc > 1 ? 1 : 0), targetCol, `stress-${r}`);
    console.log(`   Stress ${r + 1}: Errors: ${errors.length}`);
  }

  await page.screenshot({ path: `${OUT}/test-07-stress.png`, fullPage: true });

  // Final state check
  await page.waitForTimeout(1000);
  const pageHasError = await page.evaluate(() => {
    return document.body.innerText.includes('Maximum update depth') ||
           document.body.innerText.includes('error');
  });
  console.log(`\n   Page shows error text: ${pageHasError}`);

  // Summary
  console.log('\n═══════════════════════════════════════');
  console.log(`TOTAL ERRORS: ${errors.length}`);
  console.log('═══════════════════════════════════════');
  for (const err of errors) {
    console.log(`[${err.time}]`);
    console.log(err.text.substring(0, 1000));
    console.log('---');
  }

  const fs = require('fs');
  fs.writeFileSync(`${OUT}/test-errors.json`, JSON.stringify(errors, null, 2));
  console.log(`\nSaved to ${OUT}/test-errors.json`);

  await browser.close();
})();
