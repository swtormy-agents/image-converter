// Narrow viewports: brand must not crowd the header language label (zh 中文 is the widest).
import { test, expect } from '@playwright/test';

const HOMES = ['index.html', 'ru/index.html', 'zh/index.html'];
const WIDTHS = [280, 320];

for (const home of HOMES) {
  test(`brand–language gap on ${home}`, async ({ page }) => {
    for (const w of WIDTHS) {
      await page.setViewportSize({ width: w, height: 900 });
      await page.goto(home);
      const gap = await page.evaluate(() => {
        const brand = document.querySelector('header .brand');
        const lang = document.querySelector('header details.settings summary span[lang]');
        const br = brand.getBoundingClientRect();
        const lr = lang.getBoundingClientRect();
        return lr.left - br.right;
      });
      expect(gap, `brand→language gap ${home} @${w}px (${gap})`).toBeGreaterThanOrEqual(8);
    }
  });
}
