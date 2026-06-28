/* Futurism Design System — minimal vanilla behaviour for the interactive
   components. No dependencies. Wire markup per references/components.md. */

// Custom select: click value to open, click option to pick, click-outside closes.
function fdSel(opt){
  var sel=opt.closest('.sel');
  sel.querySelectorAll('.sel-opt').forEach(function(o){o.classList.remove('sel-on')});
  opt.classList.add('sel-on');
  sel.querySelector('.sel-cur').textContent=opt.textContent;
}

// Tabs: activate clicked tab + matching panel within the same container.
function fdTab(el,i){
  var root=el.closest('[data-tabs]')||el.closest('.sect')||document;
  root.querySelectorAll('.tab').forEach(function(t){t.classList.remove('on')});
  el.classList.add('on');
  root.querySelectorAll('.panel').forEach(function(p,j){p.classList.toggle('on',j===i)});
}

// Theme: flip light/dark on the root element (default <html>).
function fdTheme(root){
  root=root||document.documentElement;
  root.setAttribute('data-theme',root.getAttribute('data-theme')==='dark'?'light':'dark');
}

document.addEventListener('click',function(e){
  // open/close selects
  var val=e.target.closest('.sel-val');
  if(val){val.closest('.sel').classList.toggle('open')}
  // toggle switches
  var tg=e.target.closest('.toggle');
  if(tg){tg.classList.toggle('on')}
  // close any open select when clicking elsewhere
  document.querySelectorAll('.sel.open').forEach(function(s){if(!s.contains(e.target))s.classList.remove('open')});
},false);
