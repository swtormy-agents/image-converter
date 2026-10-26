// Brand text → language button border gap (zh 中文 + DejaVu is the tightest case).
import { test, expect } from '@playwright/test';

const HOMES = [
  { path: 'index.html', lang: 'en' },
  { path: 'ru/index.html', lang: 'ru' },
  { path: 'zh/index.html', lang: 'zh' },
];
const WIDTHS = [280, 320, 359];

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

for (const { path, lang } of HOMES) {
  for (const w of WIDTHS) {
    test(`brand→language button gap ${lang} @${w}px (system font)`, async ({ page }) => {
      await page.setViewportSize({ width: w, height: 900 });
      await page.goto(path);
      const gap = await measureGap(page);
      expect(gap, `${lang} system @${w}`).toBeGreaterThanOrEqual(8);
    });
  }
}

test.describe('DejaVu Sans', () => {
  test.use({ bypassCSP: true });

  for (const { path, lang } of HOMES) {
    for (const w of WIDTHS) {
      test(`brand→language button gap ${lang} @${w}px`, async ({ page }) => {
        await page.setViewportSize({ width: w, height: 900 });
        await page.goto(path);
        await page.addStyleTag({
          content: "html, html * { font-family: 'DejaVu Sans', sans-serif !important; }",
        });
        const gap = await measureGap(page);
        expect(gap, `${lang} dejavu @${w}`).toBeGreaterThanOrEqual(8);
      });
    }
  }
});
