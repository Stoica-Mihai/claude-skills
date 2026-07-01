/* Futurism Design System — minimal vanilla behaviour for the interactive
   components. No dependencies. Wire markup per references/components.md. */

// Custom select: click value to open, click option to pick, click-outside closes.
// An option's value is its data-value when present (lets label differ from value,
// e.g. label "Grand Prix" -> value "spec-gp"), otherwise its label text.
// Keyboard + ARIA are wired by fdInit (roles) and the keydown delegate below.
function fdOptValue(o){return o.dataset.value!==undefined?o.dataset.value:o.textContent}
// Promote the dropdown from its CSS default (position:absolute, self-anchored) to
// position:fixed anchored to the trigger, so it floats in the top layer and isn't
// clipped by an overflow:auto ancestor (e.g. a scrolling modal). Flips above the
// trigger when there isn't room below. Cleared by fdSelReset on close so the
// no-JS absolute default is restored.
function fdSelPosition(sel){
  var list=sel.querySelector('.sel-list'),v=sel.querySelector('.sel-val');
  if(!list||!v)return;
  var gap=4,m=6,r=v.getBoundingClientRect(),vh=window.innerHeight;
  var spaceBelow=vh-r.bottom-gap-m,spaceAbove=r.top-gap-m;
  var natural=Math.min(list.scrollHeight,240);
  // open downward unless it won't fit and there's more room above
  var up=spaceBelow<natural&&spaceAbove>spaceBelow;
  // cap height to the chosen side so the list never runs off-screen (it scrolls inside)
  var h=Math.min(natural,Math.max(up?spaceAbove:spaceBelow,0));
  var top=up?r.top-gap-h:r.bottom+gap;
  top=Math.max(m,Math.min(top,vh-h-m));
  list.style.position='fixed';
  list.style.right='auto';
  list.style.left=r.left+'px';
  list.style.width=r.width+'px';
  list.style.maxHeight=h+'px';
  list.style.top=top+'px';
  list.style.transformOrigin=up?'bottom':'top';
}
function fdSelReset(sel){
  var list=sel.querySelector('.sel-list');
  if(list)list.style.cssText='';
}
// Open/close a select, keeping aria-expanded in sync; focus the active option on open.
function fdSelOpen(sel,open){
  if(open)document.querySelectorAll('.sel.open').forEach(function(o){if(o!==sel)fdSelOpen(o,false)});
  sel.classList.toggle('open',open);
  var v=sel.querySelector('.sel-val');
  if(v)v.setAttribute('aria-expanded',open?'true':'false');
  if(!sel._fdReposition)sel._fdReposition=function(){fdSelPosition(sel)};
  if(open){
    fdSelPosition(sel);
    // capture=true so a scroll of ANY ancestor (the modal's own scroll) repositions it
    window.addEventListener('scroll',sel._fdReposition,true);
    window.addEventListener('resize',sel._fdReposition);
    var cur=sel.querySelector('.sel-opt.sel-on')||sel.querySelector('.sel-opt');if(cur)cur.focus();
  }else{
    window.removeEventListener('scroll',sel._fdReposition,true);
    window.removeEventListener('resize',sel._fdReposition);
    fdSelReset(sel);
  }
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

// Scope containing a tab strip AND its panels. Prefer an explicit [data-tabs]
// wrapper; fall back to the tab strip's parent (panels are usually its siblings).
function fdTabScope(el){
  var r=el.closest('[data-tabs]')||el.closest('.sect')||el.parentNode;
  if(r&&!r.querySelector('.panel')){var t=el.closest('.tabs');if(t&&t.parentNode)r=t.parentNode}
  return r||document;
}
// Tabs: activate the tab + matching panel; keep aria-selected + roving tabindex.
function fdTab(el,i){
  var root=fdTabScope(el);
  root.querySelectorAll('.tab').forEach(function(t){t.classList.remove('on');t.setAttribute('aria-selected','false');t.tabIndex=-1});
  el.classList.add('on');el.setAttribute('aria-selected','true');el.tabIndex=0;
  root.querySelectorAll('.panel').forEach(function(p,j){var on=j===i;p.classList.toggle('on',on);p.hidden=!on});
}

var fdUid=0;
function fdId(el,prefix){if(!el.id)el.id=prefix+(fdUid++);return el.id}
// Auto-wire ARIA roles + tabindex on .sel / .tabs / .toggle so markup stays clean.
// Idempotent; call again after injecting new components. Runs once on load.
function fdInit(root){
  root=root||document;
  // Select = button that pops a listbox (APG menu-button/listbox; roving focus on
  // options is correct here, unlike role=combobox which needs aria-activedescendant).
  root.querySelectorAll('.sel').forEach(function(sel){
    var v=sel.querySelector('.sel-val'),list=sel.querySelector('.sel-list');
    if(list)list.setAttribute('role','listbox');
    if(v){v.setAttribute('role','button');v.setAttribute('aria-haspopup','listbox');v.setAttribute('aria-expanded','false');
      if(list)v.setAttribute('aria-controls',fdId(list,'fd-list-'));if(!v.hasAttribute('tabindex'))v.tabIndex=0}
    sel.querySelectorAll('.sel-opt').forEach(function(o){o.setAttribute('role','option');o.setAttribute('aria-selected',o.classList.contains('sel-on')?'true':'false');o.tabIndex=-1});
  });
  root.querySelectorAll('.tabs').forEach(function(tl){
    tl.setAttribute('role','tablist');
    var scope=fdTabScope(tl.querySelector('.tab')||tl);
    var panels=Array.prototype.slice.call(scope.querySelectorAll('.panel'));
    Array.prototype.slice.call(tl.querySelectorAll('.tab')).forEach(function(t,i){
      t.setAttribute('role','tab');
      var on=t.classList.contains('on');t.setAttribute('aria-selected',on?'true':'false');t.tabIndex=on?0:-1;
      var p=panels[i];
      if(p){p.setAttribute('role','tabpanel');t.setAttribute('aria-controls',fdId(p,'fd-panel-'));p.setAttribute('aria-labelledby',fdId(t,'fd-tab-'));if(!p.hasAttribute('tabindex'))p.tabIndex=0;p.hidden=!on}
    });
  });
  root.querySelectorAll('.toggle').forEach(function(t){
    if(t.tagName!=='BUTTON'){t.setAttribute('role','switch');if(!t.hasAttribute('tabindex'))t.tabIndex=0}
    t.setAttribute('aria-checked',t.classList.contains('on')?'true':'false');
  });
  // Stepper: a native <input type=number> (spinbutton — types, arrows, clamps to
  // min/max/step) welded between −/+ buttons. The buttons step the input; the input
  // itself carries keyboard + a11y. Guard so re-init doesn't stack listeners.
  root.querySelectorAll('.stepper').forEach(function(st){
    if(st._fdStep)return;st._fdStep=true;
    var input=st.querySelector('input.num'),dn=st.querySelector('.step-dn'),up=st.querySelector('.step-up');
    if(!input)return;
    // The +/- buttons change input.value while focus stays on the button, so a
    // screen reader won't pick up the change from the input alone (that only
    // fires for the FOCUSED element's own edits) — a visually-hidden aria-live
    // region, kept in sync on every bump, carries the announcement instead.
    var live=document.createElement('span');
    live.setAttribute('role','status');live.setAttribute('aria-live','polite');
    live.style.cssText='position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap';
    st.appendChild(live);
    function clamp(){var v=parseFloat(input.value);if(isNaN(v))return;
      var lo=input.min!==''?parseFloat(input.min):-Infinity,hi=input.max!==''?parseFloat(input.max):Infinity;
      var c=Math.max(lo,Math.min(hi,v));if(c!==v)input.value=c;}
    function bump(dir){input[dir>0?'stepUp':'stepDown']();clamp();input.dispatchEvent(new Event('change',{bubbles:true}));live.textContent=input.value}
    if(dn)dn.addEventListener('click',function(){bump(-1)});
    if(up)up.addEventListener('click',function(){bump(1)});
    input.addEventListener('change',clamp);
  });
  // A closed drawer's own links/buttons are still natively tabbable (off-screen
  // via translateX isn't enough to pull them out of tab order) until fdDrawer()
  // first toggles it — set the initial closed state here so page load itself
  // doesn't leave them reachable before any interaction happens.
  root.querySelectorAll('.drawer').forEach(function(d){
    if(!d.classList.contains('drawer-open'))fdDrawerFocusables(d).forEach(function(el){el.tabIndex=-1});
  });
}
if(document.readyState!=='loading')fdInit();else document.addEventListener('DOMContentLoaded',function(){fdInit()});

// Theme: flip light/dark on the root element (default <html>).
function fdTheme(root){
  root=root||document.documentElement;
  root.setAttribute('data-theme',root.getAttribute('data-theme')==='dark'?'light':'dark');
}

// Toast: non-blocking message. opts: {type:'err' for attention; default neutral, timeout ms}.
// Darts in from the right; auto-dismisses by sliding back out via the .out class (no fade).
function fdToast(msg,opts){
  opts=opts||{};
  var wrap=document.querySelector('.toaster');
  if(!wrap){wrap=document.createElement('div');wrap.className='toaster';wrap.setAttribute('role','status');wrap.setAttribute('aria-live','polite');document.body.appendChild(wrap)}
  var t=document.createElement('div');
  t.className='toast'+(opts.type==='err'?' err':'');
  t.textContent=msg;
  wrap.appendChild(t);
  setTimeout(function(){
    t.classList.add('out');
    setTimeout(function(){if(t.parentNode)t.remove()},220);
  },opts.timeout||3200);
  return t;
}

function fdDrawerFocusables(panel){
  return Array.prototype.slice.call(panel.querySelectorAll('a[href],button,input,select,textarea'));
}
// Trap Tab inside the open drawer so it can't escape to background content —
// without this, Tab from the last item just continues into whatever follows
// the drawer in DOM order.
function fdDrawerTrap(e){
  if(e.key!=='Tab')return;
  var panel=document.querySelector('.drawer.drawer-open');
  if(!panel)return;
  var f=fdDrawerFocusables(panel);if(!f.length)return;
  var first=f[0],last=f[f.length-1];
  if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus()}
  else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus()}
}
document.addEventListener('keydown',fdDrawerTrap);
// Off-canvas drawer: toggle .drawer-open on the panel + show/hide its scrim.
// While open: locks body scroll and traps Tab (above). While closed: the
// panel's own links/buttons are pulled out of tab order — off-screen via
// translateX doesn't do that on its own, they're still natively focusable.
function fdDrawer(panel,scrim){
  panel=typeof panel==='string'?document.getElementById(panel):panel;
  if(!panel)return;
  var open=panel.classList.toggle('drawer-open');
  if(open)panel._fdReturn=document.activeElement;
  fdDrawerSync(panel,open);
  var focusables=fdDrawerFocusables(panel);
  focusables.forEach(function(el){el.tabIndex=open?0:-1});
  document.body.style.overflow=open?'hidden':'';
  scrim=typeof scrim==='string'?document.getElementById(scrim):scrim;
  if(scrim)scrim.style.display=open?'block':'none';
  if(open&&focusables.length)focusables[0].focus();
}
// Keep the opener's aria-expanded in sync, and restore focus to it on close —
// matches the accent popover / select behaviour. Used by fdDrawer + Escape close.
function fdDrawerSync(panel,open){
  var r=panel._fdReturn;if(!r)return;
  if(r.hasAttribute&&r.hasAttribute('aria-expanded'))r.setAttribute('aria-expanded',open?'true':'false');
  if(!open&&r.focus)r.focus();
}

