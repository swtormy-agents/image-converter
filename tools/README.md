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

- Input: `tools/css/input.css` (`@import "tailwindcss" source(none)`, `@plugin "daisyui"`,
  `@source` = generated pages `*.html`, `ru/*.html`, `zh/*.html`).
- Output: `build/app.css`. It is **not linked from any page yet** (the new design is not approved);
  the live stylesheet is still `style.css`. CSP is unchanged: the file is same-origin, so
  `style-src 'self'` will cover it when it is linked.
- Run `python3 tools/gen.py` first when page HTML changes, then `build:css`, then `check:css`.

## Pages

`python3 tools/gen.py` regenerates the en/ru/zh pages from `tools/i18n/`.
