#!/usr/bin/env python3
"""Spec v3 §5 AC1–AC9 that apply to image-converter. Run: python3 tools/scripts/check-interlinking.py
Reads generated HTML on disk; AC8 reruns tools/gen.py and requires a zero diff."""
import hashlib, html, json, os, re, subprocess, sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
os.chdir(ROOT)

CSP = ("default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self'; "
       "img-src 'self' blob: data:; connect-src 'self'; worker-src 'self'; "
       "object-src 'none'; base-uri 'none'; form-action 'none'")
BASE = 'https://noclaudkit.com/image-converter/'
SITE = 'https://noclaudkit.com'
LANGS = ['en', 'ru', 'zh']
HREFLANG = {'en': 'en', 'ru': 'ru', 'zh': 'zh-Hans'}
PAIRS = [('heic', 'jpg'), ('heic', 'png'), ('webp', 'png'), ('webp', 'jpg'),
         ('avif', 'jpg'), ('avif', 'png'), ('png', 'webp'), ('jpg', 'webp')]
PAGES = ['index.html'] + [f'{a}-to-{b}.html' for a, b in PAIRS] + ['privacy.html', 'licenses.html']
LANDINGS = {f'{a}-to-{b}.html' for a, b in PAIRS}
HEIC_LANDINGS = {'heic-to-jpg.html', 'heic-to-png.html'}
NB = '\u00a0'
ALLOWED_HOSTS = {
    'noclaudkit.com', 'github.com', 'docs.github.com',
    'aomedia.googlesource.com', 'aomedia.org', 'chromium.googlesource.com',
    'code.videolan.org', 'schema.org',
}
# Live hosts already present on main (licenses/privacy). No new ones.
FAILS = []


def fail(ac, msg):
    FAILS.append(f'AC{ac}: {msg}')


def lp(l):
    return '' if l == 'en' else l + '/'


def url(l, p):
    return BASE + lp(l) + ('' if p == 'index.html' else p)


def home_path(l):
    return '/' if l == 'en' else f'/{l}/'


def conv_path(l):
    return '/image-converter/' if l == 'en' else f'/image-converter/{l}/'


def pdf_path(l):
    return '/pdf/' if l == 'en' else f'/pdf/{l}/'


def page_path(l, p):
    return ROOT / (lp(l) + p)


def rel_path(l, p):
    return lp(l) + p


I18N = {l: json.loads((ROOT / f'tools/i18n/{l}.json').read_text(encoding='utf-8')) for l in LANGS}


def labels(l):
    T = I18N[l]
    return {
        'home': 'NoClaudKit',
        'conv': T['f_conv'],
        'pdf': T['ft_pdf'],
        'heic': T['ft_heic'],
        'merge': T['ft_merge'],
        'split': T['ft_split'],
        'jpgpdf': T['ft_jpgpdf'],
        'xpdf_jpg': T['xpdf_jpg'],
        'xpdf_heic': T['xpdf_heic'],
        'all': T['ft_all'],
        'crumbs': T['crumbs_aria'],
        'about': T['about_aria'],
        'results': T['results_aria'],
        'read_en': T['read_en'],
    }


