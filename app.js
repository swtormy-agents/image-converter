(function(){
'use strict';
const cfg=window.LIC_CONFIG||{HEIC_WASM_ENABLED:false};
const $=id=>document.getElementById(id);
const prog=$('prog'),clearBtn=$('clear'),fmtSel=$('fmt'),q=$('q'),qv=$('qv'),list=$('list'),status=$('status'),btn=$('convert'),zipBtn=$('zip');
let items=[];
const OUT=[['image/jpeg','JPEG','jpg'],['image/png','PNG','png'],['image/webp','WebP','webp'],['image/avif','AVIF','avif']];

function canEncode(type){return new Promise(r=>{const c=document.createElement('canvas');c.width=c.height=2;c.toBlob(b=>r(!!b&&b.type===type),type,0.8);});}
(async()=>{for(const [t,l] of OUT){if(t==='image/jpeg'||t==='image/png'||await canEncode(t)){const o=document.createElement('option');o.value=t;o.textContent=l;fmtSel.appendChild(o);}}const pre=document.body.dataset.out;if(pre&&[...fmtSel.options].some(o=>o.value===pre))fmtSel.value=pre;})();
q.addEventListener('input',()=>{qv.textContent=q.value;});

function isHeif(f){return /\.(heic|heif)$/i.test(f.name)||/image\/hei[cf]/i.test(f.type);}

async function nativeDecode(file){
  if(window.createImageBitmap){try{return await createImageBitmap(file);}catch(e){}}
  return new Promise((res,rej)=>{const u=URL.createObjectURL(file),i=new Image();i.onload=()=>{res(i);};i.onerror=()=>{URL.revokeObjectURL(u);rej(new Error('native decode failed'));};i.src=u;});
}

// Lazily loaded, separate LGPL module (same origin). Kill-switch: config.js HEIC_WASM_ENABLED=false.
let heifP=null;
function loadHeif(){
  if(!cfg.HEIC_WASM_ENABLED)return Promise.reject(new Error('HEIC decoder is disabled on this site'));
  if(!heifP)heifP=new Promise((res,rej)=>{
    const s=document.createElement('script');s.src=cfg.HEIC_WASM_PATH+'libheif.js';
    s.onload=()=>{fetch(cfg.HEIC_WASM_PATH+'libheif.wasm').then(r=>{if(!r.ok)throw new Error('could not load HEIC decoder');return r.arrayBuffer();}).then(b=>window.libheif({wasmBinary:b})).then(res,rej);};
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
  if(!blob||blob.type!==type)throw new Error('your browser cannot encode this format');
  return blob;
}
function kb(n){return n<1024*1024?Math.max(1,Math.round(n/1024))+' KB':(n/1048576).toFixed(1)+' MB';}
function add(files){
  for(const f of files){const li=document.createElement('li');li.className='file';
    li.innerHTML='<span class="file-name"></span><span class="file-meta"></span><span class="s file-status">Ready</span>';
    li.querySelector('.file-name').textContent=f.name;li.querySelector('.file-meta').textContent=kb(f.size);li.title=f.name;
    list.appendChild(li);items.push({file:f,li,out:null});}
  btn.disabled=!items.length;clearBtn.disabled=!items.length;
  if(items.length)status.textContent=items.length+(items.length===1?' file':' files')+' ready. Choose a format and press Convert.';
}
clearBtn.addEventListener('click',()=>{items.forEach(i=>{if(i.url)URL.revokeObjectURL(i.url);});items=[];list.innerHTML='';btn.disabled=zipBtn.disabled=clearBtn.disabled=true;prog.hidden=true;status.textContent='';});
$('files').addEventListener('change',e=>{add(e.target.files);e.target.value='';});
const drop=$('drop');
['dragenter','dragover'].forEach(t=>drop.addEventListener(t,e=>{e.preventDefault();drop.classList.add('over');}));
['dragleave','drop'].forEach(t=>drop.addEventListener(t,e=>{e.preventDefault();drop.classList.remove('over');}));
drop.addEventListener('drop',e=>add(e.dataTransfer.files));
drop.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();$('files').click();}});
drop.addEventListener('click',e=>{if(e.target===drop||e.target.classList.contains('drop-title'))$('files').click();});
btn.addEventListener('click',async()=>{
  btn.disabled=true;clearBtn.disabled=true;prog.hidden=false;prog.max=items.length;prog.value=0;const type=fmtSel.value,ext=OUT.find(o=>o[0]===type)[2],qual=q.value/100;let ok=0;
  for(let i=0;i<items.length;i++){const it=items[i],s=it.li.querySelector('.s');status.textContent='Converting '+(i+1)+' of '+items.length+'…';s.textContent='Converting…';s.className='s file-status is-working';
    try{const b=await convert(it,type,qual);const name=it.file.name.replace(/\.[^.]+$/,'')+'.'+ext;it.out={name,blob:b};
      if(it.url)URL.revokeObjectURL(it.url);it.url=URL.createObjectURL(b);
      s.innerHTML='';const a=document.createElement('a');a.href=it.url;a.download=name;a.className='dl';a.textContent='Download '+ext.toUpperCase()+' ('+kb(b.size)+')';s.className='s file-status is-done';s.appendChild(a);ok++;
    }catch(e){it.out=null;s.textContent='Error: '+e.message;s.className='s file-status err';}
    prog.value=i+1;
  }
  status.textContent='Done: '+ok+' of '+items.length+' converted locally.';btn.disabled=false;clearBtn.disabled=false;zipBtn.disabled=ok<2;
});
zipBtn.addEventListener('click',async()=>{const fs=items.filter(i=>i.out).map(i=>i.out);const seen={};fs.forEach(f=>{let n=f.name,k=1;while(seen[n])n=f.name.replace(/(\.[^.]+)$/,'-'+(k++)+'$1');seen[n]=1;f.name=n;});
  const z=await makeZip(fs);const a=document.createElement('a');a.href=URL.createObjectURL(z);a.download='converted-images.zip';document.body.appendChild(a);a.click();a.remove();});
})();
