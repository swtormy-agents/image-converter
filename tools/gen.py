#!/usr/bin/env python3
"""Generates all HTML pages, sitemap.xml and robots.txt. Run: python3 tools/gen.py"""
# NOTE: only writes the pages listed below; never touches google*.html (Search Console verification file, keep, not in sitemap).
import re,os,html
os.chdir(os.path.join(os.path.dirname(__file__),'..'))
BASE='https://swtormy-agents.github.io/local-image-converter/'
CSP="default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self'; img-src 'self' blob: data:; connect-src 'self'; worker-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'"
LIMITS='<p class="note"><b>Limitations:</b> for HEIC/HEIF files with several images (bursts, live photos, sequences) only the first/primary image is converted. EXIF metadata (camera data, GPS location, date) is not kept, and EXIF orientation is not applied, so some photos may come out rotated.</p>'
SAFARI='<p class="note"><b>Browser testing:</b> tested in Chrome/Chromium, Firefox and a WebKit engine build. Safari on macOS and iOS/iPadOS is not fully tested yet; if something does not work there, please report it on GitHub.</p>'
FOOT='</main><footer>Free, open-source, runs entirely in your browser. No uploads, no cookies, no ads. Not affiliated with, endorsed or sponsored by any device maker, browser or software vendor; format names are used descriptively only. Source: <a href="https://github.com/swtormy-agents/local-image-converter">GitHub</a>.<span class="foot-links"><a href="./">Converter</a> <a href="privacy.html">Privacy</a> <a href="licenses.html">Licences</a></span></footer></body></html>\n'
PAIRS=[('heic','jpg','HEIC','JPG','image/jpeg'),('heic','png','HEIC','PNG','image/png'),('webp','png','WebP','PNG','image/png'),('webp','jpg','WebP','JPG','image/jpeg'),
('avif','jpg','AVIF','JPG','image/jpeg'),('avif','png','AVIF','PNG','image/png'),('png','webp','PNG','WebP','image/webp'),('jpg','webp','JPG','WebP','image/webp')]
def head(path,title,desc,out=None):
    url=BASE+path; e=html.escape
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="{CSP}">
<meta name="referrer" content="no-referrer">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title><meta name="description" content="{e(desc)}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="website"><meta property="og:site_name" content="Local Image Converter"><meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}"><meta property="og:url" content="{url}">
<script src="theme.js"></script><link rel="icon" href="favicon.svg"><link rel="stylesheet" href="style.css"></head><body{f' data-out="{out}"' if out else ''}>
<header><div class="brand-wrap"><a class="brand" href="./">Local Image Converter</a><p class="tagline">Files never leave this device</p></div><div class="theme-wrap"><fieldset id="theme" class="seg" aria-describedby="theme-hint"><legend class="visually-hidden">Theme</legend><input type="radio" name="theme" id="theme-system" value="system"><label for="theme-system">System</label><input type="radio" name="theme" id="theme-light" value="light"><label for="theme-light">Light</label><input type="radio" name="theme" id="theme-dark" value="dark"><label for="theme-dark">Dark</label></fieldset><a id="theme-hint" class="theme-hint" href="privacy.html">Saved only in this browser</a></div></header><main>
'''
TOOL='''<section class="tool" aria-label="Converter">
<div id="drop" class="drop" tabindex="0" role="button" aria-label="Choose files or drop here" aria-describedby="drop-hint"><p class="chips" aria-hidden="true"><span class="chip">HEIC</span><span class="chip">PNG</span><span class="chip">WEBP</span><span class="chip">AVIF</span></p><p class="drop-title">Choose files or drop here</p><p id="drop-hint" class="drop-hint">Converted in your browser. Nothing is uploaded. Accepts HEIC, HEIF, WebP, AVIF, PNG, JPEG.</p><p class="drop-note">HEIC/HEIF: only the first image in a file is converted. EXIF and orientation are dropped. If your browser cannot open HEIC natively, the decoder loads on first use and may take a few seconds.</p></div>
<input id="files" class="visually-hidden" type="file" tabindex="-1" aria-hidden="true" multiple accept="image/*,.heic,.heif,.avif,.webp">
<div class="opts">
<label class="field"><span class="field-label">Output format</span><select id="fmt"></select></label>
<label class="field field-q"><span class="field-label">Quality <output id="qv" for="q" class="qv">90%</output></span><input id="q" type="range" min="10" max="100" value="90" aria-valuetext="90%" aria-describedby="q-hint"><span id="q-hint" class="hint">Applies to JPEG and WebP (and AVIF where available).</span></label>
<div class="actions"><button id="convert" class="btn btn-primary" disabled>Convert</button><button id="zip" class="btn btn-secondary" disabled>Download all (.zip)</button><button id="clear" class="btn btn-ghost" disabled>Clear list</button></div>
<p id="action-hint" class="hint action-hint">Add images to enable Convert. ZIP download is available for 2 or more converted files.</p>
</div>
<div class="progress-row"><progress id="prog" max="1" value="0" hidden></progress><p id="status" role="status" aria-live="polite"></p></div>
<ul id="list" class="files"></ul>
</section>
<noscript>This converter needs JavaScript; it runs only on your device.</noscript>
<script src="config.js"></script><script src="zip.js"></script><script src="app.js"></script>
'''
NOTES_BOX='<details class="notes"><summary><b>Limitations and browser support</b> &middot; only the first image in a HEIC/HEIF file is converted; EXIF and orientation are dropped; Safari/iOS not fully tested yet</summary>'+LIMITS+SAFARI+'</details>'
PAIRLINKS='<section class="pairs"><h2>Popular conversions</h2><ul>'+''.join(f'<li><a href="{a}-to-{b}.html">{A} to {B}</a></li>' for a,b,A,B,_ in PAIRS)+'</ul></section>'
pages=[]
def write(path,content): open(path,'w').write(content); pages.append(path)
write('index.html',head('','Local Image Converter – HEIC, WebP, AVIF to JPG/PNG in your browser','Convert HEIC/HEIF, WebP, AVIF, PNG and JPEG images to JPG, PNG or WebP directly in your browser. Files are processed on your device and not uploaded. Free, no ads, no cookies.')
 +'<h1>Convert images locally in your browser</h1>\n<p class="lead">HEIC/HEIF, WebP, AVIF, PNG, JPEG &rarr; JPEG, PNG, WebP (AVIF if your browser can encode it). Your files are processed on your device and never uploaded.</p>\n'+TOOL+NOTES_BOX+'\n'+PAIRLINKS+'\n'+FOOT)
NOTES={'heic':'HEIC/HEIF is opened natively if your browser supports it; otherwise a WebAssembly decoder (libheif) is loaded from this site and runs locally.',
 'webp':'WebP is decoded by your browser\'s built-in decoder.','avif':'AVIF is decoded by your browser\'s built-in decoder (supported in current Chrome, Edge, Firefox and Safari versions).',
 'png':'PNG is decoded by your browser.','jpg':'JPEG is decoded by your browser.'}
OUTN={'jpg':'JPG has no transparency, so transparent areas become white.','png':'PNG is lossless, so files can be larger than the original; the quality slider has no effect.','webp':'WebP output keeps transparency and is usually smaller than PNG or JPG; WebP encoding needs a browser that supports it (Chrome, Edge, Firefox; Safari may not encode WebP).'}
for a,b,A,B,mime in PAIRS:
    t=f'{A} to {B} converter – free, in your browser, no upload | Local Image Converter'
    d=f'Convert {A} images to {B} in your browser. Batch conversion, quality slider, zip download. Files stay on your device; no upload, no ads, no cookies.'
    write(f'{a}-to-{b}.html',head(f'{a}-to-{b}.html',t,d,mime)
     +f'<h1>Convert {A} to {B} in your browser</h1>\n<p class="lead">Choose or drop {A} files, the output is preset to {B}. Conversion runs on your device; the files are not uploaded. You can convert several files at once and download them one by one or as a zip.</p>\n<p>{NOTES[a]} {OUTN[b]} Other formats are accepted too; you can change the output format below.</p>\n'+TOOL+NOTES_BOX+'\n'+PAIRLINKS+'\n'+FOOT)
for f,t,d in [('privacy.html','Privacy notice – Local Image Converter','How Local Image Converter handles your files: processed locally in your browser, no uploads, no cookies, no analytics. Hosting logs by GitHub Pages explained.'),
 ('licenses.html','Licences and attributions – Local Image Converter','Third-party licences used by Local Image Converter: libheif and libde265 (LGPL-3.0) for HEIC decoding, plus browser codec attributions.')]:
    s=open(f).read(); body=re.search(r'<main>\n(.*?)</main>',s,re.S).group(1)
    body=re.sub(r'<p class="note"><b>Browser testing:</b>.*?</p>\n','',body); body=re.sub(r'<section class="pairs">.*?</section>\n','',body)
    write(f,head(f,t,d)+body+SAFARI+'\n'+PAIRLINKS+'\n'+FOOT)
open('sitemap.xml','w').write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+''.join(f'<url><loc>{BASE}{"" if p=="index.html" else p}</loc></url>\n' for p in pages)+'</urlset>\n')
open('robots.txt','w').write(f'User-agent: *\nAllow: /\nSitemap: {BASE}sitemap.xml\n')
print(pages)
