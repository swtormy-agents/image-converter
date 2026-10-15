// Theme: loaded synchronously in <head> (external, CSP-safe) so the right palette applies before first paint.
// Choice stored ONLY in localStorage key "lic-theme" ("system" | "light" | "dark"); never sent anywhere. No cookies.
// v2 (2026-10-15): on mobile (<=599px) the theme control is hidden and the system theme always applies;
// the stored desktop choice is kept untouched and applies again at >=600px.
(function(){
  'use strict';
  var KEY='lic-theme',root=document.documentElement,
      mq=window.matchMedia?window.matchMedia('(prefers-color-scheme: dark)'):null,
      mob=window.matchMedia?window.matchMedia('(max-width: 599px)'):null;
  function get(){try{var v=window.localStorage.getItem(KEY);return v==='light'||v==='dark'?v:'system';}catch(e){return 'system';}}
  function set(v){try{if(v==='system')window.localStorage.removeItem(KEY);else window.localStorage.setItem(KEY,v);}catch(e){/* storage blocked */}}
  var choice=get();
  function apply(){var c=(mob&&mob.matches)?'system':choice;var dark=c==='dark'||(c==='system'&&mq&&mq.matches);root.setAttribute('data-theme',dark?'dark':'light');}
  apply();
  function on(m,h){if(!m)return;if(m.addEventListener)m.addEventListener('change',h);else if(m.addListener)m.addListener(h);}
  on(mq,apply);on(mob,apply);
  document.addEventListener('DOMContentLoaded',function(){
    var sel=document.getElementById('theme');if(!sel||sel.tagName!=='SELECT')return;
    sel.value=choice;
    sel.addEventListener('change',function(){choice=sel.value==='light'||sel.value==='dark'?sel.value:'system';set(choice);apply();});
  });
})();