def norm(s):
    return html.unescape(s).replace(NB, ' ').replace('\u2009', ' ').strip()


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []  # dicts
        self.scripts = []
        self.navs = []
        self.title = ''
        self.csp = None
        self.canonical = None
        self.alts = []
        self.style_attrs = []
        self.stack = []
        self._cap = None
        self._cap_buf = []
        self._a = None
        self._script = None
        self._nav = None
        self._classes = []

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        self.stack.append(tag)
        if 'style' in d:
            self.style_attrs.append((tag, d.get('style')))
        if tag == 'meta' and d.get('http-equiv') == 'Content-Security-Policy':
            self.csp = d.get('content')
        if tag == 'link' and d.get('rel') == 'canonical':
            self.canonical = d.get('href')
        if tag == 'link' and d.get('rel') == 'alternate':
            self.alts.append((d.get('hreflang'), d.get('href')))
        if tag == 'nav':
            self._nav = {'attrs': d, 'links': []}
        if tag == 'a':
            self._a = {'href': d.get('href', ''), 'attrs': d, 'text': '', 'nav': self._nav,
                       'in_settings': any(True for t in self.stack if False),
                       'cls': d.get('class', ''), 'id': d.get('id', '')}
            # walk open start tags stored? we only have tag names. Use a side stack of classes.
            self._a['parents'] = list(self._classes)
        if tag == 'script':
            self._script = {'type': d.get('type', ''), 'src': d.get('src'), 'text': ''}
        if tag == 'title':
            self._cap, self._cap_buf = 'title', []
        self._classes.append(d.get('class', ''))
        if tag == 'a' and self._a is not None:
            pass

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag == 'a' and self._a is not None:
            self._a['text'] = re.sub(r'\s+', ' ', self._a['text']).strip()
            self.links.append(self._a)
            if self._nav is not None:
                self._nav['links'].append(self._a)
            self._a = None
        if tag == 'script' and self._script is not None:
            self.scripts.append(self._script)
            self._script = None
        if tag == 'nav' and self._nav is not None:
            self.navs.append(self._nav)
            self._nav = None
        if tag == 'title' and self._cap == 'title':
            self.title = ''.join(self._cap_buf)
            self._cap = None
        if self.stack and self.stack[-1] == tag:
            self.stack.pop()
        if self._classes:
            self._classes.pop()

    def handle_data(self, data):
        if self._a is not None:
            self._a['text'] += data
        if self._script is not None:
            self._script['text'] += data
        if self._cap:
            self._cap_buf.append(data)

    def feed(self, src):
        self._classes = []
        super().feed(src)


def parse(src):
    p = Page()
    try:
        p.feed(src)
    except Exception as ex:
        fail(0, f'HTML parse error: {ex}')
    return p


def path_lang(href):
    if not href or href.startswith(('#', 'mailto:', 'https://', 'http://')):
        return None
    path = href.split('?')[0]
    if path.startswith('/image-converter/ru/') or path.rstrip('/') == '/image-converter/ru':
        return 'ru'
    if path.startswith('/image-converter/zh/') or path.rstrip('/') == '/image-converter/zh':
        return 'zh'
    if path.startswith('/image-converter/'):
        return 'en'
    if path.startswith('/pdf/ru/') or path.rstrip('/') == '/pdf/ru':
        return 'ru'
    if path.startswith('/pdf/zh/') or path.rstrip('/') == '/pdf/zh':
        return 'zh'
    if path.startswith('/pdf/'):
        return 'en'
    if path == '/ru' or path == '/ru/' or path.startswith('/ru/'):
        return 'ru'
    if path == '/zh' or path == '/zh/' or path.startswith('/zh/'):
        return 'zh'
    if path.startswith('/'):
        return 'en'
    return None  # relative = same language


def in_settings(link):
    return any('settings' in (c or '').split() for c in link.get('parents', []))


def is_xlang_allowed(link, lang):
    if in_settings(link):
        return True
    if norm(link['text']) == 'Read in English':
        return True
    if link['attrs'].get('hreflang'):
        return True
    return False


def ft_nav(doc):
    for n in doc.navs:
        if n['attrs'].get('aria-labelledby') == 'ft-h' or n['attrs'].get('class') == 'ft':
            return n
        if 'ft' in (n['attrs'].get('class') or '').split():
            return n
    return None


def crumbs_nav(doc):
    for n in doc.navs:
        if 'crumbs' in (n['attrs'].get('class') or '').split():
            return n
    return None


def expected_tools(lang):
    return [
        (home_path(lang), 'NoClaudKit'),
        (conv_path(lang), I18N[lang]['f_conv']),
        (pdf_path(lang), I18N[lang]['ft_pdf']),
        (conv_path(lang) + 'heic-to-jpg.html', I18N[lang]['ft_heic']),
        (pdf_path(lang) + 'merge-pdf.html', I18N[lang]['ft_merge']),
        (pdf_path(lang) + 'split-pdf.html', I18N[lang]['ft_split']),
        (pdf_path(lang) + 'jpg-to-pdf.html', I18N[lang]['ft_jpgpdf']),
    ]


def visible_text_nodes(src, selector_start):
    return src


