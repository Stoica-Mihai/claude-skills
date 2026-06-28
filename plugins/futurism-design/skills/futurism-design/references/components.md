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

States stay inside the one-red palette: `.saving` marches diagonal stripes (the
`.prog` machine motion — not an opacity pulse) and blocks clicks; `.ok` fills ink
(done/committed); `.err` reuses the accent. Convey success with the label
("SAVED ✓"), not a second hue.

## Icon button

```html
<button class="iconbtn" aria-label="Edit">
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
       stroke-linecap="square" stroke-linejoin="miter">
    <path d="M4 20h4L20 8l-4-4L4 16v4z"/><path d="M14 6l4 4"/>
  </svg>
</button>
```

Square, token-themed. Use **inline stroke SVG in `currentColor`** for the glyph —
never emoji. Emoji carry their own color (breaks the one-red law) and rounded,
soft shapes (breaks the square/flat look); a `currentColor` SVG inherits ink and
flips to `--bg` on hover for free. Keep `stroke-linecap:square` /
`stroke-linejoin:miter` so the icon's corners match the 2px-border hardness.
Native `<button>` doesn't inherit text color, so `.iconbtn` sets `color`
explicitly — keep that when extending.

## Keycap

```html
<span class="keycap">ESC</span>
<!-- chord: caps welded into one block by .combo (shared divider, no + symbol) -->
<span class="combo"><span class="keycap">⌘</span><span class="keycap">K</span></span>
```

Plain monospace text reads as machined. For a shortcut, weld the caps with
`.combo` — they butt into one block sharing a single 2px divider, so they read as
pressed-together without a generic `+`. A standalone key stays apart via the row
gap. Don't cram a chord into one cap (`⌘K`).

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
<div class="sel-opt" data-value="spec-gp" onclick="fdSel(this)">Grand Prix</div>
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
<div class="list-row sel"><span class="dot"></span><b>Active session</b></div>
<div class="list-row"><span class="dot dead"></span><b>Idle session</b></div>
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
<div class="alert">
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
       stroke-linecap="square" stroke-linejoin="miter"><path d="M12 3L1 21h22L12 3z"/><path d="M12 10v5M12 18v.01"/></svg>
  Engine at redline. Reduce load.
</div>
<div class="alert info">
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
       stroke-linecap="square" stroke-linejoin="miter"><rect x="3" y="3" width="18" height="18"/><path d="M12 11v6M12 7v.01"/></svg>
  Build deployed in 0.8s.
</div>
```

Lead with a `currentColor` stroke SVG, not an emoji — it inherits the alert's
border color and themes for free.

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

## Checkbox & radio

Styled **native** inputs, so keyboard + a11y work with no JS. Both are squares
(circles break law 1): checkbox fills accent with a check, radio shows an inset
accent block.

```html
<label style="display:flex;align-items:center;gap:8px">
  <input type="checkbox" class="check" checked> Telemetry
</label>
<label style="display:flex;align-items:center;gap:8px">
  <input type="radio" name="mode" class="radio" checked> Track
</label>
<label style="display:flex;align-items:center;gap:8px">
  <input type="radio" name="mode" class="radio"> Street
</label>
```

## Segmented control

Welded buttons (the `.combo` idiom); active fills ink. For a few visible options
where tabs are too heavy and a select is overkill.

```html
<div class="seg">
  <button class="on">LIST</button>
  <button>GRID</button>
  <button>MAP</button>
</div>
```

Toggle `.on` in JS. Real `<button>`s, so they're keyboard-reachable.

## Pagination

```html
<div class="pager">
  <button disabled aria-label="Previous">‹</button>
  <button class="on">1</button>
  <button>2</button>
  <button>3</button>
  <button aria-label="Next">›</button>
</div>
```

Welded square cells; current page fills accent, disabled prev/next go `--muted`.

## Breadcrumb

```html
<nav class="crumb">
  <a href="#">GARAGE</a><span class="sep">›</span>
  <a href="#">TIPO 1909</a><span class="sep">›</span>
  <span class="cur">ENGINE</span>
</nav>
```

## Tooltip

```html
<span class="tip" data-tip="Delete" tabindex="0">
  <button class="iconbtn danger">…</button>
</span>
```

`data-tip` on the wrapper; an ink box darts up on hover/focus. No arrow (a pointy
triangle fights the square grid) — a butt-joined block.

## Toast

```html
<button class="btn btn-primary" onclick="fdToast('Saved',{type:'info'})"><span>SAVE</span></button>
<button class="btn btn-ghost" onclick="fdToast('Upload failed',{type:'err'})"><span>FAIL</span></button>
```

`fdToast(msg, {type:'info'|'err', timeout})` darts a card in from the bottom-right
and slides it out — never fades. Error/attention = accent border (default), neutral
= `info`. Success rides on the label, not a green (law 4).

## Empty state

```html
<div class="empty">
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
       stroke-linecap="square" stroke-linejoin="miter"><rect x="3" y="3" width="18" height="18"/><path d="M3 9h18"/></svg>
  <h2>NOTHING HERE YET</h2>
  <p>Spin up your first session to see it land.</p>
  <button class="btn btn-primary"><span>NEW SESSION →</span></button>
</div>
```

A composed pattern (no new chrome): a large `currentColor` glyph, a 900-italic
headline, calm body, one skewed CTA.

## Skeleton

```html
<div class="skel" style="width:60%"></div>
<div class="skel" style="width:90%;margin-top:8px"></div>
```

Content-shaped placeholder; reuses the marching `fd-march` stripe (a spinner would
be rotary, off-brand). Size with inline `width`/`height`.
