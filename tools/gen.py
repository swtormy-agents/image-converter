#!/usr/bin/env python3
"""Generates all HTML pages (en at root, ru/ and zh/ copies), sitemap.xml and robots.txt. Run: python3 tools/gen.py
Translations live in tools/i18n/<lang>.json (keys ending in _html are authored markup, everything else is
plain text and HTML-escaped here) and tools/i18n/privacy.<lang>.html."""
# NOTE: only writes the pages listed below; never touches google*.html (Search Console verification file, keep, not in sitemap).
import re,os,html,json,subprocess
os.chdir(os.path.join(os.path.dirname(__file__),'..'))
BASE='https://noclaudkit.com/image-converter/'
CSP="default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self'; img-src 'self' blob: data:; connect-src 'self'; worker-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'"
LANGS=['en','ru','zh']
HREFLANG={'en':'en','ru':'ru','zh':'zh-Hans'}
LANG_NAME={'en':'English','ru':'Русский','zh':'中文'}
OG_LOCALE={'en':'en_US','ru':'ru_RU','zh':'zh_CN'}
OG_LINE2={'en':'Files never leave this device','ru':'Файлы не отправляются на сервер и не покидают устройство','zh':'文件不会上传到服务器'}
OG_SEP={'en':'. ','ru':'. ','zh':'。'}
def og_alt(T,lang):
    a=re.sub(r'<[^>]*>','',html.unescape(T.get('og_h1',T['index_h1']))).strip()  # plain text of the h1 drawn in the OG image (og_h1, else index_h1; U+00A0 kept)
    if a[-1:] not in '.。!?！？': a+=OG_SEP[lang].rstrip(' ')
    return a+' '*OG_SEP[lang].endswith(' ')+OG_LINE2[lang]
def og_img(lang): return BASE+f'assets/og/og-{lang}.png'  # absolute, same BASE as canonical
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

