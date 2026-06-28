/* Futurism Design System — minimal vanilla behaviour for the interactive
   components. No dependencies. Wire markup per references/components.md. */

// Custom select: click value to open, click option to pick, click-outside closes.
// An option's value is its data-value when present (lets label differ from value,
// e.g. label "Opus 4.8" -> value "claude-opus-4-8"), otherwise its label text.
function fdOptValue(o){return o.dataset.value!==undefined?o.dataset.value:o.textContent}
function fdSel(opt){
  var sel=opt.closest('.sel');
  sel.querySelectorAll('.sel-opt').forEach(function(o){o.classList.remove('sel-on')});
  opt.classList.add('sel-on');
  sel.querySelector('.sel-cur').textContent=opt.textContent;
  sel.dataset.value=fdOptValue(opt);
  sel.classList.remove('open');
}
// Read a .sel's current value (the picked option's data-value/label).
function fdSelVal(sel){return sel?(sel.dataset.value||''):''}

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
      s.className='acc'+(a.name===cur.name?' on':'');
      s.style.background=dark()?a.dark:a.light;s.title=a.name;
      s.onclick=function(){apply(a);pick.classList.remove('open')};
      pop.appendChild(s);
    });
  }
  if(trig)trig.onclick=function(){pick.classList.toggle('open')};
  apply(accents.find(function(a){return a.name===saved})||accents[0]);
  return {reapply:function(){apply(accents.find(function(a){return a.name===(localStorage.getItem('fd-accent')||accents[0].name)})||accents[0])}};
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
  // close accent popover when clicking outside it
  document.querySelectorAll('.accpick.open').forEach(function(p){if(!p.contains(e.target))p.classList.remove('open')});
},false);
