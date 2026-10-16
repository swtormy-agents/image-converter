# Licences and attributions – Local Image Converter

HTML version: https://noclaudkit.com/image-converter/licenses.html

This site's own code is released under the MIT licence (LICENSE). Third-party components:

## libheif-js 1.23.5 (libheif 1.23.5) — LGPL-3.0

HEIC/HEIF decoding is provided by libheif v1.23.5 (© struktur AG and contributors), compiled to WebAssembly by libheif-js 1.23.5. It bundles libde265 v1.0.15 (© struktur AG, Dirk Farin and contributors; LGPL-3.0) for HEVC decoding only. This site never encodes HEVC/HEIC.

The library is shipped unmodified as a separate, dynamically loaded module (`vendor/libheif/libheif.js`, `vendor/libheif/libheif.wasm`) and is only fetched when needed. You may substitute your own compatible Emscripten build by replacing these two files (see LGPL-NOTICE.md). The decoder can also be disabled via `config.js`.

Licence texts: https://noclaudkit.com/image-converter/licenses/LGPL-3.0-libheif-js.txt, https://noclaudkit.com/image-converter/licenses/GPL-3.0.txt

## Tailwind CSS 4.3.3 — MIT

Build-time CSS framework, used only to generate a local stylesheet; no CDN.

## daisyUI 5.7.50 — MIT

Component plugin for Tailwind CSS, used only at build time; no CDN.

## Browser codecs (WebP, AVIF, JPEG, PNG)

WebP, AVIF, JPEG and PNG decoding/encoding is performed by your browser's built-in codecs; this site ships no copy of them.

## Trademarks

Format names (HEIC, HEIF, WebP, AVIF, JPEG, PNG) are used descriptively only. This site is not affiliated with, endorsed or sponsored by any device maker, browser or software vendor.
