// Card «Превью: строка с ошибкой растёт на 320 (CLS)»: a failed lazy thumbnail decode must not change the row height.
import { test, expect } from '@playwright/test';
import { deflateSync, crc32 } from 'node:zlib';

function png() { // 2x2 valid PNG
  const chunk = (t, d) => { const b = Buffer.alloc(12 + d.length); b.writeUInt32BE(d.length, 0); b.write(t, 4); d.copy(b, 8); b.writeUInt32BE(crc32(Buffer.concat([Buffer.from(t), d])), 8 + d.length); return b; };
  const ihdr = Buffer.alloc(13); ihdr.writeUInt32BE(2, 0); ihdr.writeUInt32BE(2, 4); ihdr[8] = 8; ihdr[9] = 2;
  return Buffer.concat([Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]), chunk('IHDR', ihdr), chunk('IDAT', deflateSync(Buffer.alloc(14, 0x80))), chunk('IEND', Buffer.alloc(0))]);
}
const files = Array.from({ length: 55 }, (_, i) => i % 3 === 0
  ? { name: `broken-photo-${i}.jpg`, mimeType: 'image/jpeg', buffer: Buffer.from('not really a jpeg '.repeat(20)) }
  : { name: `photo-${i}.png`, mimeType: 'image/png', buffer: png() });

for (const page_ of ['index.html', 'ru/index.html', 'zh/index.html']) {
  test(`320px: error rows keep their height, CLS < 0.01 (${page_})`, async ({ page, browserName }) => {
    await page.setViewportSize({ width: 320, height: 640 });
    await page.addInitScript(() => {
      // emulate a slow lazy decode (like HEIC on a phone) so failures land while rows are on screen
      const d = Object.getOwnPropertyDescriptor(HTMLImageElement.prototype, 'src');
      Object.defineProperty(HTMLImageElement.prototype, 'src', { configurable: true, get() { return d.get.call(this); },
        set(v) { if (String(v).startsWith('blob:') && !this.isConnected) setTimeout(() => d.set.call(this, v), 250); else d.set.call(this, v); } });
      window.__ls = { all: 0, std: 0, n: 0 };
      try { new PerformanceObserver((l) => { for (const e of l.getEntries()) { window.__ls.n++; window.__ls.all += e.value; if (!e.hadRecentInput) window.__ls.std += e.value; } })
        .observe({ type: 'layout-shift', buffered: true }); } catch { window.__ls = null; }
    });
    await page.goto(page_);
    await page.setInputFiles('#files', files);
    const rows = page.locator('#list > li');
    await expect(rows).toHaveCount(55);
    const h0 = await rows.evaluateAll((ls) => ls.map((l) => l.getBoundingClientRect().height));
    // scroll through the list so every lazy thumbnail is decoded
    await page.mouse.move(160, 400);
    for (let i = 0; i < 80; i++) { await page.mouse.wheel(0, 80); await page.waitForTimeout(40); }
    await expect(page.locator('#list .th.skeleton')).toHaveCount(0, { timeout: 15000 });
    await expect(page.locator('#list .th.is-error')).toHaveCount(19);
    const h1 = await rows.evaluateAll((ls) => ls.map((l) => l.getBoundingClientRect().height));
    await page.waitForTimeout(300);
    const ls = await page.evaluate(() => window.__ls);
    console.log(`[${test.info().project.name}] ${page_} row h ${h0[0]}→${Math.max(...h1)} layout-shift`, JSON.stringify(ls));
    expect(new Set(h1).size, 'all rows (ok and error) have one height').toBe(1);
    expect(h1).toEqual(h0);
    expect(h1[0], 'rows stay 94px at 320').toBe(94);
    // the «No preview» label in the error tile is not truncated (Olivia 6a91b5d)
    const fit = await page.locator('#list .th.is-error .th-x').evaluateAll((xs) => xs.map((x) => [x.scrollWidth, x.clientWidth, x.textContent]));
    expect(fit.length).toBe(19);
    for (const [sw, cw, tx] of fit) expect(sw, `.th-x «${tx}» fits (${sw} <= ${cw})`).toBeLessThanOrEqual(cw);
    // the error stays accessible: «No preview» text is in the row's accessible text, the tile remains decorative
    const err = rows.filter({ has: page.locator('.th.is-error') }).first();
    await expect(err.locator('.th')).toHaveAttribute('aria-hidden', 'true');
    const npv = await err.locator('.npv').textContent();
    expect(npv.length).toBeGreaterThan(3);
    // CLS is measured only on chromium: firefox/webkit have no layout-shift API, so a 0 there would be vacuous (Megan 55cc328).
    // Row heights above (h0 == h1 == 94) still cover the no-shift requirement on every engine.
    if (browserName === 'chromium') {
      expect(ls, 'layout-shift API available on chromium').not.toBeNull();
      expect(ls.all).toBeLessThan(0.01); expect(ls.std).toBeLessThan(0.01);
    } else {
      test.info().annotations.push({ type: 'skip', description: `CLS assertion skipped on ${browserName}: no layout-shift API (chromium-only check)` });
      console.log(`[${browserName}] CLS assertion skipped: no layout-shift API, chromium-only`);
    }
  });
}

