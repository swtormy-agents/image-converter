// Brand text → language button border gap (zh 中文 + DejaVu is the tightest case).
import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { execSync } from 'node:child_process';
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

const FONT_PROBE_TEXT = 'Local Image Converter 中文';

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

/** True when canvas measureText differs for family vs plain monospace (DejaVu is present). */
async function fontFamilyDiffersFromMonospace(page, family) {
  return page.evaluate(
    async ({ text, family: fam }) => {
      const withFamily = `16px "${fam}", monospace`;
      const monoOnly = '16px monospace';
      await document.fonts.load(withFamily);
      await document.fonts.load(monoOnly);
      await document.fonts.ready;
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      const width = (font) => {
        ctx.font = font;
        return ctx.measureText(text).width;
      };
      return Math.abs(width(withFamily) - width(monoOnly)) > 0.5;
    },
    { text: FONT_PROBE_TEXT, family },
  );
}

async function assertDejaVuLoaded(page) {
  const differs = await fontFamilyDiffersFromMonospace(page, 'DejaVu Sans');
  expect(
    differs,
    'DejaVu Sans must change measureText width vs monospace before gap measurement',
  ).toBe(true);
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

  test.beforeAll(() => {
    const fonts = execSync('fc-list', { encoding: 'utf8' });
    expect(fonts, 'host fc-list should list DejaVu Sans for e2e').toMatch(/DejaVu Sans/i);
  });

  test('font width probe rejects a missing family', async ({ page }) => {
    await page.goto('index.html');
    const differs = await fontFamilyDiffersFromMonospace(page, 'NoSuchFontXYZ123');
    expect(differs, 'unknown font must not differ from monospace-only probe').toBe(false);
  });

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
    { path: 'zh/heic-to-jpg.html', lang: 'zh', w: 280 },
    { path: 'zh/heic-to-jpg.html', lang: 'zh', w: 359 },
    { path: 'zh/index.html', lang: 'zh', w: 280 },
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
