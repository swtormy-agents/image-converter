# Local Image Converter

Convert images in your browser. Files never leave your device: all decoding and encoding happens locally, nothing is uploaded to a server. Free and open source; no cookies, no analytics, no ads, no account.

Use it: https://noclaudkit.com/image-converter/

## Formats

- Input: HEIC/HEIF, WebP, AVIF, PNG, JPEG. Other image types the browser can decode natively may also work.
- Output: JPEG and PNG in every browser. WebP and AVIF appear in the format list only if your browser can encode them (WebP: Chrome, Edge, Firefox; Safari may not encode WebP).

## How it works

1. Choose files or drop them on the page (several at once is fine).
2. Pick the output format and, for JPEG/WebP/AVIF, the quality (0.5–1.0, default 0.85).
3. Convert. Download each file, or all results as a ZIP (`converted-images.zip`) when at least two files were converted.

Decoding uses the browser's built-in codecs. For HEIC/HEIF files the browser cannot open, a WebAssembly decoder (libheif, LGPL-3.0) is loaded from this same site on first use (this may take a few seconds) and runs locally.

## Notes per output format

- JPG has no transparency, so transparent areas become white.
- PNG is lossless, so files can be larger than the original; the quality slider has no effect.
- WebP keeps transparency and is usually smaller than PNG or JPG.

## Limitations

- EXIF metadata (camera, GPS location, date) is dropped, and EXIF orientation is not applied, so some photos may appear rotated.
- Multi-image HEIC/HEIF: only the first image is converted.
- The tool sets no file-size limit; very large images are limited by device memory and browser canvas limits.
- Tested in Chrome/Chromium, Firefox and a WebKit engine build. Safari on macOS and iOS/iPadOS is not fully tested yet.

## Conversion pages (output format preset)

- [HEIC to JPG](https://noclaudkit.com/image-converter/heic-to-jpg.html) · [HEIC to PNG](https://noclaudkit.com/image-converter/heic-to-png.html)
- [WebP to PNG](https://noclaudkit.com/image-converter/webp-to-png.html) · [WebP to JPG](https://noclaudkit.com/image-converter/webp-to-jpg.html)
- [AVIF to JPG](https://noclaudkit.com/image-converter/avif-to-jpg.html) · [AVIF to PNG](https://noclaudkit.com/image-converter/avif-to-png.html)
- [PNG to WebP](https://noclaudkit.com/image-converter/png-to-webp.html) · [JPG to WebP](https://noclaudkit.com/image-converter/jpg-to-webp.html)

Also available in Russian (https://noclaudkit.com/image-converter/ru/) and Chinese (https://noclaudkit.com/image-converter/zh/).

See also: [Privacy](https://noclaudkit.com/image-converter/privacy.md) · [Licences](https://noclaudkit.com/image-converter/licenses.md) · [Source code](https://github.com/swtormy-agents/image-converter)

Not affiliated with or endorsed by any device, browser or software maker; format names are used descriptively.
