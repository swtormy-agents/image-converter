# LGPL-3.0 notice (HEIC decoder module)
`vendor/libheif/libheif.js` and `vendor/libheif/libheif.wasm` are unmodified files from npm `libheif-js@1.23.5` (libheif 1.23.5 + libde265 1.0.15, LGPL-3.0), copied from `libheif-wasm/`.
- Licence: `licenses/LGPL-3.0-libheif-js.txt`, `licenses/GPL-3.0.txt`.
- Source (exact versions): libheif v1.23.5 https://github.com/strukturag/libheif/tree/v1.23.5 ; libde265 v1.0.15 https://github.com/strukturag/libde265/tree/v1.0.15 ; libheif-js 1.23.5 https://github.com/catdad-experiments/libheif-js/tree/1.23.5 ; prebuilt WASM: https://github.com/catdad-experiments/libheif-emscripten/releases/tag/v1.23.5
- Rebuild: `git clone --branch 1.23.5 https://github.com/catdad-experiments/libheif-js && cd libheif-js && npm ci && npm run fetch` (or build libheif with Emscripten per its `build-emscripten.sh`), then copy `libheif-wasm/libheif.js` and `libheif.wasm` into `vendor/libheif/`.
- The module is loaded lazily and separately only when native decoding of a HEIF file fails. Kill-switch: set `HEIC_WASM_ENABLED: false` in `config.js`.
- Decoding only. This project never encodes HEVC/HEIC.