def jsonld(lang,page,title,desc):
    d={'@context':'https://schema.org','@type':'WebApplication','name':title,'description':desc,'url':url(lang,page),'inLanguage':HREFLANG[lang],
       'applicationCategory':'MultimediaApplication','operatingSystem':'Any','isAccessibleForFree':True,'offers':{'@type':'Offer','price':'0','priceCurrency':'USD'}}
    j=json.dumps(d,ensure_ascii=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    return f'<script type="application/ld+json">{j}</script>\n'
LD_PAGES={'index.html'}|{f'{a}-to-{b}.html' for a,b,*_ in PAIRS}  # JSON-LD on index and tool pages only, not privacy/licences

NB='\u00a0'
RU_SHORT='не|и|с|в|на|к|о|у|а|из|за|по|от|до|я|ни|но|же|ли'
def ru_nbsp(s): return re.sub(r'(?<![\w\u0400-\u04ff])('+RU_SHORT+r') ',lambda m:m.group(1)+NB,s,flags=re.I)
PENDING_RU=('pair_desc',)  # live ru description kept until Sarah approves the new one; guard warns instead of failing
def check_ru(T,path='ru',warn=None):
    """ru sources must carry real U+00A0 after short words (and never the &nbsp; entity). *_html keys are checked
    on their visible text (tags and attributes stripped, entities decoded)."""
    warn=[] if warn is None else warn
    for k,v in (T.items() if isinstance(T,dict) else []):
        if isinstance(v,dict): check_ru(v,path+'.'+k,warn); continue
        if not isinstance(v,str): continue
        assert '&nbsp;' not in v, f'&nbsp; entity in {path}.{k}'
        txt=html.unescape(re.sub(r'<[^>]*>','',v)) if k.endswith('_html') else v
        if ru_nbsp(txt)!=txt:
            if k in PENDING_RU: warn.append(f'{path}.{k}')
            else: raise AssertionError(f'plain space after a short word in {path}.{k}')
    return warn
ICON='<svg viewBox="0 0 28 28" aria-hidden="true"><rect x="1" y="1" width="26" height="26" rx="7"/><path d="M8 18l4-5 3 3 2-2 3 4"/></svg>'
X_ICON='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18"/></svg>'
def head(T,lang,page,title,desc,out=None):
    P='' if lang=='en' else '../'
    ld=jsonld(lang,page,title,desc) if page in LD_PAGES else ''
    alts=''.join(f'<link rel="alternate" hreflang="{HREFLANG[l]}" href="{url(l,page)}">' for l in LANGS)+f'<link rel="alternate" hreflang="x-default" href="{url("en",page)}">'
    nav='<nav aria-label="'+e(T['lang_nav'])+'"><ul class="langs">'+''.join(
        f'<li><a href="{href(lang,l,page)}" lang="{HREFLANG[l]}" hreflang="{HREFLANG[l]}"'+(' aria-current="page"' if l==lang else '')+f'>{e(LANG_NAME[l])}</a></li>' for l in LANGS)+'</ul></nav>'
    theme='<div class="theme"><label for="theme">'+e(T['theme'])+'</label><select id="theme" name="theme">'+''.join(f'<option value="{v}">{e(T[v])}</option>' for v in ('system','light','dark'))+'</select></div>'
    attrs=(f' data-out="{e(out)}"' if out else '')+(f' data-i18n="{e(json.dumps(T["js"],ensure_ascii=False))}"' if T.get('js') and page in LD_PAGES else '')
    mt=(f'<div class="mt" role="note"><div class="wrap"><span>{T["mt_notice_html"]}</span> <a href="{href(lang,"en",page)}" lang="en" hreflang="en">{e(T["read_en"])}</a></div></div>') if T.get('mt_notice_html') else ''
    return f'''<!doctype html><html lang="{HREFLANG[lang]}"><head><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="{CSP}">
<meta name="referrer" content="no-referrer">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title><meta name="description" content="{e(desc)}">
<link rel="canonical" href="{url(lang,page)}">
{alts}
<meta property="og:type" content="website"><meta property="og:site_name" content="Local Image Converter"><meta property="og:locale" content="{OG_LOCALE[lang]}"><meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}"><meta property="og:url" content="{url(lang,page)}">
<meta property="og:image" content="{og_img(lang)}"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:image:type" content="image/png"><meta property="og:image:alt" content="{e(og_alt(T,lang))}">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="{og_img(lang)}"><meta name="twitter:image:alt" content="{e(og_alt(T,lang))}">
<meta name="color-scheme" content="light dark">
{ld}<script src="{P}theme.js"></script><link rel="icon" href="{P}favicon.svg"><link rel="stylesheet" href="{P}style.css"></head><body{attrs}>
{mt}<header class="wrap top"><a class="brand" href="./" translate="no">{ICON}Local Image Converter</a><div class="prefs">{nav}{theme}</div></header>
<main class="wrap">
'''
def hero(h1,lede,T,pnote=''):
    return (f'<section class="hero"><h1>{e(h1)}</h1><p class="lede">{e(lede)}</p><p class="lede-m">{e(T["lede_m"])}</p>'
            +(f'<p class="pnote">{e(pnote)}</p>' if pnote else '')+'</section>\n')
def tool(T,P,heic=True):
    return f'''<label class="drop" for="files" id="drop"><input id="files" name="files" type="file" multiple accept="image/*,.heic,.heif,.avif,.webp"><ul class="pills" aria-hidden="true"><li>HEIC</li><li>WebP</li><li>AVIF</li><li>PNG</li><li>JPEG</li></ul><span class="dt">{e(T['drop'])}</span><span class="ds">{e(T['drop_sub'])}</span>{f'<span class="hn">{e(T["heic_note"])}</span>' if heic else ''}</label>
<section class="controls" aria-label="{e(T['converter_label'])}"><div class="fields"><div class="field"><label for="fmt">{e(T['out_fmt'])}</label><select id="fmt" name="format"><option value="image/jpeg">JPEG</option><option value="image/png">PNG</option></select></div>
<div class="field"><label for="q">{e(T['quality_label'])}</label><div class="qrow"><input id="q" name="quality" type="range" min="0.5" max="1" step="0.05" value="0.85"><output id="qv" for="q" class="qv">{e(T['q_default'])}</output></div></div></div>
<div class="bar"><div class="actions"><button id="clear" type="button" class="btn sec" disabled>{e(T['clear'])}</button><button id="zip" type="button" class="btn sec" disabled>{e(T['zip'])}</button><button id="convert" type="button" class="btn pri" disabled>{e(T['js']['convert0'])}</button></div></div>
<noscript><p>{e(T['noscript'])}</p></noscript></section>
<section class="list" aria-labelledby="lh"><h2 id="lh" class="lh" aria-live="polite">{e(T['js']['empty'])}</h2><ul id="list"></ul></section>
<script src="{P}config.js"></script><script src="{P}zip.js"></script><script src="{P}app.js"></script>
'''
def limits(T,extra=''):
    return f'<details class="lim"><summary>{e(T["lim"])}</summary><p>{e(T["lim_p"])}</p>'+(f'<p>{e(extra)}</p>' if extra else '')+'</details>\n'
def more(T,lede,pnote='',extra='',heic=True):
    ps=[lede]+([pnote] if pnote else [])+([T['heic_note']] if heic else [])+[T['lim_p']]+([extra] if extra else [])
    return f'<details class="more"><summary>{e(T["more"])}</summary>'+''.join(f'<p>{e(x)}</p>' for x in ps)+'</details>\n'
def safari(T): return '<p class="note">'+T['safari_html']+'</p>'
def pairlinks(T): return '<section class="pop" aria-labelledby="pp"><h2 id="pp">'+e(T['popular'])+'</h2><ul class="pairs">'+''.join(f'<li><a href="{a}-to-{b}.html">{e(T["pair_link"].format(A=A,B=B))}</a></li>' for a,b,A,B,_ in PAIRS)+'</ul></section>'
def foot(T):
    links=[('./',T['f_conv']),('privacy.html',T['f_priv']),('licenses.html',T['f_lic']),('https://github.com/swtormy-agents/image-converter','GitHub')]
    return (f'</main>\n<footer class="wrap"><p><span class="foot-x">{e(T["foot"])} </span>{e(T["legal"])}</p><ul class="flinks">'
            +''.join(f'<li><a href="{h}">{e(t)}</a></li>' for h,t in links)+'</ul></footer></body></html>\n')
def rebase(body):  # make relative links in English bodies work from /ru/ and /zh/
    return re.sub(r'href="(?!https?:|#|\.\./|mailto:)([^"]+)"',r'href="../\1"',body)

# English privacy/licences bodies are maintained in the root HTML files (read before rewriting).
EN_BODY={}
for f in ('privacy.html','licenses.html'):
    s=open(f,encoding='utf-8').read(); body=re.search(r'<main[^>]*>\n(.*?)</main>',s,re.S).group(1)
    body=re.sub(r'<p class="note"><b>Browser testing:</b>.*?</p>\n','',body); body=re.sub(r'<section class="(?:pairs|pop)".*?</section>\n','',body)
    EN_BODY[f]=body

def render(lang,T):
    P='' if lang=='en' else '../'; out={}
    out['index.html']=(head(T,lang,'index.html',T['index_title'],T['index_desc'])
     +hero(T['index_h1'],T['index_lead'],T)+tool(T,P)+limits(T)+more(T,T['index_lead'])+pairlinks(T)+'\n'+foot(T))
    for a,b,A,B,mime in PAIRS:
        p=f'{a}-to-{b}.html'; lead=T['pair_lead'].format(A=A,B=B); dec=T['notes'][a] if a=='heic' else ''
        out[p]=(head(T,lang,p,T['pair_title'].format(A=A,B=B),T['pair_desc'].format(A=A,B=B),mime)
         +hero(T['pair_h1'].format(A=A,B=B),lead,T,T['outn'][b])+tool(T,P,a=='heic')+limits(T,dec)+more(T,lead,T['outn'][b],dec,a=='heic')+pairlinks(T)+'\n'+foot(T))
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
        for m in re.findall(r'<script type="application/ld\+json">(.*?)</script>',s,re.S):
            assert '<' not in m and '>' not in m and '&' not in m, f'raw markup in JSON-LD in {p}'
            assert json.loads(m)['name'].endswith(bad), f'JSON-LD name mismatch in {p}'
selftest()
for _w in check_ru(I18N["ru"]): print("warning (pending approval, not changed):",_w)
for _l in LANGS:
    assert os.path.isfile(f'assets/og/og-{_l}.png'), f'missing og image for {_l}'
    _a=og_alt(I18N[_l],_l); assert '..' not in _a and '。。' not in _a and '.。' not in _a, f'double punctuation in og alt {_l}'

pages=[]
for lang in LANGS:
    if lang!='en': os.makedirs(lang,exist_ok=True)
    for p,s in render(lang,I18N[lang]).items():
        open(lp(lang)+p,'w',encoding='utf-8').write(s); pages.append((lang,p))
def sources(l,p):
    """Files whose last commit date becomes the page's <lastmod> (never the build date)."""
    f=['tools/gen.py',f'tools/i18n/{l}.json']
    if p=='privacy.html': f.append('privacy.html' if l=='en' else f'tools/i18n/privacy.{l}.html')
    if p=='licenses.html': f.append('licenses.html')  # en body is embedded in ru/zh licences too
    return f
def lastmod(l,p):
    d=subprocess.run(['git','log','-1','--format=%cs','--',*sources(l,p)],capture_output=True,text=True,check=True).stdout.strip()
    assert re.fullmatch(r'\d{4}-\d{2}-\d{2}',d), f'no git date for {l}/{p}'
    return d
open('sitemap.xml','w').write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
 +''.join(f'<url><loc>{url(l,p)}</loc><lastmod>{lastmod(l,p)}</lastmod>'+''.join(f'<xhtml:link rel="alternate" hreflang="{HREFLANG[x]}" href="{url(x,p)}"/>' for x in LANGS)+f'<xhtml:link rel="alternate" hreflang="x-default" href="{url("en",p)}"/></url>\n' for l,p in pages)+'</urlset>\n')
open('robots.txt','w').write(f'User-agent: *\nAllow: /\nSitemap: {BASE}sitemap.xml\n')
print(len(pages),'pages')