// Megan 55cc328: preview failures are announced politely in #lh (one coalesced message with the count).
const NPV = { 'index.html': 'No preview for 1 file', 'ru/index.html': 'Нет превью для 1 файла', 'zh/index.html': '1 个文件无预览' };
for (const [page_, msg] of Object.entries(NPV)) {
  test(`#lh announces preview failure (${page_})`, async ({ page }) => {
    await page.setViewportSize({ width: 320, height: 640 });
    await page.goto(page_);
    await expect(page.locator('#lh')).toHaveAttribute('aria-live', 'polite');
    await page.setInputFiles('#files', [
      { name: 'ok1.png', mimeType: 'image/png', buffer: png() },
      { name: 'text.jpg', mimeType: 'image/jpeg', buffer: Buffer.from('QA corrupt test file, not an image.'.repeat(30)) },
    ]);
    await expect(page.locator('#list > li')).toHaveCount(2);
    await page.mouse.move(160, 400); await page.mouse.wheel(0, 200);
    await expect(page.locator('#list .th.is-error')).toHaveCount(1, { timeout: 15000 });
    await expect(page.locator('#lh')).toContainText(msg, { timeout: 5000 });
    const h = await page.locator('#list > li').evaluateAll((ls) => ls.map((l) => l.getBoundingClientRect().height));
    expect(h).toEqual([94, 94]);
  });
}

// Megan 5c59faf: the no-preview announcement must not collide with conversion. While converting it is deferred,
// then announced once appended to the final summary: «<summary> · <noPreviewN>». No no-preview text during conversion.
const FX = new URL('./fixtures/', import.meta.url).pathname;
const CONV = {
  'index.html': ['3 of 5 converted', 'No preview for'],
  'ru/index.html': ['Готово 3 из\u00a05', 'Нет превью для'],
  'zh/index.html': ['已转换 3/5', '个文件无预览'],
};
const NPV3 = { 'index.html': 'No preview for 3 files', 'ru/index.html': 'Нет превью для 3 файлов', 'zh/index.html': '3 个文件无预览' };
for (const [page_, [sum, npvMark]] of Object.entries(CONV)) {
  test(`#lh no-preview waits for conversion summary (${page_})`, async ({ page }) => {
    test.setTimeout(120000);
    await page.setViewportSize({ width: 320, height: 640 });
    await page.addInitScript(() => {
      window.__lh = [];
      document.addEventListener('DOMContentLoaded', () => {
        const lh = document.getElementById('lh');
        new MutationObserver(() => window.__lh.push(lh.textContent)).observe(lh, { childList: true, characterData: true, subtree: true });
      });
    });
    await page.goto(page_);
    await page.setInputFiles('#files', ['ok1.png', 'bad1.jpg', 'bad2.jpg', 'ok2.jpg', 'big56mp.png'].map((f) => FX + f));
    await expect(page.locator('#list > li')).toHaveCount(5);
    await page.locator('#list > li').last().scrollIntoViewIfNeeded(); // lazy previews: bring all rows into the IO margin
    await page.waitForTimeout(100);
    await page.click('#convert');
    await page.mouse.move(160, 400);
    for (let i = 0; i < 10; i++) { await page.mouse.wheel(0, i % 2 ? -60 : 80); await page.waitForTimeout(80); }
    const final = `${sum} · ${NPV3[page_]}`;
    await expect(page.locator('#lh')).toHaveText(final, { timeout: 90000 });
    await page.waitForTimeout(1500); // longer than the 700ms debounce: nothing may follow
    await expect(page.locator('#lh')).toHaveText(final);
    const log = await page.evaluate(() => window.__lh);
    const iSum = log.findIndex((x) => x.startsWith(sum));
    expect(iSum, `summary present in ${JSON.stringify(log)}`).toBeGreaterThan(-1);
    expect(log.slice(0, iSum).some((x) => x.includes(npvMark)), `no no-preview text during conversion: ${JSON.stringify(log)}`).toBe(false);
    expect(log.slice(iSum), `exactly one final announcement: ${JSON.stringify(log)}`).toEqual([final]);
    await expect(page.locator('#list .th.is-error')).toHaveCount(3);
  });
}

