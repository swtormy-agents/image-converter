(function(){
'use strict';
const cfg=window.LIC_CONFIG||{HEIC_WASM_ENABLED:false};
// Asset base = directory of this script, so /ru/ and /zh/ pages load vendor files from the site root.
const BASE=(document.currentScript&&document.currentScript.src)?new URL('.',document.currentScript.src).href:'';
// Per-page UI strings: JSON in <body data-i18n> (generated + HTML-escaped by tools/gen.py). English defaults below.
let I={};try{I=JSON.parse(document.body.dataset.i18n||'{}')||{};}catch(e){I={};}
const PR=(window.Intl&&Intl.PluralRules)?new Intl.PluralRules(document.documentElement.lang||'en'):null;
function t(k,d,v){let s=typeof I[k]==='string'?I[k]:d;if(v)for(const n in v)s=s.split('{'+n+'}').join(v[n]);return s;}
function tp(k,n,d1,dn){const c=PR?PR.select(n):(n===1?'one':'other');const s=I[k+'_'+c]||I[k+'_other'];return s?s.split('{n}').join(n):(n===1?d1:dn).split('{n}').join(n);}
const $=id=>document.getElementById(id);
const clearBtn=$('clear'),fmtSel=$('fmt'),q=$('q'),qv=$('qv'),list=$('list'),status=$('lh'),btn=$('convert'),zipBtn=$('zip');
let items=[],busy=false;
const OUT=[['image/jpeg','JPEG','jpg'],['image/png','PNG','png'],['image/webp','WebP','webp'],['image/avif','AVIF','avif']];
const NS='http://www.w3.org/2000/svg';

function canEncode(type){return new Promise(r=>{const c=document.createElement('canvas');c.width=c.height=2;c.toBlob(b=>r(!!b&&b.type===type),type,0.8);});}
// JPEG and PNG options are in the static HTML; WebP/AVIF are added only where this browser can encode them.
(async()=>{for(const [t,l] of OUT){if(t==='image/jpeg'||t==='image/png')continue;if(await canEncode(t)){const o=document.createElement('option');o.value=t;o.textContent=l;fmtSel.appendChild(o);}}const pre=document.body.dataset.out;if(pre&&[...fmtSel.options].some(o=>o.value===pre))fmtSel.value=pre;syncFmt();})();
function fmtQ(v){return Number(v).toFixed(2).replace('.',t('dec','.'));}
function syncQ(){qv.textContent=fmtQ(q.value);q.setAttribute('aria-valuetext',fmtQ(q.value));}
function syncFmt(){q.disabled=fmtSel.value==='image/png';}
function stale(){if(!busy&&items.length)btn.disabled=false;}
q.addEventListener('input',()=>{syncQ();stale();});fmtSel.addEventListener('change',()=>{syncFmt();stale();});syncQ();
function syncUI(){const n=items.length,ok=items.filter(x=>x.out).length;
  btn.textContent=n?tp('convert',n,'Convert {n} file','Convert {n} files'):t('convert0','Convert');
  clearBtn.disabled=busy||!n;zipBtn.disabled=busy||ok<2;if(!n){btn.disabled=true;status.textContent=t('empty','Add images to start');}}
function isHeif(f){return /\.(heic|heif)$/i.test(f.name)||/image\/hei[cf]/i.test(f.type);}

async function nativeDecode(file){
  if(window.createImageBitmap){try{return await createImageBitmap(file);}catch(e){}}
  return new Promise((res,rej)=>{const u=URL.createObjectURL(file),i=new Image();i.onload=()=>{res(i);};i.onerror=()=>{URL.revokeObjectURL(u);rej(new Error('native decode failed'));};i.src=u;});
}

// Lazily loaded, separate LGPL module (same origin). Kill-switch: config.js HEIC_WASM_ENABLED=false.
let heifP=null;
function loadHeif(){
  if(!cfg.HEIC_WASM_ENABLED){const e=new Error('disabled');e.friendly=t('heicOff','HEIC/HEIF decoding is not available in this browser on this site right now.');return Promise.reject(e);}
  if(!heifP)heifP=new Promise((res,rej)=>{
    const s=document.createElement('script');const hp=new URL(cfg.HEIC_WASM_PATH,BASE||document.baseURI).href;s.src=hp+'libheif.js';
    s.onload=()=>{fetch(hp+'libheif.wasm').then(r=>{if(!r.ok)throw new Error('could not load HEIC decoder');return r.arrayBuffer();}).then(b=>window.libheif({wasmBinary:b})).then(res,rej);};
    s.onerror=()=>rej(new Error('could not load HEIC decoder'));document.head.appendChild(s);
  }).catch(e=>{heifP=null;throw e;});
  return heifP;
}
async function heifDecode(file){
  const lib=await loadHeif();
  const dec=new lib.HeifDecoder();const imgs=dec.decode(new Uint8Array(await file.arrayBuffer()));
  if(!imgs||!imgs.length)throw new Error('no image found in HEIF file');
  const im=imgs[0],w=im.get_width(),h=im.get_height();
  const c=document.createElement('canvas');c.width=w;c.height=h;const ctx=c.getContext('2d');
  const id=ctx.createImageData(w,h);
  await new Promise((r,j)=>im.display(id,d=>d?r():j(new Error('HEIF decode failed'))));
  ctx.putImageData(id,0,0);
  for(const x of imgs){try{x.free&&x.free();}catch(e){}}
  return c;
}
async function decode(file){
  try{return await nativeDecode(file);}catch(e){ if(isHeif(file))return heifDecode(file); throw new Error('unsupported or damaged image'); }
}
async function convert(it,type,quality){
  const src=await decode(it.file);
  const w=src.naturalWidth||src.width,h=src.naturalHeight||src.height;
  const c=document.createElement('canvas');c.width=w;c.height=h;const ctx=c.getContext('2d');
  if(type==='image/jpeg'){ctx.fillStyle='#fff';ctx.fillRect(0,0,w,h);}
  ctx.drawImage(src,0,0);if(src.close)src.close();if(src.src&&src.src.startsWith('blob:'))URL.revokeObjectURL(src.src);
  const blob=await new Promise(r=>c.toBlob(r,type,quality));
  if(!blob||blob.type!==type){const e=new Error('encode');e.friendly=t('encodeFail','Your browser cannot create this output format. Try JPEG or PNG.');throw e;}
  return blob;
}
function kb(n){return n<1024*1024?Math.max(1,Math.round(n/1024))+'\u00a0'+t('kb','KB'):(n/1048576).toFixed(1)+'\u00a0'+t('mb','MB');}
function svgX(){const s=document.createElementNS(NS,'svg');s.setAttribute('viewBox','0 0 24 24');s.setAttribute('aria-hidden','true');const p=document.createElementNS(NS,'path');p.setAttribute('d','M6 6l12 12M18 6 6 18');s.appendChild(p);return s;}
function el(tag,cls,txt){const e=document.createElement(tag);if(cls)e.className=cls;if(txt!=null)e.textContent=txt;return e;}
function fmtExt(){return OUT.find(o=>o[0]===fmtSel.value)[2].toUpperCase();}
function srcExt(f){const m=f.name.match(/\.([^.]+)$/);return m?m[1].toUpperCase().replace('JPEG','JPG'):'?';}
function setPill(it){it.pill.textContent=srcExt(it.file)+' \u2192 '+fmtExt();}
// ---- File-list thumbnails (Olivia spec 2026-10-15): local blob: only, sequential, lazy, downscaled, never full-size in DOM.
// Icon paths from lagoon/previews.py (IMG, FILE); '_' = space inside an attribute value.
const IMG_D=[['rect','x=3 y=4 width=18 height=16 rx=2'],['circle','cx=9 cy=10 r=1.6'],['path','d=M4_18l5-5_4_4_2-2_5_4']];
const FILE_D=[['path','d=M6_3h8l4_4v14H6z'],['path','d=M14_3v4h4'],['path','d=M9_13l6_6M15_13l-6_6']];
function icon(parts){const s=document.createElementNS(NS,'svg');s.setAttribute('viewBox','0 0 24 24');s.setAttribute('focusable','false');s.setAttribute('aria-hidden','true');
  for(const [tg,a] of parts){const n=document.createElementNS(NS,tg);for(const kv of a.split(' ')){const i=kv.indexOf('=');n.setAttribute(kv.slice(0,i),kv.slice(i+1).replace(/_/g,' '));}s.appendChild(n);}return s;}
const MAX_PX=50e6,mqD=window.matchMedia?matchMedia('(min-width:600px)'):null;
function thSize(){return ((mqD&&mqD.matches)?96:64)*Math.min(Math.max(window.devicePixelRatio||1,1),2);}
function hasAlpha(f){return /\.(png|webp|avif|gif)$/i.test(f.name)||/image\/(png|webp|avif|gif)/i.test(f.type);}
function thLoading(it){const d=el('div','th skeleton');d.setAttribute('aria-hidden','true');d.appendChild(icon(IMG_D));it.th.replaceWith(d);it.th=d;}
function thError(it){const d=el('div','th is-error');d.setAttribute('aria-hidden','true');d.append(icon(FILE_D),el('span','th-x',srcExt(it.file)));it.th.replaceWith(d);it.th=d;
  it.noPv=true;setRs(it,[...it.rs.childNodes].filter(n=>!n.classList||!n.classList.contains('npv')));}
// Error status: no "No preview ·" prefix (the error already explains it); li.is-err lets the status take the full row width <600px.
function setRs(it,nodes){const er=nodes.some(n=>n.classList&&n.classList.contains('err'));it.rs.textContent='';it.li.classList.toggle('is-err',er);
  if(it.noPv&&!er)it.rs.append(el('span','muted npv',t('noPreview','No preview')+' \u00b7 '));it.rs.append(...nodes);}
// Read pixel size from the file header without decoding (review note 10 / card «лимит 50 МП»).
// JPEG SOFn, PNG IHDR, GIF LSD, BMP, WebP VP8/VP8L/VP8X, ISOBMFF (AVIF/HEIC) ispe. Unknown/garbled -> null (caller falls back to decode).
async function headerDims(f){try{const b=new DataView(await f.slice(0,Math.min(f.size,1<<20)).arrayBuffer()),L=b.byteLength,u8=i=>b.getUint8(i),
  u16=(i,le)=>b.getUint16(i,le),u32=(i,le)=>b.getUint32(i,le),s4=i=>String.fromCharCode(u8(i),u8(i+1),u8(i+2),u8(i+3)),ok=(w,h)=>w>0&&h>0?{w,h}:null;
  if(L<12)return null;
  if(u16(0)===0xFFD8){let i=2;while(i+9<L){if(u8(i)!==0xFF){i++;continue;}const m=u8(i+1);if(m===0xFF){i++;continue;}if(m===0xD8||m===0x01||(m>=0xD0&&m<=0xD7)){i+=2;continue;}
      const len=u16(i+2);if((m>=0xC0&&m<=0xCF)&&m!==0xC4&&m!==0xC8&&m!==0xCC)return ok(u16(i+7),u16(i+5));if(m===0xDA||len<2)return null;i+=2+len;}return null;}
  if(u32(0)===0x89504E47&&L>=24&&s4(12)==='IHDR')return ok(u32(16),u32(20));
  if(s4(0)==='GIF8')return ok(u16(6,true),u16(8,true));
  if(u8(0)===0x42&&u8(1)===0x4D&&L>=26){const hs=u32(14,true);if(hs===12)return ok(u16(18,true),u16(20,true));return ok(Math.abs(b.getInt32(18,true)),Math.abs(b.getInt32(22,true)));}
  if(s4(0)==='RIFF'&&s4(8)==='WEBP'&&L>=30){const c=s4(12);
    if(c==='VP8X')return ok(1+(u8(24)|u8(25)<<8|u8(26)<<16),1+(u8(27)|u8(28)<<8|u8(29)<<16));
    if(c==='VP8L'&&u8(20)===0x2F){const v=u32(21,true);return ok(1+(v&0x3FFF),1+((v>>>14)&0x3FFF));}
    if(c==='VP8 '&&u8(23)===0x9D&&u8(24)===0x01&&u8(25)===0x2A)return ok(u16(26,true)&0x3FFF,u16(28,true)&0x3FFF);return null;}
  if(s4(4)==='ftyp'){let best=null;const walk=(a,e)=>{while(a+8<=e){let sz=u32(a);const ty=s4(a+4);let h=8;if(sz===1){if(a+16>L)return;sz=u32(a+12);h=16;}else if(sz===0)sz=e-a;if(sz<h)return;
      const end=Math.min(a+sz,e);if(ty==='meta')walk(a+h+4,end);else if(ty==='iprp'||ty==='ipco')walk(a+h,end);
      else if(ty==='ispe'&&a+20<=L){const w=u32(a+12),hh=u32(a+16);if(w&&hh&&(!best||w*hh>best.w*best.h))best={w,h:hh};}a+=sz;}};walk(0,L);return best;}
  return null;}catch(e){return null;}}
async function makeThumb(it){
  const hd=await headerDims(it.file);if(hd&&hd.w*hd.h>MAX_PX)throw new Error('too large');  // skip the full decode for >50 MP
  const src=await decode(it.file);  // same path as conversion: native, then the existing lazy HEIC decoder (respects HEIC_WASM_ENABLED)
  try{const w=src.naturalWidth||src.width,h=src.naturalHeight||src.height;if(!w||!h||w*h>MAX_PX)throw new Error('too large');
    const k=Math.min(1,thSize()/Math.max(w,h)),c=document.createElement('canvas');c.width=Math.max(1,Math.round(w*k));c.height=Math.max(1,Math.round(h*k));
    const ctx=c.getContext('2d');ctx.imageSmoothingQuality='high';ctx.drawImage(src,0,0,c.width,c.height);
    const a=hasAlpha(it.file),b=await new Promise(r=>c.toBlob(r,a?'image/png':'image/jpeg',0.8));c.width=c.height=0;
    if(!b)throw new Error('thumb encode');return {b,a};
  }finally{if(src.close)src.close();if(src.src&&src.src.startsWith('blob:'))URL.revokeObjectURL(src.src);if(src.width&&src.getContext)src.width=src.height=0;}
}
const thQ=[];let thRun=false;
async function pump(){if(thRun)return;thRun=true;
  while(thQ.length){const it=thQ.shift();if(!items.includes(it))continue;
    try{const r=await makeThumb(it);if(!items.includes(it))continue;
      const u=URL.createObjectURL(r.b),d=el('div','th'+(r.a?' th-alpha':'')),im=document.createElement('img');
      im.alt='';im.width=96;im.height=96;im.decoding='async';im.src=u;d.appendChild(im);it.th.replaceWith(d);it.th=d;it.thUrl=u;
    }catch(e){if(items.includes(it))thError(it);}}
  thRun=false;}
const io=window.IntersectionObserver?new IntersectionObserver(es=>{for(const x of es)if(x.isIntersecting){io.unobserve(x.target);const it=items.find(i=>i.li===x.target);if(it){thQ.push(it);pump();}}},{rootMargin:'300px 0px'}):null;
function queueThumb(it){if(io)io.observe(it.li);else{thQ.push(it);pump();}}
function dropItem(it){if(io)io.unobserve(it.li);if(it.url)URL.revokeObjectURL(it.url);if(it.thUrl){URL.revokeObjectURL(it.thUrl);it.thUrl=null;}}
function splitName(n){const i=n.lastIndexOf('.'),f=el('span','fn');f.append(el('span','fn-b',i>0?n.slice(0,i):n),el('span','fn-e',i>0?n.slice(i):''));return f;}
// Remove one row. Focus (WCAG 2.4.3): next row's Remove, else previous row's, else the file picker inside the drop zone.
// Programmatic focus keeps :focus-visible heuristics, so the ring shows only after a keyboard-initiated removal.
// Status: removal message via removed_zero (n==0) or Intl.PluralRules removed_* otherwise.
function remove(it){if(busy)return;const i=items.indexOf(it);if(i<0)return;const nx=items[i+1]||items[i-1]||null,name=it.file.name;
  dropItem(it);it.li.remove();items.splice(i,1);syncUI();
  if(nx)nx.rm.focus();else $('files').focus();
  const n=items.length;
  status.textContent=(n===0?t('removed_zero','Removed {name}. The list is empty',{name}):tp('removed',n,'Removed {name}. {n} file in the list','Removed {name}. {n} files in the list').split('{name}').join(name));}
function add(files){
  for(const f of files){const li=el('li','row'),meta=el('div','meta'),sub=el('span','sub'),rs=el('span','rs');
    meta.append(splitName(f.name));sub.append(el('span',null,kb(f.size)));const pill=el('span','pill');sub.append(pill);meta.append(sub,rs);
    
    const rm=el('button','rm');rm.type='button';rm.setAttribute('aria-label',t('removeName','Remove {name}',{name:f.name}));rm.appendChild(svgX());
    const th=el('div','th');li.setAttribute('translate','no');li.append(th,meta,rm);
    const it={file:f,li,rs,rm,pill,th,out:null,a:null,thUrl:null,noPv:false};setPill(it);thLoading(it);setRs(it,[el('span','muted',t('ready','Ready'))]);
    rm.addEventListener('click',()=>remove(it));
    list.appendChild(li);items.push(it);queueThumb(it);}
  if(items.length){status.textContent=tp('added',items.length,'{n} file added','{n} files added');btn.disabled=false;}
  syncUI();
}
fmtSel.addEventListener('change',()=>items.forEach(it=>{if(!it.out)setPill(it);}));
clearBtn.addEventListener('click',()=>{items.forEach(dropItem);items=[];thQ.length=0;list.textContent='';syncUI();});
$('files').addEventListener('change',e=>{add(e.target.files);e.target.value='';});
const drop=$('drop');
['dragenter','dragover'].forEach(t=>drop.addEventListener(t,e=>{e.preventDefault();drop.classList.add('over');}));
['dragleave','drop'].forEach(t=>drop.addEventListener(t,e=>{e.preventDefault();drop.classList.remove('over');}));
drop.addEventListener('drop',e=>add(e.dataTransfer.files));
btn.addEventListener('click',async()=>{
  if(!items.length)return;busy=true;btn.disabled=true;syncUI();const type=fmtSel.value,ext=OUT.find(o=>o[0]===type)[2],qual=Number(q.value);let ok=0;
  for(let i=0;i<items.length;i++){const it=items[i],rs=it.rs;status.textContent=t('progress','Converting {i} of {n}…',{i:i+1,n:items.length});setRs(it,[el('span','muted',t('working','Converting…'))]);
    if(it.a){it.a.remove();it.a=null;}it.out=null;setPill(it);
    try{const b=await convert(it,type,qual);const name=it.file.name.replace(/\.[^.]+$/,'')+'.'+ext;it.out={name,blob:b};
      if(it.url)URL.revokeObjectURL(it.url);it.url=URL.createObjectURL(b);
      setRs(it,[el('span','ok',t('done','Done')+' \u00b7 '+kb(b.size)+(isHeif(it.file)?' \u00b7 '+t('firstOnly','first image only'):''))]);
      const a=el('a','btn sec sm',t('dl','Download'));a.href=it.url;a.download=name;a.setAttribute('aria-label',t('dlName','Download {name}',{name}));it.li.insertBefore(a,it.rm);it.a=a;ok++;
    }catch(e){it.out=null;setRs(it,[el('span','err',e.friendly||t('readErr',"Couldn't read this file. Is it a supported image (HEIC, HEIF, WebP, AVIF, PNG, JPEG)?"))]);}
  }
  busy=false;status.textContent=t('converted','{ok} of {n} converted',{ok,n:items.length});btn.disabled=true;syncUI();
});
zipBtn.addEventListener('click',async()=>{const fs=items.filter(i=>i.out).map(i=>({name:i.out.name,blob:i.out.blob}));const seen={};fs.forEach(f=>{let n=f.name,k=1;while(seen[n])n=f.name.replace(/(\.[^.]+)$/,'-'+(k++)+'$1');seen[n]=1;f.name=n;});
  const z=await makeZip(fs);const a=document.createElement('a');a.href=URL.createObjectURL(z);a.download='converted-images.zip';document.body.appendChild(a);a.click();a.remove();});
syncUI();
})();
