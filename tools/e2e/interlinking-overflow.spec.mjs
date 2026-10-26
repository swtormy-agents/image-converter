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
        const crumbSeps = await page.locator('nav.crumbs li').evaluateAll((lis) => lis.map((li, i, all) => {
          const after = getComputedStyle(li, '::after').content;
          return { last: i === all.length - 1, after };
        }));
        expect(crumbSeps.length, `crumbs on ${loc}${p}`).toBeGreaterThan(0);
        for (const { last, after } of crumbSeps) {
          if (last) expect(after.includes('/'), `last crumb has no ::after slash on ${loc}${p} (${after})`).toBe(false);
          else expect(after, `crumb separator via ::after on ${loc}${p}`).toMatch(/\//);
        }
        const cur = page.locator('nav.ft a[aria-current="page"]');
        if (await cur.count()) {
          const thick = await cur.evaluate((el) => getComputedStyle(el).textDecorationThickness);
          const px = parseFloat(thick);
          expect(Number.isFinite(px) && px >= 2, `aria-current thickness on ${loc}${p} (${thick})`).toBe(true);
        }
        const ftLink = page.locator('nav.ft a:not([aria-current])').first();
        await ftLink.hover();
        const hoverDeco = await ftLink.evaluate((el) => getComputedStyle(el).textDecorationLine);
        expect(hoverDeco, `footer hover underline on ${loc}${p}`).toContain('underline');
        for (const theme of THEMES) {
          await page.evaluate((t) => document.documentElement.setAttribute('data-theme', t), theme);
          const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
          expect(overflow, `${loc}${p} @${w} ${theme}`).toBeLessThanOrEqual(0);
        }
      }
    }
  });
}
