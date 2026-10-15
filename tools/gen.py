#!/usr/bin/env python3
"""Generates all HTML pages (en at root, ru/ and zh/ copies), sitemap.xml and robots.txt. Run: python3 tools/gen.py
Translations live in tools/i18n/<lang>.json (keys ending in _html are authored markup, everything else is
plain text and HTML-escaped here) and tools/i18n/privacy.<lang>.html."""
# NOTE: only writes the pages listed below; never touches google*.html (Search Console verification file, keep, not in sitemap).
import re,os,html,json
os.chdir(os.path.join(os.path.dirname(__file__),'..'))
BASE='https://swtormy-agents.github.io/local-image-converter/'
CSP="default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self'; img-src 'self' blob: data:; connect-src 'self'; worker-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'"
LANGS=['en','ru','zh']
HREFLANG={'en':'en','ru':'ru','zh':'zh-Hans'}
LANG_NAME={'en':'English','ru':'Русский','zh':'中文'}
OG_LOCALE={'en':'en_US','ru':'ru_RU','zh':'zh_CN'}
I18N={l:json.load(open(f'tools/i18n/{l}.json',encoding='utf-8')) for l in LANGS}
PAIRS=[('heic','jpg','HEIC','JPG','image/jpeg'),('heic','png','HEIC','PNG','image/png'),('webp','png','WebP','PNG','image/png'),('webp','jpg','WebP','JPG','image/jpeg'),
('avif','jpg','AVIF','JPG','image/jpeg'),('avif','png','AVIF','PNG','image/png'),('png','webp','PNG','WebP','image/webp'),('jpg','webp','JPG','WebP','image/webp')]
PAGES=['index.html']+[f'{a}-to-{b}.html' for a,b,*_ in PAIRS]+['privacy.html','licenses.html']
e=lambda s:html.escape(str(s),quote=True)
def lp(l): return '' if l=='en' else l+'/'
def url(l,p): return BASE+lp(l)+('' if p=='index.html' else p)
def href(cur,tl,p):
    h=('' if cur=='en' else '../')+lp(tl)+('' if p=='index.html' else p)
    return h or './'

