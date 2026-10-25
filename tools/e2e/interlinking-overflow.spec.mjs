// Spec v3 AC10 (image-converter): no horizontal scroll at 280/320/375/768/1280, en/ru/zh, light+dark.
import { test, expect } from '@playwright/test';

const WIDTHS = [280, 320, 375, 768, 1280];
const LANGS = ['', 'ru/', 'zh/'];
const PAGES = ['index.html', 'heic-to-jpg.html', 'privacy.html', 'licenses.html'];
const THEMES = ['lagoon', 'lagoon-dark'];

for (const loc of LANGS) {
  test(`no horizontal scroll ${loc || 'en'}`, async ({ page }) => {
    test.setTimeout(180000);
    for (const w of WIDTHS) {
      await page.setViewportSize({ width: w, height: 900 });
      for (const p of PAGES) {
        await page.goto(loc + p);
        await expect(page.locator('nav.crumbs')).toHaveCount(1);
        await expect(page.locator('nav.ft')).toHaveCount(1);
        await expect(page.locator('header .brand')).toHaveCount(1);
        await expect(page.locator('header details.settings')).toHaveCount(1);
        const crumbsParent = await page.locator('nav.crumbs').evaluate((el) => el.closest('main') !== null);
        expect(crumbsParent, `crumbs inside main on ${loc}${p}`).toBe(true);
        for (const theme of THEMES) {
          await page.evaluate((t) => document.documentElement.setAttribute('data-theme', t), theme);
          const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
          expect(overflow, `${loc}${p} @${w} ${theme}`).toBeLessThanOrEqual(0);
        }
      }
    }
  });
}