// Inline two-step destructive confirm on a .row-act container (no modal, no native
// confirm()). opts: { icon (idle SVG/text), label:'Delete', cancel:'Cancel',
// failLabel:'Failed', onConfirm: () => Promise }. First click arms (accent confirm +
// ghost cancel); focus moves to the SAFE cancel and Esc cancels; on cancel focus
// returns to the trigger. onConfirm rejecting flashes .failed then reverts to idle.
// The slot is a container, not a button, so its child buttons never nest in a button.
function fdConfirm(slot, opts){
  slot = typeof slot === 'string' ? document.getElementById(slot) : slot;
  if(!slot) return;
  opts = opts || {};
  var label = opts.label || 'Delete', cancel = opts.cancel || 'Cancel', failLabel = opts.failLabel || 'Failed';
  function mk(cls, txt){ var b=document.createElement('button'); b.type='button'; b.className=cls; b.textContent=txt; return b }
  function idle(){
    slot.classList.remove('confirming','failed'); slot.textContent='';
    var b=document.createElement('button'); b.type='button'; b.className='row-act-btn';
    b.setAttribute('aria-label', label); b.innerHTML = opts.icon || '✕';
    b.onclick=function(e){ e.stopPropagation(); e.preventDefault(); arm() };
    slot.appendChild(b);
  }
  function arm(){
    slot.classList.add('confirming'); slot.textContent='';
    var yes=mk('confirm-yes', label), no=mk('confirm-no', cancel);
    yes.setAttribute('aria-label', label); no.setAttribute('aria-label', cancel);
    yes.onclick=function(e){ e.stopPropagation(); e.preventDefault(); run() };
    no.onclick=function(e){ e.stopPropagation(); e.preventDefault(); idle(); var t=slot.querySelector('.row-act-btn'); if(t)t.focus() };
    slot.appendChild(yes); slot.appendChild(no);
    no.focus(); // land on the least-destructive option
  }
  function run(){
    Promise.resolve(opts.onConfirm && opts.onConfirm()).then(function(){
      // Success: if the row still exists, revert to idle and return focus to the
      // trigger; if onConfirm removed the row, hand focus off via onDone so it isn't
      // orphaned on a detached node (focus-order break right after a destructive act).
      if(slot.isConnected){ idle(); var t=slot.querySelector('.row-act-btn'); if(t)t.focus() }
      else if(opts.onDone) opts.onDone();
    }).catch(function(){
      slot.classList.remove('confirming'); slot.classList.add('failed'); slot.textContent='';
      var f=document.createElement('span'); f.className='row-act-fail'; f.textContent=failLabel;
      slot.appendChild(f);
      setTimeout(function(){ if(slot.isConnected) idle() }, 1800);
    });
  }
  slot.addEventListener('keydown', function(e){ if(e.key==='Escape' && slot.classList.contains('confirming')){ idle(); var t=slot.querySelector('.row-act-btn'); if(t)t.focus() } });
  idle();
}