def head(T,lang,page,title,desc,out=None):
    P='' if lang=='en' else '../'
    alts=''.join(f'<link rel="alternate" hreflang="{HREFLANG[l]}" href="{url(l,page)}">' for l in LANGS)+f'<link rel="alternate" hreflang="x-default" href="{url("en",page)}">'
    nav='<nav class="lang-nav" aria-label="'+e(T['lang_nav'])+'"><ul>'+''.join(
        f'<li><a href="{href(lang,l,page)}" lang="{HREFLANG[l]}" hreflang="{HREFLANG[l]}"'+(' aria-current="page"' if l==lang else '')+f'>{e(LANG_NAME[l])}</a></li>' for l in LANGS)+'</ul></nav>'
    attrs=(f' data-out="{e(out)}"' if out else '')+(f' data-i18n="{e(json.dumps(T["js"],ensure_ascii=False))}"' if T.get('js') else '')
    mt=f'<p class="mt-notice" role="note">{T["mt_notice_html"]}</p>' if T.get('mt_notice_html') else ''
    return f'''<!doctype html><html lang="{HREFLANG[lang]}"><head><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="{CSP}">
<meta name="referrer" content="no-referrer">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title><meta name="description" content="{e(desc)}">
<link rel="canonical" href="{url(lang,page)}">
{alts}
<meta property="og:type" content="website"><meta property="og:site_name" content="Local Image Converter"><meta property="og:locale" content="{OG_LOCALE[lang]}"><meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}"><meta property="og:url" content="{url(lang,page)}">
<script src="{P}theme.js"></script><link rel="icon" href="{P}favicon.svg"><link rel="stylesheet" href="{P}style.css"></head><body{attrs}>
<header><div class="brand-wrap"><a class="brand" href="./">Local Image Converter</a><p class="tagline">{e(T['tagline'])}</p></div><div class="header-right">{nav}<div class="theme-wrap"><fieldset id="theme" class="seg" aria-describedby="theme-hint"><legend class="visually-hidden">{e(T['theme'])}</legend><input type="radio" name="theme" id="theme-system" value="system"><label for="theme-system">{e(T['system'])}</label><input type="radio" name="theme" id="theme-light" value="light"><label for="theme-light">{e(T['light'])}</label><input type="radio" name="theme" id="theme-dark" value="dark"><label for="theme-dark">{e(T['dark'])}</label></fieldset><a id="theme-hint" class="theme-hint" href="privacy.html">{e(T['theme_hint'])}</a></div></div></header>{mt}<main>
'''
def tool(T,P):
    return f'''<section class="tool" aria-label="{e(T['converter_label'])}">
<div id="drop" class="drop" tabindex="0" role="button" aria-label="{e(T['drop'])}" aria-describedby="drop-hint"><p class="chips" aria-hidden="true"><span class="chip">HEIC</span><span class="chip">PNG</span><span class="chip">WEBP</span><span class="chip">AVIF</span></p><p class="drop-title">{e(T['drop'])}</p><p id="drop-hint" class="drop-hint">{e(T['drop_hint'])}</p><p class="drop-note">{e(T['drop_note'])}</p></div>
<input id="files" class="visually-hidden" type="file" tabindex="-1" aria-hidden="true" multiple accept="image/*,.heic,.heif,.avif,.webp">
<div class="opts">
<label class="field"><span class="field-label">{e(T['out_fmt'])}</span><select id="fmt"></select></label>
<label class="field field-q"><span class="field-label">{e(T['quality'])} <output id="qv" for="q" class="qv">90%</output></span><input id="q" type="range" min="10" max="100" value="90" aria-valuetext="90%" aria-describedby="q-hint"><span id="q-hint" class="hint">{e(T['q_hint'])}</span></label>
<div class="actions"><button id="convert" class="btn btn-primary" disabled>{e(T['convert'])}</button><button id="zip" class="btn btn-secondary" disabled>{e(T['zip'])}</button><button id="clear" class="btn btn-ghost" disabled>{e(T['clear'])}</button></div>
<p id="action-hint" class="hint action-hint">{e(T['action_hint'])}</p>
</div>
<div class="progress-row"><progress id="prog" max="1" value="0" hidden></progress><p id="status" role="status" aria-live="polite"></p></div>
<ul id="list" class="files"></ul>
</section>
<noscript>{e(T['noscript'])}</noscript>
<script src="{P}config.js"></script><script src="{P}zip.js"></script><script src="{P}app.js"></script>
'''
def safari(T): return '<p class="note">'+T['safari_html']+'</p>'
def notes_box(T): return '<details class="notes"><summary>'+T['notes_summary_html']+'</summary><p class="note">'+T['limits_html']+'</p>'+safari(T)+'</details>'
def pairlinks(T): return '<section class="pairs"><h2>'+e(T['popular'])+'</h2><ul>'+''.join(f'<li><a href="{a}-to-{b}.html">{e(T["pair_link"].format(A=A,B=B))}</a></li>' for a,b,A,B,_ in PAIRS)+'</ul></section>'
def foot(T): return f'</main><footer>{T["foot_html"]}<span class="foot-links"><a href="./">{e(T["f_conv"])}</a> <a href="privacy.html">{e(T["f_priv"])}</a> <a href="licenses.html">{e(T["f_lic"])}</a></span></footer></body></html>\n'
def rebase(body):  # make relative links in English bodies work from /ru/ and /zh/
    return re.sub(r'href="(?!https?:|#|\.\./|mailto:)([^"]+)"',r'href="../\1"',body)