// Megan 0d7ccf9: Convert immediately (no pre-scroll), scroll only after the summary. The summary must stay as the #lh prefix
// and the final status must carry the full count; at most one announcement after the summary.
for (const [page_, [sum, npvMark]] of Object.entries(CONV)) {
  test(`Convert immediately, scroll after summary (${page_})`, async ({ page }) => {
    test.setTimeout(120000);
    await page.setViewportSize({ width: 320, height: 640 });
    await page.addInitScript(() => {
      window.__lh = [];
      document.addEventListener('DOMContentLoaded', () => {
        const lh = document.getElementById('lh');
        new MutationObserver(() => window.__lh.push(lh.textContent)).observe(lh, { childList: true, characterData: true, subtree: true });
      });
    });
    await page.goto(page_);
    await page.setInputFiles('#files', ['ok1.png', 'bad1.jpg', 'bad2.jpg', 'ok2.jpg', 'big56mp.png'].map((f) => FX + f));
    await expect(page.locator('#list > li')).toHaveCount(5);
    await page.click('#convert');
    await expect(page.locator('#lh')).toContainText(sum, { timeout: 90000 });
    const heights = () => page.locator('#list > li').evaluateAll((ls) => ls.map((l) => l.getBoundingClientRect().height));
    const h0 = await heights();
    await page.mouse.move(160, 400);
    for (let i = 0; i < 6; i++) { await page.mouse.wheel(0, 200); await page.waitForTimeout(80); }
    await page.locator('#list > li').last().scrollIntoViewIfNeeded();
    const final = `${sum} · ${NPV3[page_]}`;
    await expect(page.locator('#list .th.is-error')).toHaveCount(3, { timeout: 30000 });
    await expect(page.locator('#lh')).toHaveText(final, { timeout: 10000 });
    await page.waitForTimeout(1500);
    await expect(page.locator('#lh')).toHaveText(final);
    const log = await page.evaluate(() => window.__lh);
    const iSum = log.findIndex((x) => x.startsWith(sum));
    expect(log.slice(0, iSum).some((x) => x.includes(npvMark)), `no no-preview text during conversion: ${JSON.stringify(log)}`).toBe(false);
    const after = log.slice(iSum);
    expect(after.every((x) => x.startsWith(sum)), `summary kept as prefix: ${JSON.stringify(log)}`).toBe(true);
    expect(after.length, `at most summary + one update: ${JSON.stringify(log)}`).toBeLessThanOrEqual(2);
    expect(after.at(-1)).toBe(final);
    const h1 = await heights();
    expect(h1, 'preview failures after the summary must not change row heights').toEqual(h0);
  });
}