// Accent picker: swap --accent and (in dark) --shadow at runtime, persist.
// Pass the picker root .accpick + an array of {name,light,dark}. In dark the
// offset shadow follows the accent; in light it stays ink.
// Relative luminance (WCAG) of a #rgb/#rrggbb color, 0..1.
function fdLuminance(hex){
  hex=String(hex).replace('#','');
  if(hex.length===3)hex=hex.replace(/./g,'$&$&');
  var v=[0,2,4].map(function(i){
    var c=parseInt(hex.substr(i,2),16)/255;
    return c<=.03928?c/12.92:Math.pow((c+.055)/1.055,2.4);
  });
  return .2126*v[0]+.7152*v[1]+.0722*v[2];
}
// Pick the kit's cream or near-black foreground — whichever contrasts better on `col`
// — so text/icons on an accent fill stay legible for ANY runtime-picked accent.
function fdOnAccent(col){
  var cream='#efe9dc',ink='#16140f',L=fdLuminance(col);
  function ratio(a,b){return (Math.max(a,b)+.05)/(Math.min(a,b)+.05)}
  return ratio(L,fdLuminance(cream))>=ratio(L,fdLuminance(ink))?cream:ink;
}
function fdAccent(pick,accents,onChange){
  pick=typeof pick==='string'?document.getElementById(pick):pick;
  if(!pick)return;
  var trig=pick.querySelector('.acctrig'),pop=pick.querySelector('.accpop'),current;
  var saved=localStorage.getItem('fd-accent')||accents[0].name;
  function dark(){return document.documentElement.getAttribute('data-theme')==='dark'}
  function apply(a){
    current=a;
    var col=dark()?a.dark:a.light,r=document.documentElement.style;
    r.setProperty('--accent',col);
    r.setProperty('--shadow',dark()?col:'#1a1714');
    // Keep the accent's paired foreground legible for any picked color; an accent
    // may override with onLight/onDark.
    r.setProperty('--on-accent',(dark()?a.onDark:a.onLight)||fdOnAccent(col));
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
    syncSwatchFocus();
  }
  // Swatches default to real <button>s (natively tabbable), so without this
  // they'd stay in Tab order even while the popover is closed/invisible
  // (transform:scaleY(0) blocks pointer/visual access but not keyboard focus).
  // Pull them out of the tab order when closed, same as .sel-opt's tabindex=-1.
  function syncSwatchFocus(){
    if(!pop)return;
    var open=pick.classList.contains('open');
    Array.prototype.slice.call(pop.querySelectorAll('.acc')).forEach(function(s){s.tabIndex=open?0:-1});
  }
  if(trig){
    trig.setAttribute('aria-haspopup','true');trig.setAttribute('aria-expanded','false');
    if(!trig.getAttribute('aria-label'))trig.setAttribute('aria-label','Accent color');
    trig.onclick=function(){var o=pick.classList.toggle('open');trig.setAttribute('aria-expanded',o?'true':'false');syncSwatchFocus()};
  }
  apply(accents.find(function(a){return a.name===saved})||accents[0]);
  // Re-apply on theme flip so --accent/--shadow track the new theme without the
  // caller having to call reapply() after every fdTheme(). Disconnect a prior
  // observer first so re-initialising the same picker doesn't stack them.
  if(pick._fdObs)pick._fdObs.disconnect();
  pick._fdObs=new MutationObserver(function(){if(current)apply(current)});
  pick._fdObs.observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']});
  // Keep swatch tabindex in sync however the popover closes (outside click,
  // Escape) — those paths only toggle the .open class, not this module's code.
  if(pick._fdOpenObs)pick._fdOpenObs.disconnect();
  pick._fdOpenObs=new MutationObserver(syncSwatchFocus);
  pick._fdOpenObs.observe(pick,{attributes:true,attributeFilter:['class']});
  return {reapply:function(){apply(accents.find(function(a){return a.name===(localStorage.getItem('fd-accent')||accents[0].name)})||accents[0])}};
}