def check_page(lang, page, src, doc):
    loc = rel_path(lang, page)
    L = labels(lang)

    # AC7 CSP
    if doc.csp != CSP:
        fail(7, f'{loc}: CSP meta not byte-identical')

    # AC9 canonical + hreflang
    if doc.canonical != url(lang, page):
        fail(9, f'{loc}: canonical {doc.canonical!r} != {url(lang, page)!r}')
    want_alts = [(HREFLANG[l], url(l, page)) for l in LANGS] + [('x-default', url('en', page))]
    if doc.alts != want_alts:
        fail(9, f'{loc}: hreflang {doc.alts!r} != {want_alts!r}')

    # no PDF-инструменты
    if 'PDF-инструменты' in src:
        fail(5, f'{loc}: leftover «PDF-инструменты»')

    # no inline style
    if doc.style_attrs:
        fail(7, f'{loc}: inline style= {doc.style_attrs}')

    # results region: fixed aria-label (not live #lh)
    if page not in ('privacy.html', 'licenses.html'):
        m = re.search(r'<section class="results[^"]*"[^>]*>', src)
        if not m:
            fail(1, f'{loc}: missing section.results')
        else:
            tag = m.group(0)
            if 'aria-labelledby' in tag:
                fail(1, f'{loc}: results still has aria-labelledby (name must not follow #lh)')
            want = f'aria-label="{L["results"]}"'
            if want not in tag:
                fail(1, f'{loc}: results aria-label missing or wrong (want {L["results"]!r} in {tag})')

    # AC1 footer
    ft = ft_nav(doc)
    if not ft:
        fail(1, f'{loc}: missing nav.ft')
    else:
        hrefs = [(a['href'], norm(a['text'])) for a in ft['links']]
        exp = [(h, norm(t)) for h, t in expected_tools(lang)]
        if hrefs != exp:
            fail(1, f'{loc}: footer 7 links {hrefs!r} != {exp!r}')
        if not any(a['href'] == home_path(lang) for a in ft['links']):
            fail(1, f'{loc}: no same-language home link')
        # current page stays <a aria-current="page">
        cur = conv_path(lang) if page == 'index.html' else conv_path(lang) + page
        for a in ft['links']:
            if a['href'] == cur and a['attrs'].get('aria-current') != 'page':
                fail(1, f'{loc}: footer current {cur} missing aria-current')
            if a['href'] != cur and a['attrs'].get('aria-current') == 'page':
                fail(1, f'{loc}: footer unexpected aria-current on {a["href"]}')
        noc = ft['links'][0]
        if noc['attrs'].get('translate') != 'no':
            fail(1, f'{loc}: NoClaudKit missing translate=no')

    # AC1 same-language hrefs
    for a in doc.links:
        pl = path_lang(a['href'])
        if pl and pl != lang and not is_xlang_allowed(a, lang):
            fail(1, f'{loc}: cross-language href {a["href"]!r} text={a["text"]!r}')

    # AC3 contextual jpg-to-pdf
    xpdf_href = pdf_path(lang) + 'jpg-to-pdf.html'
    contextual = [a for a in doc.links
                  if a['href'] == xpdf_href and not (a['nav'] and 'ft' in (a['nav']['attrs'].get('class') or '').split())]
    if page in LANDINGS:
        if len(contextual) != 1:
            fail(3, f'{loc}: expected 1 contextual jpg-to-pdf, got {len(contextual)} {[a["text"] for a in contextual]}')
        else:
            want = L['xpdf_heic'] if page in HEIC_LANDINGS else L['xpdf_jpg']
            if norm(contextual[0]['text']) != norm(want):
                fail(3, f'{loc}: contextual anchor {contextual[0]["text"]!r} != {want!r}')
    elif page == 'index.html':
        hub = [a for a in doc.links if a['href'] == pdf_path(lang)
               and not (a['nav'] and 'ft' in (a['nav']['attrs'].get('class') or '').split())]
        if len(hub) != 1 or norm(hub[0]['text']) != norm(L['pdf']):
            fail(3, f'{loc}: hub PDF tools link {[(a["href"], a["text"]) for a in hub]!r}')
    else:
        if contextual:
            fail(3, f'{loc}: unexpected contextual jpg-to-pdf on doc page')

    # AC4 href hygiene (exclude #main, #dl)
    for a in doc.links:
        h = a['href']
        if re.search(r'[?&]utm_|[?&]ref=', h, re.I):
            fail(4, f'{loc}: utm/ref in {h}')
        if '#' in h and not h.rstrip('/').endswith(('#main', '#dl')) and h not in ('#main', '#dl'):
            # allow only those two fragments
            frag = h.split('#', 1)[1]
            if frag not in ('main', 'dl'):
                fail(4, f'{loc}: hash in {h}')
        if a['attrs'].get('rel', '').lower().find('nofollow') >= 0:
            fail(4, f'{loc}: nofollow on {h}')
        if 'onclick' in a['attrs']:
            fail(4, f'{loc}: onclick on {h}')

    # AC5 anchors ≤2, no free/online
    counts = {}
    for a in doc.links:
        if in_settings(a):
            continue
        if norm(a['text']) == 'Read in English':
            continue
        key = norm(a['text'])
        if not key:
            continue
        counts[key] = counts.get(key, 0) + 1
    for k, n in counts.items():
        if n > 2:
            fail(5, f'{loc}: anchor {k!r} appears {n}×')
        if re.search(r'(?i)\b(free|online)\b', k):
            fail(5, f'{loc}: free/online in anchor {k!r}')

    # AC6 breadcrumbs + JSON-LD
    cr = crumbs_nav(doc)
    if not cr:
        fail(6, f'{loc}: missing nav.crumbs')
    else:
        if cr['attrs'].get('aria-label') != L['crumbs']:
            fail(6, f'{loc}: crumbs aria-label {cr["attrs"].get("aria-label")!r}')
        if NB in (cr['attrs'].get('aria-label') or ''):
            fail(6, f'{loc}: NBSP in crumbs aria-label')
        # last item is span, not a link — count links vs expected trail
        n_links = len(cr['links'])
        if page == 'index.html':
            if n_links != 1:
                fail(6, f'{loc}: hub crumbs should have 1 link, got {n_links}')
        else:
            if n_links != 2:
                fail(6, f'{loc}: landing crumbs should have 2 links, got {n_links}')
        if cr['links'] and cr['links'][0]['attrs'].get('translate') != 'no':
            fail(6, f'{loc}: crumb NoClaudKit missing translate=no')
        if '›' in src[src.find('class="crumbs"'):src.find('class="crumbs"') + 800] if 'class="crumbs"' in src else '':
            fail(6, f'{loc}: literal › in crumbs HTML')

    if NB in doc.title:
        fail(6, f'{loc}: NBSP in <title>')

    bread = None
    for sc in doc.scripts:
        if sc['type'] != 'application/ld+json':
            continue
        raw = sc['text']
        if '<' in raw or '>' in raw:
            fail(6, f'{loc}: raw < or > in JSON-LD')
        if '&' in raw:
            fail(6, f'{loc}: raw & in JSON-LD')
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as ex:
            fail(6, f'{loc}: invalid JSON-LD: {ex}')
            continue
        if data.get('@type') == 'BreadcrumbList':
            bread = (data, raw)
    if not bread:
        fail(6, f'{loc}: missing BreadcrumbList JSON-LD')
    else:
        data, raw = bread
        items = data.get('itemListElement') or []
        want_n = 2 if page == 'index.html' else 3
        if len(items) != want_n:
            fail(6, f'{loc}: BreadcrumbList length {len(items)} != {want_n}')
        names_ld = [it.get('name', '') for it in items]
        if any(NB in n for n in names_ld):
            fail(6, f'{loc}: NBSP in JSON-LD name {names_ld!r}')
        # visible trail names (crumbs ol text) via regex
        m = re.search(r'<nav class="crumbs"[^>]*>(.*?)</nav>', src, re.S)
        if m:
            vis = re.findall(r'<a[^>]*>(.*?)</a>|<span aria-current="page">(.*?)</span>', m.group(1), re.S)
            vis_names = [norm(html.unescape(re.sub(r'<[^>]+>', '', a or b))) for a, b in vis]
            ld_names = [norm(n) for n in names_ld]
            if vis_names != ld_names:
                fail(6, f'{loc}: JSON-LD names {ld_names!r} != visible {vis_names!r}')
        for it in items:
            item = it.get('item', '')
            if not item.startswith('https://noclaudkit.com/'):
                fail(6, f'{loc}: JSON-LD item not absolute canonical {item!r}')
            il = path_lang(urlparse(item).path) or 'en'
            if il != lang:
                fail(6, f'{loc}: JSON-LD item cross-language {item!r}')
        if '\\u003c' not in raw and '<' in json.dumps(data):
            pass  # nothing to escape unless < appears
        # type exactly application/ld+json already required

    # AC7 hosts
    for m in re.finditer(r'''(?:href|src|content)=["'](https?://[^"']+)["']''', src):
        host = urlparse(m.group(1)).netloc
        if host and host not in ALLOWED_HOSTS:
            fail(7, f'{loc}: new host {host} in {m.group(1)}')

    # scripts: only existing + JSON-LD
    for sc in doc.scripts:
        if sc['src']:
            if sc['src'] not in ('theme.js', '../theme.js', 'config.js', '../config.js',
                                 'zip.js', '../zip.js', 'app.js', '../app.js'):
                fail(7, f'{loc}: unexpected script src {sc["src"]}')
        elif sc['type'] != 'application/ld+json':
            fail(7, f'{loc}: inline script that is not JSON-LD')


