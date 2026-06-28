/* Futurism Design System — minimal vanilla behaviour for the interactive
   components. No dependencies. Wire markup per references/components.md. */

// Custom select: click value to open, click option to pick, click-outside closes.
// An option's value is its data-value when present (lets label differ from value,
// e.g. label "Grand Prix" -> value "spec-gp"), otherwise its label text.
// Keyboard + ARIA are wired by fdInit (roles) and the keydown delegate below.
function fdOptValue(o){return o.dataset.value!==undefined?o.dataset.value:o.textContent}
// Open/close a select, keeping aria-expanded in sync; focus the active option on open.
function fdSelOpen(sel,open){
  sel.classList.toggle('open',open);
  var v=sel.querySelector('.sel-val');
  if(v)v.setAttribute('aria-expanded',open?'true':'false');
  if(open){var cur=sel.querySelector('.sel-opt.sel-on')||sel.querySelector('.sel-opt');if(cur)cur.focus()}
}
function fdSel(opt){
  var sel=opt.closest('.sel');
  sel.querySelectorAll('.sel-opt').forEach(function(o){o.classList.remove('sel-on');o.setAttribute('aria-selected','false')});
  opt.classList.add('sel-on');opt.setAttribute('aria-selected','true');
  sel.querySelector('.sel-cur').textContent=opt.textContent;
  sel.dataset.value=fdOptValue(opt);
  fdSelOpen(sel,false);
  var v=sel.querySelector('.sel-val');if(v)v.focus();
}
// Read a .sel's current value (the picked option's data-value/label).
function fdSelVal(sel){return sel?(sel.dataset.value||''):''}

// Tabs: activate clicked tab + matching panel; keep aria-selected + roving tabindex.
function fdTab(el,i){
  var root=el.closest('[data-tabs]')||el.closest('.sect')||document;
  root.querySelectorAll('.tab').forEach(function(t){t.classList.remove('on');t.setAttribute('aria-selected','false');t.tabIndex=-1});
  el.classList.add('on');el.setAttribute('aria-selected','true');el.tabIndex=0;
  root.querySelectorAll('.panel').forEach(function(p,j){p.classList.toggle('on',j===i)});
}

// Auto-wire ARIA roles + tabindex on .sel / .tabs / .toggle so markup stays clean.
// Idempotent; call again after injecting new components. Runs once on load.
function fdInit(root){
  root=root||document;
  root.querySelectorAll('.sel').forEach(function(sel){
    var v=sel.querySelector('.sel-val');
    if(v){v.setAttribute('role','combobox');v.setAttribute('aria-haspopup','listbox');v.setAttribute('aria-expanded','false');if(!v.hasAttribute('tabindex'))v.tabIndex=0}
    var list=sel.querySelector('.sel-list');if(list)list.setAttribute('role','listbox');
    sel.querySelectorAll('.sel-opt').forEach(function(o){o.setAttribute('role','option');o.setAttribute('aria-selected',o.classList.contains('sel-on')?'true':'false');o.tabIndex=-1});
  });
  root.querySelectorAll('.tabs').forEach(function(tl){
    tl.setAttribute('role','tablist');
    tl.querySelectorAll('.tab').forEach(function(t){t.setAttribute('role','tab');t.setAttribute('aria-selected',t.classList.contains('on')?'true':'false');t.tabIndex=t.classList.contains('on')?0:-1});
  });
  root.querySelectorAll('.panel').forEach(function(p){p.setAttribute('role','tabpanel');if(!p.hasAttribute('tabindex'))p.tabIndex=0});
  root.querySelectorAll('.toggle').forEach(function(t){
    if(t.tagName!=='BUTTON'){t.setAttribute('role','switch');if(!t.hasAttribute('tabindex'))t.tabIndex=0}
    t.setAttribute('aria-checked',t.classList.contains('on')?'true':'false');
  });
}
if(document.readyState!=='loading')fdInit();else document.addEventListener('DOMContentLoaded',function(){fdInit()});

// Theme: flip light/dark on the root element (default <html>).
function fdTheme(root){
  root=root||document.documentElement;
  root.setAttribute('data-theme',root.getAttribute('data-theme')==='dark'?'light':'dark');
}

// Toast: non-blocking message. opts: {type:'info'|'err' (default err), timeout ms}.
// Darts in from the right; auto-dismisses by sliding back out (no fade).
function fdToast(msg,opts){
  opts=opts||{};
  var wrap=document.querySelector('.toaster');
  if(!wrap){wrap=document.createElement('div');wrap.className='toaster';document.body.appendChild(wrap)}
  var t=document.createElement('div');
  t.className='toast'+(opts.type==='info'?' info':'');
  t.textContent=msg;
  wrap.appendChild(t);
  setTimeout(function(){
    t.style.transition='transform var(--med) var(--ease)';
    t.style.transform='translateX(40px)';
    setTimeout(function(){if(t.parentNode)t.remove()},220);
  },opts.timeout||3200);
  return t;
}

// Off-canvas drawer: toggle .drawer-open on the panel + show/hide its scrim.
function fdDrawer(panel,scrim){
  panel=typeof panel==='string'?document.getElementById(panel):panel;
  if(!panel)return;
  var open=panel.classList.toggle('drawer-open');
  scrim=typeof scrim==='string'?document.getElementById(scrim):scrim;
  if(scrim)scrim.style.display=open?'block':'none';
}