# English privacy/licences bodies are maintained in the root HTML files (read before rewriting).
EN_BODY={}
for f in ('privacy.html','licenses.html'):
    s=open(f,encoding='utf-8').read(); body=re.search(r'<main>\n(.*?)</main>',s,re.S).group(1)
    body=re.sub(r'<p class="note"><b>Browser testing:</b>.*?</p>\n','',body); body=re.sub(r'<section class="pairs">.*?</section>\n','',body)
    EN_BODY[f]=body

def render(lang,T):
    P='' if lang=='en' else '../'; out={}
    out['index.html']=(head(T,lang,'index.html',T['index_title'],T['index_desc'])
     +f'<h1>{e(T["index_h1"])}</h1>\n<p class="lead">{T["index_lead_html"]}</p>\n'+tool(T,P)+notes_box(T)+'\n'+pairlinks(T)+'\n'+foot(T))
    for a,b,A,B,mime in PAIRS:
        p=f'{a}-to-{b}.html'
        out[p]=(head(T,lang,p,T['pair_title'].format(A=A,B=B),T['pair_desc'].format(A=A,B=B),mime)
         +f'<h1>{e(T["pair_h1"].format(A=A,B=B))}</h1>\n<p class="lead">{e(T["pair_lead"].format(A=A,B=B))}</p>\n'+tool(T,P)+f'<p class="pair-notes">{e(T["notes"][a])} {e(T["outn"][b])} {e(T["other_formats"])}</p>\n'+notes_box(T)+'\n'+pairlinks(T)+'\n'+foot(T))
    if lang=='en': pb,lb=EN_BODY['privacy.html'],EN_BODY['licenses.html']
    else:
        pb='<p class="note prevails">'+T['prevails_html']+'</p>\n'+open(f'tools/i18n/privacy.{lang}.html',encoding='utf-8').read()
        lb='<p class="note prevails">'+T['licenses_note_html']+'</p>\n<div lang="en">\n'+rebase(EN_BODY['licenses.html'])+'</div>\n'
    out['privacy.html']=head(T,lang,'privacy.html',T['privacy_title'],T['privacy_desc'])+pb+safari(T)+'\n'+pairlinks(T)+'\n'+foot(T)
    out['licenses.html']=head(T,lang,'licenses.html',T['licenses_title'],T['licenses_desc'])+lb+safari(T)+'\n'+pairlinks(T)+'\n'+foot(T)
    return out

def selftest():
    """Escaping check: inject a markup test string into every plain-text field; it must never appear unescaped."""
    bad='<script>alert(1)</script>'
    T=json.loads(json.dumps(I18N['ru']))
    for k,v in T.items():
        if k.endswith('_html'): continue
        if isinstance(v,str): T[k]=v+bad
        elif k in('notes','outn'): T[k]={kk:vv+bad for kk,vv in v.items()}
        elif k=='js': T[k]={kk:vv+bad for kk,vv in v.items()}
    for p,s in render('ru',T).items():
        assert bad not in s and '<script>alert' not in s, f'unescaped test string in {p}'
        assert '&lt;script&gt;alert(1)' in s, f'escaped test string missing in {p}'
selftest()

pages=[]
for lang in LANGS:
    if lang!='en': os.makedirs(lang,exist_ok=True)
    for p,s in render(lang,I18N[lang]).items():
        open(lp(lang)+p,'w',encoding='utf-8').write(s); pages.append((lang,p))
open('sitemap.xml','w').write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
 +''.join(f'<url><loc>{url(l,p)}</loc>'+''.join(f'<xhtml:link rel="alternate" hreflang="{HREFLANG[x]}" href="{url(x,p)}"/>' for x in LANGS)+f'<xhtml:link rel="alternate" hreflang="x-default" href="{url("en",p)}"/></url>\n' for l,p in pages)+'</urlset>\n')
open('robots.txt','w').write(f'User-agent: *\nAllow: /\nSitemap: {BASE}sitemap.xml\n')
print(len(pages),'pages')
