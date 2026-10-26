#!/usr/bin/env python3
"""Generates all HTML pages (en at root, ru/ and zh/ copies), sitemap.xml and robots.txt. Run: python3 tools/gen.py
Translations live in tools/i18n/<lang>.json (keys ending in _html are authored markup, everything else is
plain text and HTML-escaped here) and tools/i18n/privacy.<lang>.html."""
# NOTE: only writes the pages listed below; never touches google*.html (Search Console verification file, keep, not in sitemap).
import re,os,html,json,subprocess,hashlib
os.chdir(os.path.join(os.path.dirname(__file__),'..'))
BASE='https://noclaudkit.com/image-converter/'
SITE='https://noclaudkit.com'
CSP="default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self'; img-src 'self' blob: data:; connect-src 'self'; worker-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'"
LANGS=['en','ru','zh']
HREFLANG={'en':'en','ru':'ru','zh':'zh-Hans'}
LANG_NAME={'en':'English','ru':'Русский','zh':'中文'}
OG_LOCALE={'en':'en_US','ru':'ru_RU','zh':'zh_CN'}
OG_SEP={'en':'. ','ru':'. ','zh':'。'}
def og_alt(T,lang):
    a=re.sub(r'<[^>]*>','',html.unescape(T.get('og_h1',T['index_h1']))).strip()  # plain text of the h1 drawn in the OG image (og_h1, else index_h1; U+00A0 kept)
    if a[-1:] not in '.。!?！？': a+=OG_SEP[lang].rstrip(' ')
    return a+' '*OG_SEP[lang].endswith(' ')+T['tagline']  # i18n key tagline = second line of the OG image
def og_img(lang):  # absolute, same BASE as canonical; ?v= = sha256[:8] of the PNG in repo (cache-bust, deterministic; GH Pages ignores query)
    with open(f'assets/og/og-{lang}.png','rb') as f: v=hashlib.sha256(f.read()).hexdigest()[:8]
    return BASE+f'assets/og/og-{lang}.png?v={v}'
I18N={l:json.load(open(f'tools/i18n/{l}.json',encoding='utf-8')) for l in LANGS}
for _l in LANGS: assert '\u00a0' not in I18N[_l]['tagline'] and '&nbsp;' not in I18N[_l]['tagline'], f'U+00A0 in tagline {_l}'
PAIRS=[('heic','jpg','HEIC','JPG','image/jpeg'),('heic','png','HEIC','PNG','image/png'),('webp','png','WebP','PNG','image/png'),('webp','jpg','WebP','JPG','image/jpeg'),
('avif','jpg','AVIF','JPG','image/jpeg'),('avif','png','AVIF','PNG','image/png'),('png','webp','PNG','WebP','image/webp'),('jpg','webp','JPG','WebP','image/webp')]
PAGES=['index.html']+[f'{a}-to-{b}.html' for a,b,*_ in PAIRS]+['privacy.html','licenses.html']
e=lambda s:html.escape(str(s),quote=True)
def lp(l): return '' if l=='en' else l+'/'
def url(l,p): return BASE+lp(l)+('' if p=='index.html' else p)
def href(cur,tl,p):
    h=('' if cur=='en' else '../')+lp(tl)+('' if p=='index.html' else p)
    return h or './'

