# Build tools

## Local CSS build (Tailwind CSS 4 + daisyUI 5)

Pinned, no CDN: `@tailwindcss/cli` 4.3.3 and `daisyui` 5.7.50 (exact versions in
`package.json`, integrity hashes in `package-lock.json`). `node_modules/` is not committed.

```sh
npm --prefix tools ci               # install exact locked versions
npm --prefix tools run build:css    # tools/css/input.css -> build/app.css (minified)
npm --prefix tools run check:css    # builds twice, compares sha256, checks build/app.css is current
                                    # and that the output has no external url() or @import
```

- Input: `tools/css/input.css` (`@import "tailwindcss" source(none)`, daisyUI with the «Лагуна» themes
  `lagoon` / `lagoon-dark`, `@source` = generated pages `*.html`, `ru/*.html`, `zh/*.html`, `tools/gen.py`, `app.js`).
- Output: `build/app.css`, linked from every page (the old hand-written `style.css` was removed with the
  «Лагуна» redesign). CSP is unchanged: the file is same-origin, covered by `style-src 'self'`.
- Run `python3 tools/gen.py` first when page HTML changes, then `build:css`, then `check:css`.

## Pages

`python3 tools/gen.py` regenerates the en/ru/zh pages from `tools/i18n/`.

## E2E (Playwright)

```sh
npm --prefix tools ci && npx --prefix tools playwright install chromium firefox webkit
npm --prefix tools run test:e2e   # chromium, firefox, webkit; serves the repo root on 127.0.0.1:18731
```
