// Brand text → language button border gap (zh 中文 + DejaVu is the tightest case).
import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const FIXTURES = join(__dirname, 'fixtures');

const LOCALES = [
  { prefix: '', lang: 'en' },
  { prefix: 'ru/', lang: 'ru' },
  { prefix: 'zh/', lang: 'zh' },
];
const PAGES = ['index.html', 'heic-to-jpg.html'];
const WIDTHS = [280, 320, 359];

const LATE_TILE_FILES = [
  { name: 'ok1.png', mimeType: 'image/png', buffer: readFileSync(join(FIXTURES, 'ok1.png')) },
  { name: 'ok2.jpg', mimeType: 'image/jpeg', buffer: readFileSync(join(FIXTURES, 'ok2.jpg')) },
];

function paths() {
  return LOCALES.flatMap(({ prefix, lang }) =>
    PAGES.map((page) => ({ path: prefix + page, lang })),
  );
}

function measureGap(page) {
  return page.evaluate(() => {
    const brand = document.querySelector('header .brand');
    const summary = document.querySelector('header details.settings summary');
    const range = document.createRange();
    const nodes = [];
    const walk = (el) => {
      for (const n of el.childNodes) {
        if (n.nodeType === Node.TEXT_NODE && n.textContent.trim()) nodes.push(n);
        else if (n.nodeType === Node.ELEMENT_NODE) walk(n);
      }
    };
    walk(brand);
    if (!nodes.length) throw new Error('no brand text nodes');
    range.setStart(nodes[0], 0);
    const last = nodes[nodes.length - 1];
    range.setEnd(last, last.textContent.length);
    const textRight = range.getBoundingClientRect().right;
    return summary.getBoundingClientRect().left - textRight;
  });
}

async function applyDejaVu(page) {
  await page.addStyleTag({
    content: "html, html * { font-family: 'DejaVu Sans', sans-serif !important; }",
  });
}

async function assertDejaVuLoaded(page) {
  const loaded = await page.evaluate(async () => {
    await document.fonts.load('16px "DejaVu Sans"');
    await document.fonts.ready;
    return document.fonts.check('16px "DejaVu Sans"');
  });
  expect(loaded, 'DejaVu Sans must be loaded before measuring (document.fonts.check)').toBe(true);
}

for (const { path, lang } of paths()) {
  for (const w of WIDTHS) {
    test(`brand→language button gap ${lang} @${w}px (system font) [${path}]`, async ({ page }) => {
      await page.setViewportSize({ width: w, height: 900 });
      await page.goto(path);
      const gap = await measureGap(page);
      expect(gap, `${lang} system @${w} ${path}`).toBeGreaterThanOrEqual(8);
    });
  }
}

test.describe('DejaVu Sans', () => {
  test.use({ bypassCSP: true });

  for (const { path, lang } of paths()) {
    for (const w of WIDTHS) {
      test(`brand→language button gap ${lang} @${w}px [${path}]`, async ({ page }) => {
        await page.setViewportSize({ width: w, height: 900 });
        await page.goto(path);
        await applyDejaVu(page);
        await assertDejaVuLoaded(page);
        const gap = await measureGap(page);
        expect(gap, `${lang} dejavu @${w} ${path}`).toBeGreaterThanOrEqual(8);
      });
    }
  }
});

test.describe('header gap stable after fonts and late tiles', () => {
  test.use({ bypassCSP: true });

  const lateCases = [
    { path: 'zh/heic-to-jpg.html', lang: 'zh', w: 359 },
    { path: 'zh/index.html', lang: 'zh', w: 320 },
  ];

  for (const { path, lang, w } of lateCases) {
    test(`gap after fonts.ready reload (${lang} @${w}px) [${path}]`, async ({ page }) => {
      await page.setViewportSize({ width: w, height: 900 });
      await page.goto(path);
      await applyDejaVu(page);
      await assertDejaVuLoaded(page);
      const before = await measureGap(page);
      expect(before, `pre-reload ${lang} @${w}`).toBeGreaterThanOrEqual(8);
      await page.reload();
      await applyDejaVu(page);
      await assertDejaVuLoaded(page);
      const after = await measureGap(page);
      expect(after, `post-reload ${lang} @${w}`).toBeGreaterThanOrEqual(8);
    });

    test(`gap after lazy file tiles (${lang} @${w}px) [${path}]`, async ({ page }) => {
      await page.setViewportSize({ width: w, height: 900 });
      await page.goto(path);
      await applyDejaVu(page);
      await assertDejaVuLoaded(page);
      const baseline = await measureGap(page);
      expect(baseline, `baseline ${lang} @${w}`).toBeGreaterThanOrEqual(8);
      await page.setInputFiles('#files', LATE_TILE_FILES);
      await expect(page.locator('#list > li')).toHaveCount(2);
      await page.locator('#list > li').first().scrollIntoViewIfNeeded();
      const afterTiles = await measureGap(page);
      expect(afterTiles, `after tiles ${lang} @${w}`).toBeGreaterThanOrEqual(8);
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      );
      expect(overflow, `no horizontal scroll after tiles ${lang} @${w}`).toBeLessThanOrEqual(0);
    });
  }
});
