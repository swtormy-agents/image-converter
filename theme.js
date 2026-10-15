// Theme (lagoon): loaded synchronously in <head>, external file (CSP-safe), runs before first paint.
// Default: no data-theme attribute -> daisyUI applies "lagoon" or, via prefers-color-scheme: dark, "lagoon-dark".
// Compatibility: the existing localStorage key "lic-theme" ("system" | "light" | "dark") is still honoured on
// desktop (>=600px) and set by the desktop-only <select id="theme">; on mobile (<=599px) the system theme always applies
// and the stored desktop choice is kept untouched. Never sent anywhere. No cookies.
(function(){
  'use strict';
  var KEY='lic-theme',root=document.documentElement,
      mob=window.matchMedia?window.matchMedia('(max-width: 599px)'):null;
  function get(){try{var v=window.localStorage.getItem(KEY);return v==='light'||v==='dark'?v:'system';}catch(e){return 'system';}}
  function set(v){try{if(v==='system')window.localStorage.removeItem(KEY);else window.localStorage.setItem(KEY,v);}catch(e){}}
  var choice=get();
  function apply(){var c=(mob&&mob.matches)?'system':choice;
    if(c==='system')root.removeAttribute('data-theme');else root.setAttribute('data-theme',c==='dark'?'lagoon-dark':'lagoon');}
  apply();
  if(mob){if(mob.addEventListener)mob.addEventListener('change',apply);else if(mob.addListener)mob.addListener(apply);}
  document.addEventListener('DOMContentLoaded',function(){
    var sel=document.getElementById('theme');if(!sel||sel.tagName!=='SELECT')return;
    sel.value=choice;
    sel.addEventListener('change',function(){choice=sel.value==='light'||sel.value==='dark'?sel.value:'system';set(choice);apply();});
  });
})();