// Pull-to-refresh on a .pull element (structure: .pull > .pull-fill + .pull-label).
// The indicator sits at height:0, so the drag itself is tracked on opts.container
// (default document.body) — wherever the user's finger actually is — not on the
// indicator. opts: { container:document.body, threshold:80 (px pull to arm),
// maxPull:100 (px pull to reach barHeight), barHeight:40 (px bar height revealed),
// labelIdle/labelArmed/labelBusy, shouldStart(e) (return false to ignore a touch,
// e.g. one starting inside a scrollable panel), onRefresh(done) }. onRefresh is
// called on release once armed; it may return a Promise or call the passed done()
// callback — the barber-pole runs until it resolves/done() fires.
function fdPull(el, opts){
  el = typeof el === 'string' ? document.getElementById(el) : el;
  if(!el) return;
  opts = opts || {};
  var container = opts.container || document.body;
  var threshold = opts.threshold || 80, maxPull = opts.maxPull || 100, barHeight = opts.barHeight || 40;
  var labelIdle = opts.labelIdle || 'Pull to refresh', labelArmed = opts.labelArmed || 'Release to refresh', labelBusy = opts.labelBusy || 'Refreshing';
  var label = el.querySelector('.pull-label');
  var startY = 0, pulling = false, busy = false, wasArmed = false;
  function reset(){
    el.style.height = '0';
    el.style.setProperty('--pull', '0');
    el.classList.remove('armed', 'refreshing');
    if(label) label.textContent = '';
  }
  function done(){
    busy = false;
    reset();
  }
  container.addEventListener('touchstart', function(e){
    if(busy) return;
    if(opts.shouldStart && !opts.shouldStart(e)) return;
    startY = e.touches[0].clientY;
    pulling = true;
    wasArmed = false;
    if(label) label.textContent = labelIdle;
  }, { passive: true });
  container.addEventListener('touchmove', function(e){
    if(!pulling) return;
    var dy = e.touches[0].clientY - startY;
    if(dy < 0){ pulling = false; reset(); return; }
    var clamped = Math.min(dy, maxPull);
    el.style.height = (clamped / maxPull * barHeight) + 'px';
    el.style.setProperty('--pull', String(Math.min(dy / threshold, 1)));
    var armed = dy >= threshold;
    el.classList.toggle('armed', armed);
    // Only write the aria-live text on the armed/idle EDGE, not every touchmove —
    // this container is role="status"/aria-live="polite", so rewriting it on
    // every frame of a drag queues a rapid-fire announcement pileup instead of
    // one sensible cue at the threshold crossing.
    if(armed !== wasArmed){ if(label) label.textContent = armed ? labelArmed : labelIdle; wasArmed = armed; }
  }, { passive: true });
  container.addEventListener('touchend', function(){
    if(!pulling) return;
    pulling = false;
    if(el.classList.contains('armed')){
      busy = true;
      el.classList.add('refreshing');
      el.style.height = barHeight + 'px';
      if(label) label.textContent = labelBusy;
      var result = opts.onRefresh && opts.onRefresh(done);
      if(result && typeof result.then === 'function') result.then(done, done);
    } else {
      reset();
    }
  });
  return { reset: reset };
}

