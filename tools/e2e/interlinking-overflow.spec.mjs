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
        if (await page.locator('section.results').count()) {
          const want = { '': 'Your images', 'ru/': 'Ваши изображения', 'zh/': '您的图片' }[loc];
          await expect(page.locator('section.results')).not.toHaveAttribute('aria-labelledby');
          await expect(page.locator('section.results')).toHaveAttribute('aria-label', want);
        }
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
          const deco = await cur.evaluate((el) => {
            const cs = getComputedStyle(el);
            return { line: cs.textDecorationLine, thick: cs.textDecorationThickness, off: cs.textUnderlineOffset };
          });
          expect(deco.line, `aria-current underline at rest on ${loc}${p}`).toContain('underline');
          const px = parseFloat(deco.thick);
          expect(Number.isFinite(px) && px >= 2, `aria-current thickness on ${loc}${p} (${deco.thick})`).toBe(true);
        }
        const ftLink = page.locator('nav.ft a:not([aria-current])').first();
        await ftLink.hover();
        const hoverDeco = await ftLink.evaluate((el) => getComputedStyle(el).textDecorationLine);
        expect(hoverDeco, `footer hover underline on ${loc}${p}`).toContain('underline');
        if (w === 280 || w === 320) {
          const header = await page.evaluate(() => {
            const nav = document.querySelector('header .navbar');
            const brand = document.querySelector('header .brand');
            const settings = document.querySelector('header details.settings');
            const span = brand.querySelector('span');
            const nr = nav.getBoundingClientRect();
            const br = brand.getBoundingClientRect();
            const sr = settings.getBoundingClientRect();
            const sp = span.getBoundingClientRect();
            return {
              gap: sr.left - br.right,
              whiteSpace: getComputedStyle(brand).whiteSpace,
              brandLines: Math.round(sp.height / parseFloat(getComputedStyle(span).lineHeight || getComputedStyle(span).fontSize)),
              spanScrollW: span.scrollWidth,
              spanClientW: span.clientWidth,
              brandClipped: br.left < nr.left - 1 || br.right > nr.right + 1,
              settingsClipped: sr.left < nr.left - 1 || sr.right > nr.right + 1,
              overlap: sr.left < br.right - 0.5,
            };
          });
          expect(header.whiteSpace, `brand nowrap ${loc}${p} @${w}`).toBe('nowrap');
          expect(header.brandLines, `brand single line ${loc}${p} @${w}`).toBeLessThanOrEqual(1);
          expect(header.spanScrollW, `brand text not clipped ${loc}${p} @${w}`).toBeLessThanOrEqual(header.spanClientW + 1);
          expect(header.brandClipped, `brand in navbar ${loc}${p} @${w}`).toBe(false);
          expect(header.settingsClipped, `settings in navbar ${loc}${p} @${w}`).toBe(false);
          expect(header.overlap, `brand/settings no overlap ${loc}${p} @${w}`).toBe(false);
          expect(header.gap, `header gap ${loc}${p} @${w} (${header.gap})`).toBeGreaterThanOrEqual(10);
        }
        for (const theme of THEMES) {
          await page.evaluate((t) => document.documentElement.setAttribute('data-theme', t), theme);
          const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
          expect(overflow, `${loc}${p} @${w} ${theme}`).toBeLessThanOrEqual(0);
        }
      }
    }
  });
}
