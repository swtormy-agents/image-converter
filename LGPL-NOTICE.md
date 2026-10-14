# LGPL-3.0 notice (HEIC decoder module)
`vendor/libheif/libheif.js` and `vendor/libheif/libheif.wasm` are unmodified files from npm `libheif-js@1.23.5` (libheif 1.23.x + libde265 1.0.15, LGPL-3.0), copied from `libheif-wasm/`.
- Licence: `licenses/LGPL-3.0-libheif-js.txt`, `licenses/GPL-3.0.txt`.
- Source: https://github.com/strukturag/libheif , https://github.com/strukturag/libde265 , https://github.com/catdad-experiments/libheif-js
- Rebuild: `git clone https://github.com/catdad-experiments/libheif-js && cd libheif-js && npm ci && npm run fetch` (or build libheif with Emscripten per its `build-emscripten.sh`), then copy `libheif-wasm/libheif.js` and `libheif.wasm` into `vendor/libheif/`.
- The module is loaded lazily and separately only when native decoding of a HEIF file fails. Kill-switch: set `HEIC_WASM_ENABLED: false` in `config.js`.
- Decoding only. This project never encodes HEVC/HEIC.