// A pressed .btn depresses (moves down on :active); capture the pointer so the click
// still retargets to the button even though it slid out from under the cursor —
// otherwise a press begun on the hovered top edge would release off the button.
document.addEventListener('pointerdown',function(e){
  var b=e.target&&e.target.closest&&e.target.closest('.btn');
  if(b&&e.pointerId!=null&&b.setPointerCapture){try{b.setPointerCapture(e.pointerId)}catch(_){}}
});

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
  if(!e.target||!e.target.closest)return;
  // Custom select: Enter/Space/Down open; Up/Down move; Enter pick; Esc/Tab close.
  var sel=e.target.closest('.sel');
  if(sel){
    var opts=Array.prototype.slice.call(sel.querySelectorAll('.sel-opt'));
    var open=sel.classList.contains('open'),i=opts.indexOf(e.target);
    if(e.key==='ArrowDown'){e.preventDefault();if(!open)fdSelOpen(sel,true);else if(i<opts.length-1)opts[i+1].focus()}
    else if(e.key==='ArrowUp'){e.preventDefault();if(i>0)opts[i-1].focus()}
    else if(e.key==='Enter'||e.key===' '){e.preventDefault();if(!open)fdSelOpen(sel,true);else if(i>-1)fdSel(opts[i])}
    else if(e.key==='Escape'){if(open){e.preventDefault();fdSelOpen(sel,false);var v=sel.querySelector('.sel-val');if(v)v.focus()}}
    else if(e.key==='Tab'){if(open)fdSelOpen(sel,false)}
    return;
  }
  // Tabs: Enter/Space activate the focused tab; Left/Right move + activate.
  // Calls fdTab directly (no reliance on inline onclick indices).
  var tab=e.target.closest('.tab');
  if(tab&&(e.key==='Enter'||e.key===' '||e.key==='ArrowRight'||e.key==='ArrowLeft')){
    var tl=tab.closest('.tabs');if(!tl)return;
    e.preventDefault();
    var tabs=Array.prototype.slice.call(tl.querySelectorAll('.tab')),ti=tabs.indexOf(tab);
    if(e.key==='Enter'||e.key===' '){fdTab(tab,ti)}
    else{var n=e.key==='ArrowRight'?(ti+1)%tabs.length:(ti-1+tabs.length)%tabs.length;fdTab(tabs[n],n);tabs[n].focus()}
    return;
  }
  // Toggle (div role=switch): Enter/Space flips it (native <button> handles itself).
  var tg=e.target.closest('.toggle');
  if(tg&&tg.tagName!=='BUTTON'&&(e.key==='Enter'||e.key===' ')){
    e.preventDefault();tg.classList.toggle('on');tg.setAttribute('aria-checked',tg.classList.contains('on')?'true':'false');return;
  }
  // Escape closes the accent popover or an open drawer and restores focus.
  if(e.key==='Escape'){
    document.querySelectorAll('.accpick.open').forEach(function(p){p.classList.remove('open');var t=p.querySelector('.acctrig');if(t){t.setAttribute('aria-expanded','false');t.focus()}});
    var drawers=document.querySelectorAll('.drawer.drawer-open');
    if(drawers.length){
      drawers.forEach(function(d){
        d.classList.remove('drawer-open');
        fdDrawerSync(d,false);
        fdDrawerFocusables(d).forEach(function(el){el.tabIndex=-1});
      });
      document.body.style.overflow='';
      document.querySelectorAll('.scrim-bg').forEach(function(s){s.style.display='none'});
    }
  }
},false);
