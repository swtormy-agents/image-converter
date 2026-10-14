// Minimal store-only (no compression) ZIP writer. Images are already compressed.
(function(){
  const T=new Uint32Array(256);for(let n=0;n<256;n++){let c=n;for(let k=0;k<8;k++)c=c&1?0xEDB88320^(c>>>1):c>>>1;T[n]=c>>>0;}
  function crc(b){let c=0xFFFFFFFF;for(let i=0;i<b.length;i++)c=T[(c^b[i])&255]^(c>>>8);return (c^0xFFFFFFFF)>>>0;}
  window.makeZip=async function(files){ // [{name, blob}]
    const parts=[],cen=[];let off=0;const enc=new TextEncoder();
    for(const f of files){
      const data=new Uint8Array(await f.blob.arrayBuffer()),name=enc.encode(f.name),c=crc(data);
      const h=new DataView(new ArrayBuffer(30));
      h.setUint32(0,0x04034b50,true);h.setUint16(4,20,true);h.setUint16(6,0x0800,true);h.setUint32(14,c,true);
      h.setUint32(18,data.length,true);h.setUint32(22,data.length,true);h.setUint16(26,name.length,true);
      parts.push(h,name,data);
      const d=new DataView(new ArrayBuffer(46));
      d.setUint32(0,0x02014b50,true);d.setUint16(4,20,true);d.setUint16(6,20,true);d.setUint16(8,0x0800,true);d.setUint32(16,c,true);
      d.setUint32(20,data.length,true);d.setUint32(24,data.length,true);d.setUint16(28,name.length,true);d.setUint32(42,off,true);
      cen.push(d,name);off+=30+name.length+data.length;
    }
    let cs=0;for(const x of cen)cs+=x.byteLength;
    const e=new DataView(new ArrayBuffer(22));e.setUint32(0,0x06054b50,true);e.setUint16(8,files.length,true);e.setUint16(10,files.length,true);
    e.setUint32(12,cs,true);e.setUint32(16,off,true);
    return new Blob([...parts,...cen,e],{type:'application/zip'});
  };
})();