// Accent picker: swap --accent and (in dark) --shadow at runtime, persist.
// Pass the picker root .accpick + an array of {name,light,dark}. In dark the
// offset shadow follows the accent; in light it stays ink.
function fdAccent(pick,accents,onChange){
  pick=typeof pick==='string'?document.getElementById(pick):pick;
  if(!pick)return;
  var trig=pick.querySelector('.acctrig'),pop=pick.querySelector('.accpop');
  var saved=localStorage.getItem('fd-accent')||accents[0].name;
  function dark(){return document.documentElement.getAttribute('data-theme')==='dark'}
  function apply(a){
    var col=dark()?a.dark:a.light,r=document.documentElement.style;
    r.setProperty('--accent',col);
    r.setProperty('--shadow',dark()?col:'#1a1714');
    localStorage.setItem('fd-accent',a.name);
    if(trig)trig.style.background=col;
    render(a);
    if(onChange)onChange(a);
  }
  function render(cur){
    if(!pop)return;pop.innerHTML='';
    accents.forEach(function(a){
      var s=document.createElement('button');
      var on=a.name===cur.name;
      s.className='acc'+(on?' on':'');
      s.style.background=dark()?a.dark:a.light;s.title=a.name;
      s.setAttribute('aria-label',a.name);s.setAttribute('aria-pressed',on?'true':'false');
      s.onclick=function(){apply(a);pick.classList.remove('open');if(trig)trig.setAttribute('aria-expanded','false')};
      pop.appendChild(s);
    });
  }
  if(trig){
    trig.setAttribute('aria-haspopup','true');trig.setAttribute('aria-expanded','false');
    if(!trig.getAttribute('aria-label'))trig.setAttribute('aria-label','Accent color');
    trig.onclick=function(){var o=pick.classList.toggle('open');trig.setAttribute('aria-expanded',o?'true':'false')};
  }
  apply(accents.find(function(a){return a.name===saved})||accents[0]);
  return {reapply:function(){apply(accents.find(function(a){return a.name===(localStorage.getItem('fd-accent')||accents[0].name)})||accents[0])}};
}

document.addEventListener('click',function(e){
  // open/close selects (via fdSelOpen so aria-expanded stays synced)
  var val=e.target.closest('.sel-val');
  if(val){var s=val.closest('.sel');fdSelOpen(s,!s.classList.contains('open'))}
  // toggle switches
  var tg=e.target.closest('.toggle');
  if(tg){tg.classList.toggle('on');tg.setAttribute('aria-checked',tg.classList.contains('on')?'true':'false')}
  // close any open select when clicking elsewhere
  document.querySelectorAll('.sel.open').forEach(function(s){if(!s.contains(e.target))fdSelOpen(s,false)});
  // close accent popover when clicking outside it
  document.querySelectorAll('.accpick.open').forEach(function(p){if(!p.contains(e.target)){p.classList.remove('open');var t=p.querySelector('.acctrig');if(t)t.setAttribute('aria-expanded','false')}});
},false);

// Keyboard for the div-built controls (native button/dialog/checkbox handle their own).
document.addEventListener('keydown',function(e){
  // Custom select: Enter/Space/Down open; Up/Down move; Enter pick; Esc/Tab close.
  var sel=e.target.closest('.sel');
  if(sel){
    var opts=Array.prototype.slice.call(sel.querySelectorAll('.sel-opt'));
    var open=sel.classList.contains('open'),i=opts.indexOf(e.target);
    if(e.key==='ArrowDown'){e.preventDefault();if(!open)fdSelOpen(sel,true);else if(i<opts.length-1)opts[i+1].focus()}
    else if(e.key==='ArrowUp'){e.preventDefault();if(i>0)opts[i-1].focus()}
    else if(e.key==='Enter'||e.key===' '){e.preventDefault();if(!open)fdSelOpen(sel,true);else if(i>-1)fdSel(opts[i])}
    else if(e.key==='Escape'){if(open){fdSelOpen(sel,false);var v=sel.querySelector('.sel-val');if(v)v.focus()}}
    else if(e.key==='Tab'){if(open)fdSelOpen(sel,false)}
    return;
  }
  // Tabs: Left/Right move focus + activate (roving tabindex).
  var tab=e.target.closest('.tab');
  if(tab&&(e.key==='ArrowRight'||e.key==='ArrowLeft')){
    e.preventDefault();
    var tabs=Array.prototype.slice.call(tab.closest('.tabs').querySelectorAll('.tab')),ti=tabs.indexOf(tab);
    var n=e.key==='ArrowRight'?(ti+1)%tabs.length:(ti-1+tabs.length)%tabs.length;
    tabs[n].focus();tabs[n].click();
    return;
  }
  // Toggle (div role=switch): Enter/Space flips it (native <button> handles itself).
  var tg=e.target.closest('.toggle');
  if(tg&&tg.tagName!=='BUTTON'&&(e.key==='Enter'||e.key===' ')){
    e.preventDefault();tg.classList.toggle('on');tg.setAttribute('aria-checked',tg.classList.contains('on')?'true':'false');
  }
},false);
