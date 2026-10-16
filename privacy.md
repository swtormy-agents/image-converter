# Privacy notice – Local Image Converter

HTML version: https://noclaudkit.com/image-converter/privacy.html

- **No uploads.** All decoding and encoding happens inside your browser. Image files and file names are not sent to any server. The page's Content-Security-Policy restricts network connections to this site's own origin (`connect-src 'self'`), and the converter code makes no network requests with your files.
- **Self-hosted code.** All scripts, including the optional HEIC decoder module, are served from this same site. No third-party CDNs, fonts or trackers.
- **No cookies, no analytics, no ads, no accounts.** We do not collect personal data.
- **Theme setting.** The only thing this site stores in your browser is your theme choice (Light or Dark), kept locally in localStorage under the key `lic-theme`. It is never sent anywhere and is not a cookie. Choosing System removes it; you can also clear it by clearing this site's data in your browser.
- **Hosting logs.** The site is hosted on GitHub Pages. GitHub, as the host, may log technical data such as visitor IP addresses for security and operation; see the GitHub Privacy Statement. We do not receive or use these logs.
- **HEIC decoder.** If your browser cannot open a HEIC/HEIF file natively, the page loads a WebAssembly decoder (libheif) from this same site. It runs locally like the rest of the tool.
- **Metadata and limitations.** Converted files do not contain the original EXIF metadata (including GPS location); EXIF orientation is dropped, so some photos may appear rotated. For multi-image HEIC/HEIF files only the first/primary image is converted.

Questions: open an issue in the GitHub repository: https://github.com/swtormy-agents/image-converter
