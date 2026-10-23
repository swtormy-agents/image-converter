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
  test(`320px: error rows keep their height, CLS < 0.01 (${page_})`, async ({ page }) => {
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
    // the error stays accessible: «No preview» text is in the row's accessible text, the tile remains decorative
    const err = rows.filter({ has: page.locator('.th.is-error') }).first();
    await expect(err.locator('.th')).toHaveAttribute('aria-hidden', 'true');
    const npv = await err.locator('.npv').textContent();
    expect(npv.length).toBeGreaterThan(3);
    if (ls) { expect(ls.all).toBeLessThan(0.01); expect(ls.std).toBeLessThan(0.01); }
  });
}
