# Components

Copy-paste markup. All styling comes from `assets/futurism.css`; interactive
parts need the handlers in `assets/futurism.js`. Everything themes automatically
via tokens — no per-component dark variant needed.

## Setup

```html
<link rel="stylesheet" href="futurism.css">
<script src="futurism.js" defer></script>
<!-- light is default; for dark: <html data-theme="dark"> -->
```

## Theme switch

```html
<div class="switch" onclick="fdTheme()">LIGHT / DARK</div>
```

## Nav

```html
<nav class="nav">
  <div class="logo">FUTURISMO<span style="color:var(--accent)">.</span></div>
  <div class="links"><a href="#">WORK</a><a href="#">STUDIO</a><a href="#">CONTACT</a></div>
  <button class="btn btn-primary"><span>START →</span></button>
</nav>
```

## Type

```html
<div class="kick">MANIFESTO · 1909</div>
<h1>SPEED IS BEAUTY</h1>
<h2>Section heading</h2>
<h3>Subsection heading</h3>
<p>Body stays calm and legible. Drama lives in display type and the single red,
  not the paragraph. Inline <a href="#">links dart<span class="arr"> →</span></a>.</p>
<blockquote>Motion is the only truth.</blockquote>
```

## Buttons & badges

```html
<button class="btn btn-primary"><span>PRIMARY →</span></button>
<button class="btn btn-ink"><span>INK</span></button>
<button class="btn btn-ghost"><span>GHOST</span></button>

<span class="badge red">NEW</span>
<span class="badge">DEFAULT</span>
<span class="badge out">OUTLINE</span>
```

Always wrap button labels in `<span>` — the outer `.btn` skews, the inner span
counter-skews to keep text upright.

### Button states

```html
<button class="btn btn-primary saving"><span>SAVING…</span></button>
<button class="btn ok"><span>SAVED ✓</span></button>
<button class="btn err"><span>FAILED</span></button>
```

`.saving` pulses and blocks clicks; `.ok` is the one allowed non-accent hue
(green = system state, not brand); `.err` reuses the accent.

## Icon button

```html
<button class="iconbtn"><span>✎</span></button>
<button class="iconbtn danger" aria-label="Delete">✕</button>
```

Square, token-themed. Native `<button>` doesn't inherit text color, so `.iconbtn`
sets `color` explicitly — keep that when extending.

## Keycap

```html
<span class="keycap">⌘K</span>
```

## Status dot

```html
<span class="dot"></span>        <!-- live: pulses -->
<span class="dot dead"></span>   <!-- idle: muted, still -->
```

## Form row

```html
<div class="form-row">
  <label>Model</label>
  <input value="opus">
</div>
```

## Input

```html
<label>Full name</label>
<input value="Filippo M.">
```

## Custom select (never use native `<select>`)

```html
<label>Discipline</label>
<div class="sel">
  <div class="sel-val"><span class="sel-cur">Painting</span><i class="caret">›</i></div>
  <div class="sel-list">
    <div class="sel-opt sel-on" onclick="fdSel(this)">Painting</div>
    <div class="sel-opt" onclick="fdSel(this)">Sculpture</div>
    <div class="sel-opt" onclick="fdSel(this)">Architecture</div>
  </div>
</div>
```

Open/close and click-outside are handled by `futurism.js`; `fdSel` sets the value.

When the displayed label differs from the stored value, add `data-value` — the
option shows its text but `fdSel` stores `data-value`. Read it with `fdSelVal(sel)`
(or `sel.dataset.value`):

```html
<div class="sel-opt" data-value="claude-opus-4-8" onclick="fdSel(this)">Opus 4.8</div>
```

## Modal

Prefer native `<dialog>` — the shell stays transparent, the `.modal` box carries
the chrome. `<dialog>` is `overflow:visible` so the offset shadow isn't clipped;
tall content scrolls inside `.modal`.

```html
<dialog id="confirm">
  <div class="modal">
    <div class="mhead"><h2>Delete session?</h2></div>
    <div class="mbody"><p>This kills the running process. No undo.</p></div>
    <div class="mfoot">
      <span class="kick">irreversible</span>
      <div class="grp">
        <button class="btn btn-ghost" onclick="confirm.close()"><span>CANCEL</span></button>
        <button class="btn btn-primary"><span>DELETE →</span></button>
      </div>
    </div>
  </div>
</dialog>
```

Open/close with `dialog.showModal()` / `dialog.close()`. The `::backdrop` uses
`--scrim`. For non-`<dialog>` cases use `.overlay.open` wrapping the same `.modal`.

## List rows

```html
<div class="row sel"><span class="dot"></span><b>Active session</b></div>
<div class="row"><span class="dot dead"></span><b>Idle session</b></div>
```

Hover + selected highlights route through a `--row-bg` variable so a JS-set inline
`background:var(--row-bg,transparent)` can't clobber them. Selected sits at 30%
mix — below ~30% it's nearly invisible on the carbon theme.

## Accent picker

```html
<div class="accpick" id="accpick">
  <button class="acctrig" aria-label="Accent color"></button>
  <div class="accpop"></div>
</div>
<script>
  fdAccent('accpick', [
    {name:'Red',   light:'#d22f1a', dark:'#ff4d33'},
    {name:'Cyan',  light:'#0a8f86', dark:'#2ee6d6'},
    {name:'Violet',light:'#7a3fd6', dark:'#b06bff'},
  ]);
</script>
```

Swaps `--accent` at runtime and persists it. In dark the offset shadow follows the
accent (`--shadow` = accent); in light it stays ink. Re-call the returned
`.reapply()` after a theme flip so the right light/dark variant is used.

## Off-canvas drawer

```html
<aside class="drawer" id="nav">…</aside>
<div class="scrim-bg" id="navScrim" style="display:none" onclick="fdDrawer('nav','navScrim')"></div>
<button class="iconbtn" onclick="fdDrawer('nav','navScrim')">☰</button>
```

`fdDrawer` slides the panel in/out and shows/hides the scrim. On desktop, make the
panel static at your breakpoint (see the Responsive & touch section in SKILL.md).

## Toggle

```html
<div class="toggle on"><i></i></div>
```

`futurism.js` flips `.on` on click. Read state via `.classList.contains('on')`.

## Cards

```html
<div class="card">
  <span class="badge red">001</span>
  <h3>Dynamism</h3>
  <p>Hover lunges up-left; the solid shadow stretches.</p>
  <a href="#">Open<span class="arr"> →</span></a>
</div>
```

## Tabs

```html
<div class="tabs" data-tabs>
  <div class="tab on" onclick="fdTab(this,0)">Overview</div>
  <div class="tab" onclick="fdTab(this,1)">Specs</div>
  <div class="tab" onclick="fdTab(this,2)">Press</div>
</div>
<div class="panel on">Overview content.</div>
<div class="panel">Specs content.</div>
<div class="panel">Press content.</div>
```

## Alerts

```html
<div class="alert">⚠ Engine at redline. Reduce load.</div>
<div class="alert info">ℹ Build deployed in 0.8s.</div>
```

## Progress

```html
<div class="prog"><i style="width:62%"></i></div>
```

## Table

```html
<table>
  <thead><tr><th>Model</th><th>0–100</th><th>Top</th></tr></thead>
  <tbody>
    <tr><td>Tipo 1909</td><td>3.2s</td><td>305</td></tr>
    <tr><td>Manifesto GT</td><td>2.8s</td><td>331</td></tr>
  </tbody>
</table>
```