def ac8_rerun():
    before = {}
    paths = []
    for lang in LANGS:
        for p in PAGES:
            fp = page_path(lang, p)
            before[str(fp)] = fp.read_bytes()
            paths.append(fp)
    for extra in (ROOT / 'sitemap.xml', ROOT / 'robots.txt'):
        before[str(extra)] = extra.read_bytes()
        paths.append(extra)
    subprocess.run([sys.executable, str(ROOT / 'tools/gen.py')], check=True, cwd=ROOT)
    dirty = []
    for fp in paths:
        if fp.read_bytes() != before[str(fp)]:
            dirty.append(str(fp.relative_to(ROOT)))
    if dirty:
        fail(8, 'generator rerun produced a diff: ' + ', '.join(dirty))


def ac9_vs_main():
    """Canonical + hreflang byte-identical to origin/main (those tags only)."""
    r = subprocess.run(['git', 'show', 'origin/main:index.html'], capture_output=True, text=True)
    if r.returncode != 0:
        return  # no baseline
    for lang in LANGS:
        for p in PAGES:
            rel = rel_path(lang, p)
            old = subprocess.run(['git', 'show', f'origin/main:{rel}'], capture_output=True, text=True)
            if old.returncode != 0:
                continue
            new = page_path(lang, p).read_text(encoding='utf-8')
            def grab(s):
                can = re.search(r'<link rel="canonical"[^>]*>', s)
                alts = re.findall(r'<link rel="alternate"[^>]*>', s)
                return (can.group(0) if can else None, ''.join(alts))
            if grab(old.stdout) != grab(new):
                fail(9, f'{rel}: canonical/hreflang changed vs origin/main')
            oc = re.search(r'<meta http-equiv="Content-Security-Policy" content="([^"]+)">', old.stdout)
            nc = re.search(r'<meta http-equiv="Content-Security-Policy" content="([^"]+)">', new)
            if oc and nc and oc.group(1) != nc.group(1):
                fail(7, f'{rel}: CSP changed vs origin/main')


def main():
    for lang in LANGS:
        for p in PAGES:
            fp = page_path(lang, p)
            if not fp.is_file():
                fail(1, f'missing {rel_path(lang, p)}')
                continue
            src = fp.read_text(encoding='utf-8')
            check_page(lang, p, src, parse(src))
    ac8_rerun()
    ac9_vs_main()
    if FAILS:
        print(f'FAIL ({len(FAILS)})')
        for m in FAILS:
            print(' -', m)
        return 1
    print(f'OK: AC1, AC3–AC9 on {len(LANGS)*len(PAGES)} image-converter pages (AC2 is home-only)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
