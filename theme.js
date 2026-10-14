// Theme: loaded synchronously in <head> (external, CSP-safe) so the right palette applies before first paint.
// Choice stored ONLY in localStorage key "lic-theme" ("system" | "light" | "dark"); never sent anywhere. No cookies.
(function(){
  'use strict';
  var KEY='lic-theme',root=document.documentElement,mq=window.matchMedia?window.matchMedia('(prefers-color-scheme: dark)'):null;
  function get(){try{var v=window.localStorage.getItem(KEY);return v==='light'||v==='dark'?v:'system';}catch(e){return 'system';}}
  function set(v){try{if(v==='system')window.localStorage.removeItem(KEY);else window.localStorage.setItem(KEY,v);}catch(e){/* storage blocked: choice applies to this page view only */}}
  var choice=get();
  function apply(){var dark=choice==='dark'||(choice==='system'&&mq&&mq.matches);root.setAttribute('data-theme',dark?'dark':'light');}
  apply();
  if(mq){var h=function(){if(choice==='system')apply();};if(mq.addEventListener)mq.addEventListener('change',h);else if(mq.addListener)mq.addListener(h);}
  document.addEventListener('DOMContentLoaded',function(){
    var sel=document.getElementById('theme');if(!sel)return;
    sel.value=choice;
    sel.addEventListener('change',function(){choice=sel.value;set(choice);apply();});
  });
})();
