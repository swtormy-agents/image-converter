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
const prog=$('prog'),clearBtn=$('clear'),fmtSel=$('fmt'),q=$('q'),qv=$('qv'),list=$('list'),status=$('status'),btn=$('convert'),zipBtn=$('zip');
let items=[];
const OUT=[['image/jpeg','JPEG','jpg'],['image/png','PNG','png'],['image/webp','WebP','webp'],['image/avif','AVIF','avif']];

function canEncode(type){return new Promise(r=>{const c=document.createElement('canvas');c.width=c.height=2;c.toBlob(b=>r(!!b&&b.type===type),type,0.8);});}
(async()=>{for(const [t,l] of OUT){if(t==='image/jpeg'||t==='image/png'||await canEncode(t)){const o=document.createElement('option');o.value=t;o.textContent=l;fmtSel.appendChild(o);}}const pre=document.body.dataset.out;if(pre&&[...fmtSel.options].some(o=>o.value===pre))fmtSel.value=pre;syncFmt();})();
const qHint=$('q-hint'),aHint=$('action-hint');
function syncQ(){qv.textContent=q.value+'%';q.setAttribute('aria-valuetext',q.value+'%');}
function syncFmt(){const lossless=fmtSel.value==='image/png';q.disabled=lossless;qHint.textContent=lossless?t('qPng','PNG is lossless, quality does not apply.'):t('qHint','Applies to JPEG and WebP (and AVIF where available).');}
q.addEventListener('input',syncQ);fmtSel.addEventListener('change',syncFmt);
function syncHint(ok){aHint.textContent=!items.length?t('hintEmpty','Add images to enable Convert. ZIP download is available for 2 or more converted files.'):(ok===undefined?t('hintPress','Press Convert to process the list.'):(ok>=2?t('hintDone','All done. Download files one by one or as a ZIP.'):t('hintZip','ZIP download is available for 2 or more converted files.')));}

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
function kb(n){return n<1024*1024?Math.max(1,Math.round(n/1024))+' '+t('kb','KB'):(n/1048576).toFixed(1)+' '+t('mb','MB');}
function add(files){
  for(const f of files){const li=document.createElement('li');li.className='file';
    li.innerHTML='<span class="file-name"></span><span class="file-meta"></span><span class="s file-status"></span><button class="rm" type="button">&times;</button>';li.querySelector('.s').textContent=t('ready','Ready');
    li.querySelector('.file-name').textContent=f.name;li.querySelector('.file-meta').textContent=kb(f.size);if(isHeif(f)){const st=li.querySelector('.file-status');st.textContent=t('readyHeic','Ready · HEIC: first image only');}li.title=f.name;
    const it={file:f,li,out:null};li.querySelector('.rm').addEventListener('click',()=>{if(it.url)URL.revokeObjectURL(it.url);li.remove();items=items.filter(x=>x!==it);btn.disabled=clearBtn.disabled=!items.length;zipBtn.disabled=items.filter(x=>x.out).length<2;syncHint();});li.querySelector('.rm').setAttribute('aria-label',t('removeName','Remove {name}',{name:f.name}));list.appendChild(li);items.push(it);}
  btn.disabled=!items.length;clearBtn.disabled=!items.length;
  if(items.length)status.textContent=tp('count',items.length,'{n} image in the list.','{n} images in the list.');syncHint();
}
clearBtn.addEventListener('click',()=>{items.forEach(i=>{if(i.url)URL.revokeObjectURL(i.url);});items=[];list.innerHTML='';btn.disabled=zipBtn.disabled=clearBtn.disabled=true;prog.hidden=true;status.textContent='';syncHint();});
$('files').addEventListener('change',e=>{add(e.target.files);e.target.value='';});
const drop=$('drop');
['dragenter','dragover'].forEach(t=>drop.addEventListener(t,e=>{e.preventDefault();drop.classList.add('over');}));
['dragleave','drop'].forEach(t=>drop.addEventListener(t,e=>{e.preventDefault();drop.classList.remove('over');}));
drop.addEventListener('drop',e=>add(e.dataTransfer.files));
const pick=()=>$('files').click();
drop.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();if(!e.repeat)pick();}else if(e.key===' '||e.key==='Spacebar'){e.preventDefault();}});
drop.addEventListener('keyup',e=>{if(e.key===' '||e.key==='Spacebar'){e.preventDefault();pick();}});
drop.addEventListener('click',e=>{if(e.target&&e.target.id==='files')return;pick();});
btn.addEventListener('click',async()=>{
  btn.disabled=true;clearBtn.disabled=true;prog.hidden=false;prog.max=items.length;prog.value=0;const type=fmtSel.value,ext=OUT.find(o=>o[0]===type)[2],qual=q.value/100;let ok=0;
  for(let i=0;i<items.length;i++){const it=items[i],s=it.li.querySelector('.s');status.textContent=t('progress','Converting {i} of {n}…',{i:i+1,n:items.length});s.textContent=t('working','Converting…');s.className='s file-status is-working';
    try{const b=await convert(it,type,qual);const name=it.file.name.replace(/\.[^.]+$/,'')+'.'+ext;it.out={name,blob:b};
      if(it.url)URL.revokeObjectURL(it.url);it.url=URL.createObjectURL(b);
      s.innerHTML='';const a=document.createElement('a');a.href=it.url;a.download=name;a.className='dl';if(isHeif(it.file)){const h=document.createElement('span');h.className='heic-note';h.textContent=t('firstOnly','First image only · ');s.textContent='';s.appendChild(h);}a.textContent=t('download','Download {ext} ({size})',{ext:ext.toUpperCase(),size:kb(b.size)});s.className='s file-status is-done';s.appendChild(a);ok++;
    }catch(e){it.out=null;s.textContent=e.friendly||t('readErr',"Couldn't read this file. Is it a supported image (HEIC, HEIF, WebP, AVIF, PNG, JPEG)?");s.className='s file-status err';}
    prog.value=i+1;
  }
  status.textContent=t('done','Done: {ok} of {n} converted locally.',{ok,n:items.length});btn.disabled=false;clearBtn.disabled=false;zipBtn.disabled=ok<2;syncHint(ok);
});
zipBtn.addEventListener('click',async()=>{const fs=items.filter(i=>i.out).map(i=>i.out);const seen={};fs.forEach(f=>{let n=f.name,k=1;while(seen[n])n=f.name.replace(/(\.[^.]+)$/,'-'+(k++)+'$1');seen[n]=1;f.name=n;});
  const z=await makeZip(fs);const a=document.createElement('a');a.href=URL.createObjectURL(z);a.download='converted-images.zip';document.body.appendChild(a);a.click();a.remove();});
})();