def ld_dumps(d):
    return json.dumps(d,ensure_ascii=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
def jsonld(lang,page,title,desc):
    d={'@context':'https://schema.org','@type':'WebApplication','name':title,'description':desc,'url':url(lang,page),'inLanguage':HREFLANG[lang],
       'applicationCategory':'MultimediaApplication','operatingSystem':'Any','isAccessibleForFree':True,'offers':{'@type':'Offer','price':'0','priceCurrency':'USD'}}
    return f'<script type="application/ld+json">{ld_dumps(d)}</script>\n'
def home_path(l): return '/' if l=='en' else f'/{l}/'
def home_abs(l): return SITE+home_path(l)
def conv_path(l): return '/image-converter/' if l=='en' else f'/image-converter/{l}/'
def pdf_path(l): return '/pdf/' if l=='en' else f'/pdf/{l}/'
LANDING_PAGES={f'{a}-to-{b}.html' for a,b,*_ in PAIRS}
HEIC_LANDINGS={'heic-to-jpg.html','heic-to-png.html'}
def page_label(T,page):
    if page=='index.html': return T['f_conv']
    if page=='privacy.html': return T['f_priv']
    if page=='licenses.html': return T['f_lic']
    if page=='heic-to-jpg.html': return T['ft_heic']
    for a,b,A,B,_ in PAIRS:
        if page==f'{a}-to-{b}.html': return T['pair_link'].format(A=A,B=B)
    raise ValueError(page)
def crumb_items(T,lang,page):
    """(visible name, absolute canonical URL, href or None if current)."""
    items=[('NoClaudKit',home_abs(lang),home_path(lang))]
    if page=='index.html':
        items.append((T['f_conv'],url(lang,page),None)); return items
    items.append((T['f_conv'],url(lang,'index.html'),conv_path(lang)))
    items.append((page_label(T,page),url(lang,page),None))
    return items
def crumbs_html(T,lang,page):
    lis=[]
    for name,absu,href in crumb_items(T,lang,page):
        if href is None: lis.append(f'<li><span aria-current="page">{e(name)}</span></li>')
        else:
            extra=' translate="no"' if name=='NoClaudKit' else ''
            lis.append(f'<li><a href="{href}"{extra}>{e(name)}</a></li>')
    return f'<nav class="crumbs" aria-label="{e(T["crumbs_aria"])}"><ol>'+''.join(lis)+'</ol></nav>\n'
def crumbs_ld(T,lang,page):
    el=[{'@type':'ListItem','position':i+1,'name':name.replace('\u00a0',' '),'item':absu} for i,(name,absu,_) in enumerate(crumb_items(T,lang,page))]
    return f'<script type="application/ld+json">{ld_dumps({"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":el})}</script>\n'
def xpdf(T,lang,page):
    if page=='index.html': href,lab=pdf_path(lang),T['ft_pdf']
    elif page in HEIC_LANDINGS: href,lab=pdf_path(lang)+'jpg-to-pdf.html',T['xpdf_heic']
    elif page in LANDING_PAGES: href,lab=pdf_path(lang)+'jpg-to-pdf.html',T['xpdf_jpg']
    else: return ''
    return f'<p class="xpdf mt-8"><a class="link link-primary inline-flex items-center min-h-11" href="{href}">{e(lab)}</a></p>\n'
DOC_PAGES={'privacy.html','licenses.html'}
LD_PAGES={'index.html'}|{f'{a}-to-{b}.html' for a,b,*_ in PAIRS}  # JSON-LD on index and tool pages only, not privacy/licences

NB='\u00a0'
PLAIN_KEYS={'tagline','removed_zero','removed_one','removed_few','removed_many','removed_other','crumbs_aria','about_aria','results_aria'}  # tagline: OG alt plain spaces; removed_*: Nathan aria-live texts, plain spaces by design; crumbs_aria/about_aria/results_aria: aria-labels, no NBSP
RU_SHORT='не|и|с|в|на|к|о|у|а|из|за|по|от|до|я|ни|но|же|ли'
def ru_nbsp(s): return re.sub(r'(?<![\w\u0400-\u04ff])('+RU_SHORT+r') ',lambda m:m.group(1)+NB,s,flags=re.I)
def check_ru(T,path='ru'):
    """ru sources must carry real U+00A0 after short words (and never the &nbsp; entity). *_html keys are checked
    on their visible text (tags and attributes stripped, entities decoded)."""
    for k,v in (T.items() if isinstance(T,dict) else []):
        if isinstance(v,dict): check_ru(v,path+'.'+k); continue
        if not isinstance(v,str): continue
        if k in PLAIN_KEYS: assert NB not in v and '&nbsp;' not in v, f'U+00A0 in plain-space key {path}.{k}'; continue
        assert '&nbsp;' not in v, f'&nbsp; entity in {path}.{k}'
        txt=html.unescape(re.sub(r'<[^>]*>','',v)) if k.endswith('_html') else v
        assert ru_nbsp(txt)==txt, f'plain space after a short word in {path}.{k}'
ICON='<svg viewBox="0 0 28 28" aria-hidden="true" class="size-7 shrink-0 text-primary" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="1" y="1" width="26" height="26" rx="7"/><path d="M8 18l4-5 3 3 2-2 3 4"/></svg>'
GLOBE='<svg class="ico-globe size-5 shrink-0 hidden min-[360px]:block" viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>'
CHEV_S='<svg class="ico-chev hidden sm:block size-3.5 shrink-0 opacity-70" viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" stroke-width="2"><path d="m6 9 6 6 6-6"/></svg>'
CHECK='<svg class="ms-auto size-4 shrink-0" viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.5l4.5 4.5L19 7"/></svg>'
LANG_CODE={'en':'EN','ru':'RU','zh':''}  # right-hand codes of the inactive items; none for 中文 (the name is already the code; the button shows i18n lang_code: EN/RU/中文)
X_ICON='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18"/></svg>'
def head(T,lang,page,title,desc,out=None):
    P='' if lang=='en' else '../'
    ld=(jsonld(lang,page,title,desc) if page in LD_PAGES else '')+crumbs_ld(T,lang,page)
    alts=''.join(f'<link rel="alternate" hreflang="{HREFLANG[l]}" href="{url(l,page)}">' for l in LANGS)+f'<link rel="alternate" hreflang="x-default" href="{url("en",page)}">'
    ROOT=re.sub(r'^https?://[^/]+','',BASE)  # '/image-converter/': language links (inline list and dropdown) are root-relative plain <a href>, no JS
    # Selectors v2, variant B «Одно меню» (spec /workspace/design/selectors-v2/spec.md, owner-approved 2026-10-15):
    # one daisyUI <details> = language links (real <a hreflang>, no JS) + desktop-only theme radios (wired by theme.js, no theme-controller)
    def li(l):
        cur=l==lang
        tail=CHECK if cur else (f'<span class="ms-auto text-xs text-base-content/70">{LANG_CODE[l]}</span>' if LANG_CODE[l] else '')
        return (f'<li><a class="min-h-11'+(' menu-active' if cur else '')+f'" href="{ROOT}{lp(l)}{"" if page=="index.html" else page}" hreflang="{HREFLANG[l]}" lang="{HREFLANG[l]}"'
                +(' aria-current="page"' if cur else '')+f'>{e(LANG_NAME[l])}{" "+tail if tail else ""}</a></li>')
    radios=''.join(f'<input class="join-item btn btn-ghost flex-1 min-h-11 theme-opt" type="radio" name="theme" value="{v}" aria-label="{e(T[v])}" title="{e(T[v])}"'+(' checked' if v=='system' else '')+'>' for v in ('system','light','dark'))
    aria=''.join(f' data-l-{k}="{e(T["settings_aria_"+k])}"' for k in ('system','light','dark','mobile'))
    nav=(f'<details class="settings dropdown dropdown-end"><summary class="btn btn-outline border-base-300 min-h-11 min-w-11 px-2 gap-1 min-[360px]:px-2.5 min-[360px]:gap-1.5 font-medium whitespace-nowrap" aria-label="{e(T["settings_aria_system"])}" aria-haspopup="true" aria-expanded="false"{aria}>'
         f'{GLOBE}<span lang="{HREFLANG[lang]}">{e(T["lang_code"])}</span><span class="sep hidden sm:block w-px h-6 bg-base-300 mx-1" aria-hidden="true"></span><span class="ico-theme hidden sm:block size-5" aria-hidden="true"></span>{CHEV_S}</summary>'
         '<div class="dropdown-content z-20 mt-2 w-56 rounded-box border border-base-300 bg-base-100 p-2 shadow-lg">'
         f'<nav aria-labelledby="lang-h"><p id="lang-h" class="px-3 pt-2 pb-1 text-xs font-medium text-base-content/80">{e(T["lang_nav"])}</p><ul class="menu w-full p-0">'+''.join(li(l) for l in LANGS)+'</ul></nav>'
         f'<div class="theme-sec hidden sm:block"><hr class="my-1.5 mx-1 border-base-300"><fieldset><legend id="theme-h" class="px-3 pt-2 pb-1 text-xs font-medium text-base-content/80">{e(T["theme"])}</legend>'
         f'<div class="join flex w-full p-0.5 border border-base-300 rounded-field" role="radiogroup" aria-labelledby="theme-h">{radios}</div></fieldset></div></div></details>')
    attrs=(f' data-out="{e(out)}"' if out else '')+(f' data-i18n="{e(json.dumps(T["js"],ensure_ascii=False).replace(NB,chr(92)+"u00a0"))}"' if T.get('js') and page in LD_PAGES else '')
    mt=(f'<div class="mt-note bg-base-200 text-sm" role="note"><div class="mx-auto max-w-4xl px-4 sm:px-6 flex flex-wrap items-center gap-x-2"><span>{T["mt_notice_html"]}</span> <a class="link link-primary min-h-11 inline-flex items-center" href="{href(lang,"en",page)}" lang="en" hreflang="en">{e(T["read_en"])}</a></div></div>') if T.get('mt_notice_html') else ''
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
{ld}<script src="{P}theme.js"></script><link rel="icon" href="{P}favicon.svg"><link rel="stylesheet" href="{P}build/app.css"></head><body class="min-h-screen flex flex-col bg-base-100 text-base-content antialiased{' doc' if page in DOC_PAGES else ''}"{attrs}>
{mt}<header class="top bg-base-100 border-b border-base-300"><div class="navbar mx-auto max-w-4xl px-3 min-[360px]:px-4 sm:px-6 gap-3 min-h-16">
<div class="navbar-start min-w-0 w-auto grow"><a class="brand flex items-center gap-2 min-h-11 font-semibold text-sm sm:text-lg whitespace-nowrap" href="./" translate="no">{ICON}<span>Local{NB}Image{NB}Converter</span></a></div>
<div class="navbar-end w-auto">{nav}</div></div></header>
<main class="mx-auto w-full max-w-4xl px-4 sm:px-6 py-8 sm:py-12 grow">
{crumbs_html(T,lang,page)}'''
def hero(h1,lede,T,pnote=''):
    return (f'<section class="intro"><h1 class="text-3xl sm:text-5xl font-bold tracking-tight text-balance max-w-3xl">{e(h1)}</h1><p class="lede hidden sm:block mt-4 text-lg text-base-content/80 max-w-2xl text-pretty">{e(lede)}</p><p class="lede-m sm:hidden mt-3 text-base-content/80">{e(T["lede_m"])}</p>'
            +(f'<p class="pnote hidden sm:flex alert alert-outline mt-4 text-sm">{e(pnote)}</p>' if pnote else '')+'</section>\n')
def tool(T,P,heic=True):
    return f'''<label class="drop mt-6 flex flex-col items-center gap-2 rounded-box border-2 border-dashed border-base-content/60 bg-base-200 px-4 py-8 sm:py-12 text-center cursor-pointer hover:border-primary has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-primary" for="files" id="drop"><input class="sr-only" id="files" name="files" type="file" multiple accept="image/*,.heic,.heif,.avif,.webp"><ul class="pills flex flex-wrap justify-center gap-2 mb-1" aria-hidden="true"><li class="badge badge-outline">HEIC</li><li class="badge badge-outline">WebP</li><li class="badge badge-outline">AVIF</li><li class="badge badge-outline">PNG</li><li class="badge badge-outline">JPEG</li></ul><span class="dt text-lg font-semibold text-balance">{e(T['drop'])}</span><span class="ds hidden sm:block text-sm text-base-content/80">{e(T['drop_sub'])}</span>{f'<span class="hn hidden sm:block text-sm text-base-content/80 max-w-xl text-pretty">{e(T["heic_note"])}</span>' if heic else ''}</label>
<section class="controls card card-border bg-base-100 mt-4 p-4 sm:p-6" aria-label="{e(T['converter_label'])}"><div class="fields grid gap-4 sm:grid-cols-2"><div class="field flex flex-col gap-2"><label for="fmt" class="text-sm font-medium">{e(T['out_fmt'])}</label><select id="fmt" name="format" class="select w-full min-h-11"><option value="image/jpeg">JPEG</option><option value="image/png">PNG</option></select></div>
<div class="field flex flex-col gap-2"><label for="q" class="text-sm font-medium">{e(T['quality_label'])}</label><div class="qrow flex items-center gap-3 min-h-11"><input class="grow h-11 accent-primary cursor-pointer" id="q" name="quality" type="range" min="0.5" max="1" step="0.05" value="0.85"><output id="qv" for="q" class="qv font-medium tabular-nums w-10 text-end">{e(T['q_default'])}</output></div></div></div>
<div class="bar mt-4"><div class="actions flex flex-col-reverse sm:flex-row gap-2 sm:justify-end"><button id="clear" type="button" class="btn sec btn-outline min-h-11" disabled>{e(T['clear'])}</button><button id="zip" type="button" class="btn sec btn-outline min-h-11" disabled>{e(T['zip'])}</button><button id="convert" type="button" class="btn pri btn-primary min-h-11 px-6" disabled>{e(T['js']['convert0'])}</button></div></div>
<noscript><p>{e(T['noscript'])}</p></noscript></section>
<section class="results mt-4" aria-label="{e(T['results_aria'])}"><p role="status" id="lh" class="lh text-center text-sm font-normal text-base-content/80 py-3" aria-live="polite">{e(T['js']['empty'])}</p><ul id="list" class="flex flex-col gap-2"></ul></section>
<script src="{P}config.js"></script><script src="{P}zip.js"></script><script src="{P}app.js"></script>
'''
def limits(T,extra=''):
    return f'<details class="lim hidden sm:block collapse collapse-arrow bg-base-200 mt-4"><summary class="collapse-title font-semibold min-h-11">{e(T["lim"])}</summary><div class="collapse-content text-sm space-y-2"><p>{e(T["lim_p"])}</p>'+(f'<p>{e(extra)}</p>' if extra else '')+'</div></details>\n'
def more(T,lede,pnote='',extra='',heic=True):
    ps=[lede]+([pnote] if pnote else [])+([T['heic_note']] if heic else [])+[T['lim_p']]+([extra] if extra else [])
    return f'<details class="more sm:hidden collapse collapse-arrow bg-base-200 mt-4"><summary class="collapse-title font-semibold min-h-11">{e(T["more"])}</summary><div class="collapse-content text-sm space-y-2">'+''.join(f'<p>{e(x)}</p>' for x in ps)+'</div></details>\n'
def safari(T): return '<p class="note">'+T['safari_html']+'</p>'
def pairlinks(T,page=''):  # «Лагуна»: pair links as daisyUI buttons; the current tool page is btn-primary + aria-current
    def li(a,b,A,B):
        cur=page==f'{a}-to-{b}.html'
        return f'<li><a class="btn {"btn-primary" if cur else "btn-outline"} min-h-11 w-full justify-start font-medium" href="{a}-to-{b}.html"'+(' aria-current="page"' if cur else '')+f'>{e(T["pair_link"].format(A=A,B=B))}</a></li>'
    return '<section class="pop mt-12" aria-labelledby="pp"><h2 id="pp" class="text-2xl font-semibold">'+e(T['popular'])+'</h2><ul class="pairs grid grid-cols-2 sm:grid-cols-4 gap-2 mt-4">'+''.join(li(a,b,A,B) for a,b,A,B,_ in PAIRS)+'</ul></section>'
def foot(T,lang,page):
    cur=conv_path(lang) if page=='index.html' else conv_path(lang)+page
    tools=[
        (home_path(lang),'NoClaudKit',True),
        (conv_path(lang),T['f_conv'],False),
        (pdf_path(lang),T['ft_pdf'],False),
        (conv_path(lang)+'heic-to-jpg.html',T['ft_heic'],False),
        (pdf_path(lang)+'merge-pdf.html',T['ft_merge'],False),
        (pdf_path(lang)+'split-pdf.html',T['ft_split'],False),
        (pdf_path(lang)+'jpg-to-pdf.html',T['ft_jpgpdf'],False),
    ]
    def tool_a(h,t,tno):
        extra=(' translate="no"' if tno else '')+(' aria-current="page"' if h==cur else '')
        return f'<li><a href="{h}"{extra}>{e(t)}</a></li>'
    about=[('privacy.html',T['f_priv']),('licenses.html',T['f_lic']),('https://github.com/swtormy-agents/image-converter','GitHub')]
    return (f'</main>\n<footer class="bg-base-200 mt-8"><div class="mx-auto max-w-4xl px-4 sm:px-6 py-6 text-base-content">'
            f'<nav class="ft" aria-labelledby="ft-h"><h2 id="ft-h" class="text-sm font-medium text-base-content/80">{e(T["ft_all"])}</h2>'
            f'<ul>'+''.join(tool_a(*x) for x in tools)+'</ul></nav>'
            f'<div class="footer sm:footer-horizontal mt-6"><p class="max-w-xl text-sm"><span class="foot-x hidden sm:inline">{e(T["foot"])} </span>{e(T["legal"])}</p>'
            f'<nav aria-label="{e(T["about_aria"])}"><ul class="flinks flex flex-wrap gap-x-4">'
            +''.join(f'<li><a class="link link-hover min-h-11 min-w-11 inline-flex items-center justify-center" href="{h}">{e(t)}</a></li>' for h,t in about)
            +'</ul></nav></div></div></footer></body></html>\n')
def rebase(body):  # make relative links in English bodies work from /ru/ and /zh/
    return re.sub(r'href="(?!https?:|#|\.\./|mailto:)([^"]+)"',r'href="../\1"',body)

# English privacy/licences bodies are maintained in the root HTML files (read before rewriting).
EN_BODY={}
for f in ('privacy.html','licenses.html'):
    s=open(f,encoding='utf-8').read(); body=re.search(r'<main[^>]*>\n(.*?)</main>',s,re.S).group(1)
    body=re.sub(r'<nav class="crumbs"[^>]*>.*?</nav>\n','',body)
    body=re.sub(r'<p class="note"><b>Browser testing:</b>.*?</p>\n','',body); body=re.sub(r'<section class="(?:pairs|pop)[^"]*".*?</section>\n','',body)
    body=re.sub(r'<p class="xpdf[^"]*"[^>]*>.*?</p>\n','',body)
    EN_BODY[f]=body

def render(lang,T):
    P='' if lang=='en' else '../'; out={}
    out['index.html']=(head(T,lang,'index.html',T['index_title'],T['index_desc'])
     +hero(T['index_h1'],T['index_lead'],T)+tool(T,P)+limits(T)+more(T,T['index_lead'])+pairlinks(T)+xpdf(T,lang,'index.html')+'\n'+foot(T,lang,'index.html'))
    for a,b,A,B,mime in PAIRS:
        p=f'{a}-to-{b}.html'; lead=T['pair_lead'].format(A=A,B=B); dec=T['notes'][a] if a in('heic','avif') else ''  # decoder/browser-support note (Limitations + mobile «Подробнее»)
        pm=T.get('pair_meta',{}).get(p,{})  # approved per-page overrides
        out[p]=(head(T,lang,p,pm.get('title',T['pair_title'].format(A=A,B=B)),pm.get('desc',T['pair_desc'].format(A=A,B=B)),mime)
         +hero(T['pair_h1'].format(A=A,B=B),lead,T,T['outn'][b])+tool(T,P,a=='heic')+limits(T,dec)+more(T,lead,T['outn'][b],dec,a=='heic')+pairlinks(T,p)+xpdf(T,lang,p)+'\n'+foot(T,lang,p))
    if lang=='en': pb,lb=EN_BODY['privacy.html'],EN_BODY['licenses.html']
    else:
        pb='<p class="note prevails">'+T['prevails_html']+'</p>\n'+open(f'tools/i18n/privacy.{lang}.html',encoding='utf-8').read()
        lb='<p class="note prevails">'+T['licenses_note_html']+'</p>\n<div lang="en">\n'+rebase(EN_BODY['licenses.html'])+'</div>\n'
    out['privacy.html']=head(T,lang,'privacy.html',T['privacy_title'],T['privacy_desc'])+pb+safari(T)+'\n'+pairlinks(T)+'\n'+foot(T,lang,'privacy.html')
    out['licenses.html']=head(T,lang,'licenses.html',T['licenses_title'],T['licenses_desc'])+lb+safari(T)+'\n'+pairlinks(T)+'\n'+foot(T,lang,'licenses.html')
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
            data=json.loads(m)
            if data.get('@type')=='BreadcrumbList':
                for it in data['itemListElement']:
                    if it['name']=='NoClaudKit': continue
                    assert bad in it['name'], f'JSON-LD crumb name mismatch in {p}'
            else:
                assert data['name'].endswith(bad), f'JSON-LD name mismatch in {p}'
selftest()
check_ru(I18N["ru"])
_pv=re.sub(r'<code>.*?</code>|<[^>]+>',' ',open('tools/i18n/privacy.ru.html',encoding='utf-8').read(),flags=re.S)  # visible text only
assert '&nbsp;' not in _pv and ru_nbsp(_pv)==_pv and ' —' not in _pv, 'privacy.ru.html: plain space after a short word or before an em dash'

for _l in LANGS:
    assert os.path.isfile(f'assets/og/og-{_l}.png'), f'missing og image for {_l}'
    _a=og_alt(I18N[_l],_l); assert '..' not in _a and '。。' not in _a and '.。' not in _a, f'double punctuation in og alt {_l}'

def plain_meta(s):
    """U+00A0 only in visible text: plain spaces inside tags/attributes, <title> and JSON-LD."""
    s=re.sub(r'<[^>]*>',lambda m:m.group(0).replace(NB,' '),s)
    s=re.sub(r'(<title>|<script type="application/ld\+json">)(.*?)(</title>|</script>)',lambda m:m.group(1)+m.group(2).replace(NB,' ')+m.group(3),s,flags=re.S)
    for m in re.finditer(r'<[^>]*>|<title>.*?</title>|<script type="application/ld\+json">.*?</script>',s,re.S): assert NB not in m.group(0), 'U+00A0 in markup/meta'
    return s
pages=[]
for lang in LANGS:
    if lang!='en': os.makedirs(lang,exist_ok=True)
    for p,s in render(lang,I18N[lang]).items():
        s=plain_meta(s)
        open(lp(lang)+p,'w',encoding='utf-8').write(s); pages.append((lang,p))
def sources(l,p):
    """Content files whose last commit date becomes the page's <lastmod> (never the build date).
    tools/gen.py is deliberately not a source: template/generator edits must not bump every page's lastmod."""
    f=[f'tools/i18n/{l}.json']
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
