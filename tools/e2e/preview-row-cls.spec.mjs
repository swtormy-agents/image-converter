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
const CORE_FX = ['ok1.png', 'bad1.jpg', 'bad2.jpg', 'ok2.jpg', 'big56mp.png'].map((f) => FX + f);
// CORE: 3 convert OK (ok1, ok2, big56mp), 2 convert fail (bad1, bad2); 3 preview fails (bad1, bad2, big56mp).
const PAD_N = 24;
function padFiles(n = PAD_N) {
  return Array.from({ length: n }, (_, i) => ({ name: `pad-${i}.png`, mimeType: 'image/png', buffer: png() }));
}
function lateBroken(n) {
  return Array.from({ length: n }, (_, i) => ({
    name: `late-bad-${i}.jpg`, mimeType: 'image/jpeg',
    buffer: Buffer.from('QA corrupt test file, not an image.'.repeat(30)),
  }));
}
function watchLh() {
  return () => {
    window.__lh = [];
    document.addEventListener('DOMContentLoaded', () => {
      const lh = document.getElementById('lh');
      new MutationObserver(() => window.__lh.push(lh.textContent)).observe(lh, { childList: true, characterData: true, subtree: true });
    });
  };
}
async function fmtConverted(page, ok, n) {
  return page.evaluate(({ ok, n }) => {
    const I = JSON.parse(document.body.dataset.i18n || '{}');
    return (I.converted || '{ok} of {n} converted').split('{ok}').join(String(ok)).split('{n}').join(String(n));
  }, { ok, n });
}
async function fmtNoPv(page, n) {
  return page.evaluate((n) => {
    const I = JSON.parse(document.body.dataset.i18n || '{}');
    const lang = document.documentElement.lang || 'en';
    const PR = (window.Intl && Intl.PluralRules) ? new Intl.PluralRules(lang) : null;
    const c = PR ? PR.select(n) : (n === 1 ? 'one' : 'other');
    const s = I['noPreviewN_' + c] || I['noPreviewN_other'];
    return s.split('{n}').join(String(n));
  }, n);
}
async function fmtRemoved(page, name, n) {
  return page.evaluate(({ name, n }) => {
    const I = JSON.parse(document.body.dataset.i18n || '{}');
    const lang = document.documentElement.lang || 'en';
    const PR = (window.Intl && Intl.PluralRules) ? new Intl.PluralRules(lang) : null;
    const c = PR ? PR.select(n) : (n === 1 ? 'one' : 'other');
    const s = I['removed_' + c] || I['removed_other'];
    return s.split('{name}').join(name).split('{n}').join(String(n));
  }, { name, n });
}
function npvCounts(after, sum) {
  return after.map((x) => {
    if (x === sum) return 0;
    if (!x.startsWith(sum)) return NaN;
    const rest = x.slice(sum.length);
    const m = rest.match(/(\d+)/);
    return m ? Number(m[1]) : NaN;
  });
}
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

// Megan 0d7ccf9 / L3: Convert immediately (no pre-scroll), scroll only after the summary. Extra rows keep some
// previews untried at summary time in every lang×engine combo. Known failures are announced then; later
// failures rewrite the count (≤1 update per newly found batch, never a lower count after a higher one).
const LATE_N = 2;
const B_N = 5 + PAD_N + LATE_N; // 31
const B_OK = 3 + PAD_N; // 27
const B_NPV_TOTAL = 3 + LATE_N; // 5
for (const [page_, [, npvMark]] of Object.entries(CONV)) {
  test(`Convert immediately, scroll after summary (${page_})`, async ({ page }) => {
    test.setTimeout(120000);
    await page.setViewportSize({ width: 320, height: 640 });
    await page.addInitScript(watchLh());
    await page.goto(page_);
    const sum = await fmtConverted(page, B_OK, B_N);
    await page.setInputFiles('#files', [...CORE_FX, ...padFiles(), ...lateBroken(LATE_N)]);
    await expect(page.locator('#list > li')).toHaveCount(B_N);
    await page.click('#convert');
    await expect(page.locator('#lh')).toContainText(sum, { timeout: 90000 });
    const sk = await page.locator('#list .th.skeleton').count();
    expect(sk, 'previews still untried at summary (late path)').toBeGreaterThan(0);
    const k = await page.locator('#list .th.is-error').count();
    expect(k, 'at least one on-screen preview failure known at summary').toBeGreaterThanOrEqual(1);
    const atSum = `${sum} · ${await fmtNoPv(page, k)}`;
    await expect(page.locator('#lh')).toHaveText(atSum);
    const heights = () => page.locator('#list > li').evaluateAll((ls) => ls.map((l) => l.getBoundingClientRect().height));
    const h0 = await heights();
    await page.mouse.move(160, 400);
    for (let i = 0; i < 40; i++) { await page.mouse.wheel(0, 200); await page.waitForTimeout(40); }
    await page.locator('#list > li').last().scrollIntoViewIfNeeded();
    const final = `${sum} · ${await fmtNoPv(page, B_NPV_TOTAL)}`;
    await expect(page.locator('#list .th.skeleton')).toHaveCount(0, { timeout: 30000 });
    await expect(page.locator('#list .th.is-error')).toHaveCount(B_NPV_TOTAL, { timeout: 30000 });
    await expect(page.locator('#lh')).toHaveText(final, { timeout: 10000 });
    await page.waitForTimeout(1500);
    await expect(page.locator('#lh')).toHaveText(final);
    const log = await page.evaluate(() => window.__lh);
    const iSum = log.findIndex((x) => x.startsWith(sum));
    expect(log.slice(0, iSum).some((x) => x.includes(npvMark)), `no no-preview text during conversion: ${JSON.stringify(log)}`).toBe(false);
    const after = log.slice(iSum);
    expect(after.every((x) => x.startsWith(sum)), `summary kept as prefix: ${JSON.stringify(log)}`).toBe(true);
    const counts = npvCounts(after, sum);
    expect(counts.every((n) => Number.isFinite(n)), `parseable no-preview counts: ${JSON.stringify(after)}`).toBe(true);
    for (let i = 1; i < counts.length; i++) {
      expect(counts[i], `no lower count after a higher one: ${JSON.stringify(after)}`).toBeGreaterThanOrEqual(counts[i - 1]);
      expect(counts[i], `≤1 update per newly found batch (count must change): ${JSON.stringify(after)}`).not.toBe(counts[i - 1]);
    }
    expect(after.at(-1)).toBe(final);
    const h1 = await heights();
    expect(h1, 'preview failures after the summary must not change row heights').toEqual(h0);
  });
}

// L1: convert and never scroll — known on-screen failures are announced at summary while off-screen rows stay skeleton.
const A_N = 5 + PAD_N; // 29
const A_OK = 3 + PAD_N; // 27
for (const page_ of Object.keys(CONV)) {
  test(`#lh announces known preview failures at summary without scroll (${page_})`, async ({ page }) => {
    test.setTimeout(120000);
    await page.setViewportSize({ width: 320, height: 640 });
    await page.goto(page_);
    const sum = await fmtConverted(page, A_OK, A_N);
    await page.setInputFiles('#files', [...CORE_FX, ...padFiles()]);
    await expect(page.locator('#list > li')).toHaveCount(A_N);
    await expect(page.locator('#list .th.is-error')).toHaveCount(1, { timeout: 15000 });
    await expect(page.locator('#list .th.skeleton')).not.toHaveCount(0);
    await page.click('#convert');
    await expect(page.locator('#lh')).toContainText(sum, { timeout: 90000 });
    const sk = await page.locator('#list .th.skeleton').count();
    expect(sk, 'off-screen previews stay untried (no scroll)').toBeGreaterThan(0);
    const k = await page.locator('#list .th.is-error').count();
    expect(k, 'known on-screen failures at summary').toBeGreaterThanOrEqual(1);
    const want = `${sum} · ${await fmtNoPv(page, k)}`;
    await expect(page.locator('#lh')).toHaveText(want);
    await page.waitForTimeout(1500);
    await expect(page.locator('#lh')).toHaveText(want);
    expect(await page.locator('#list .th.skeleton').count(), 'still untried after 1500ms (no scroll)').toBeGreaterThan(0);
  });
}

// Megan L2: removing a failed row after the final announcement keeps the removal message (no recount).
for (const [page_, [sum5]] of Object.entries(CONV)) {
  test(`#lh removal after final announcement is not followed by a recount (${page_})`, async ({ page }) => {
    test.setTimeout(120000);
    await page.setViewportSize({ width: 320, height: 640 });
    await page.addInitScript(watchLh());
    await page.goto(page_);
    await page.setInputFiles('#files', CORE_FX);
    await expect(page.locator('#list > li')).toHaveCount(5);
    await page.locator('#list > li').last().scrollIntoViewIfNeeded();
    await page.waitForTimeout(100);
    await page.click('#convert');
    const final = `${sum5} · ${NPV3[page_]}`;
    await expect(page.locator('#list .th.is-error')).toHaveCount(3, { timeout: 90000 });
    await expect(page.locator('#lh')).toHaveText(final, { timeout: 90000 });
    await page.waitForTimeout(1500);
    await expect(page.locator('#lh')).toHaveText(final);
    const err = page.locator('#list > li').filter({ has: page.locator('.th.is-error') }).first();
    const fileName = await err.locator('.fn').evaluate((el) => el.textContent);
    await err.locator('.rm').click();
    const removed = await fmtRemoved(page, fileName, 4);
    await expect(page.locator('#lh')).toHaveText(removed);
    await page.waitForTimeout(1500);
    await expect(page.locator('#lh')).toHaveText(removed);
    const log = await page.evaluate(() => window.__lh);
    const iRm = log.lastIndexOf(removed);
    expect(iRm, `removal present in ${JSON.stringify(log)}`).toBeGreaterThan(-1);
    expect(log.slice(iRm).every((x) => x === removed), `no no-preview recount after removal: ${JSON.stringify(log)}`).toBe(true);
  });
}
