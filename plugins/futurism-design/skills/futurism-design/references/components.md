# Components

Copy-paste markup. All styling comes from `assets/futurism.css`; interactive
parts need the handlers in `assets/futurism.js`. Everything themes automatically
via tokens — no per-component dark variant needed.

## Setup

```html
<link rel="stylesheet" href="futurism.css">
<script src="futurism.js" defer></script>
<!-- light is default; for dark: <html data-theme="dark"> -->
<!-- futurism.js runs fdInit() on load to wire ARIA roles + keyboard on
     .sel/.tabs/.toggle. After injecting components dynamically, call fdInit() again. -->
```

## Theme switch

A 2-state labeled pill; `.act` marks the live segment.

```html
<button class="switch" onclick="flipTheme()" aria-label="Toggle light/dark theme" aria-pressed="false">
  <span class="l act" aria-hidden="true">LIGHT</span><span class="d" aria-hidden="true">DARK</span>
</button>
<script>
function flipTheme(){
  fdTheme();                                       // flip the data-theme attribute
  var dark = document.documentElement.getAttribute('data-theme') === 'dark';
  var sw = document.querySelector('.switch');
  sw.querySelector('.l').classList.toggle('act', !dark);
  sw.querySelector('.d').classList.toggle('act', dark);
  sw.setAttribute('aria-pressed', dark ? 'true' : 'false');
}
</script>
```

`fdTheme()` only flips the theme — the `flipTheme` wrapper moves `.act` to the live
label and updates `aria-pressed`. (Bare `onclick="fdTheme()"` would flip the theme
but leave the pill and pressed-state stale.)

## Nav

```html
<nav class="nav">
  <div class="logo">FUTURISMO<span style="color:var(--accent)">.</span></div>
  <div class="links"><a href="#">WORK</a><a href="#">STUDIO</a><a href="#">CONTACT</a></div>
  <button class="btn btn-primary"><span>START →</span></button>
</nav>
```

## Vertical nav (sidebar)

Items are real `<a>` (or `<button>`) so keyboard + focus work for free. The active
item gets a left accent edge — mark it `aria-current="page"`, **not** `role="tab"`
(these navigate/switch views; they aren't an ARIA tablist).

```html
<nav class="nav-v" aria-label="Sections">
  <a href="#overview" aria-current="page"><svg>…</svg> Overview</a>
  <a href="#dpi"><svg>…</svg> DPI</a>
  <a href="#sensor"><svg>…</svg> Sensor</a>
</nav>
```

For a view-switcher (no real URLs) use `<button>`s and move `aria-current="page"`
to the chosen one in your handler:

```js
nav.querySelectorAll('button').forEach(b => b.onclick = () => {
  nav.querySelectorAll('button').forEach(x => x.removeAttribute('aria-current'));
  b.setAttribute('aria-current', 'page');
  // …show the matching view…
});
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

**`.btn-square`** drops the skew for buttons that sit **flush against a square
element** — an input+action group, one action in a square toolbar — where a skewed
button's slanted edge would leave a wedge gap. Reserve the skewed `.btn` for
standalone CTAs and rows of skewed siblings (confirm+cancel). For an icon action,
`.iconbtn` is already square.

```html
<label for="debounce">Debounce (ms)</label>
<div style="display:flex;gap:10px;align-items:stretch">
  <input id="debounce" type="number" value="4">
  <button class="btn btn-primary btn-square"><span>SET</span></button>
</div>
```

`align-items:stretch` makes the button match the field's height (the button has no
border, so it's 2px shorter otherwise — they wouldn't sit flush top-to-bottom).

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
  <label for="model">Model</label>
  <input id="model" value="opus">
</div>
```

## Input

Always associate the label — `for`/`id` (or wrap the input in the `<label>`) — or the
field has no accessible name ("edit text, blank" to a screen reader).

```html
<label for="fullName">Full name</label>
<input id="fullName" value="Filippo M.">

<label for="debounce">Debounce (ms)</label>
<input id="debounce" type="number" value="4">
```

The native number-input spinner is OS chrome (rounded, OS-themed) and is suppressed,
so the field stays a clean square (law 7). For an on-brand +/− control, use the
**Stepper** instead.

## Custom select (never use native `<select>`)

The `.sel-val` is a div (becomes `role="button"` via `fdInit`), so a `<label>` can't
target it with `for`; name it with `aria-labelledby` pointing at the label's `id`.

```html
<label id="lblDisc">Discipline</label>
<div class="sel">
  <div class="sel-val" aria-labelledby="lblDisc"><span class="sel-cur">Painting</span><i class="caret">›</i></div>
  <div class="sel-list">
    <div class="sel-opt sel-on" onclick="fdSel(this)">Painting</div>
    <div class="sel-opt" onclick="fdSel(this)">Sculpture</div>
    <div class="sel-opt" onclick="fdSel(this)">Architecture</div>
  </div>
</div>
```

Open/close and click-outside are handled by `futurism.js`; `fdSel` sets the value.
The dropdown `.sel-list` is **progressive-enhancement positioned**: the CSS default is
`position:absolute` (self-anchored under the trigger via `top:100%/left:0/right:0`), so
it **works with the stylesheet alone** — no `futurism.js`, or your own select JS — and
is immune to ancestor transforms. When `futurism.js` is loaded, `fdSelOpen` calls
`fdSelPosition` to promote the list to `position:fixed` anchored to the trigger
(left/top/width), flip it above when there's no room below, and reposition on
scroll/resize — letting it float in the **top layer** and **escape an `overflow:auto`
ancestor** (a scrolling `.modal`/`<dialog>`, a card with internal scroll); `fdSelReset`
restores the absolute default on close. Either way the list stays a DOM child of `.sel`,
so ARIA wiring and click-outside work. If you vendor only the CSS, the dropdown is
clipped *only* when it sits inside an overflow ancestor — add the JS to escape it.
Caveat (JS/fixed mode only): `transform`/`filter`/`will-change`/`backdrop-filter` on an
ancestor re-roots the fixed list (breaks anchoring + drops it behind a modal backdrop) —
keep those off a `.sel`'s scrolling/modal ancestors and animate modal entrances with
`opacity`, or just don't load the anchoring JS for that select (absolute is transform-safe).
`fdInit` (auto-runs on load) wires the ARIA roles — the `.sel-val` becomes a
`button` with `aria-haspopup="listbox"`/`aria-controls`, the list a `listbox`, each
option an `option` — so it's keyboard-operable: Enter/Space/↓ open, ↑↓ move, Enter
picks, Esc closes.

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
<dialog id="confirmModal">
  <div class="modal">
    <div class="mhead"><h2>Delete session?</h2></div>
    <div class="mbody"><p>This kills the running process. No undo.</p></div>
    <div class="mfoot">
      <span class="kick">irreversible</span>
      <div class="grp">
        <button class="btn btn-ghost" autofocus onclick="document.getElementById('confirmModal').close()"><span>CANCEL</span></button>
        <button class="btn btn-primary"><span>DELETE →</span></button>
      </div>
    </div>
  </div>
</dialog>
```

(Don't id a dialog `confirm` and call `confirm.close()` — `window.confirm` shadows
the named element, so it throws. Use `getElementById`.)

Open/close with `dialog.showModal()` / `dialog.close()`. Native `<dialog>` traps
Tab and closes on Esc; add `autofocus` to the least-destructive button (e.g.
CANCEL) so focus lands sensibly on open. The `::backdrop` uses `--scrim`. For
non-`<dialog>` cases use `.overlay.open` wrapping the same `.modal`.

## List rows

```html
<!-- Status list: rows are display-only; mark the current one for AT. -->
<ul style="list-style:none;margin:0;padding:0">
  <li class="list-row sel" aria-current="true"><span class="dot"></span><b>Active session</b></li>
  <li class="list-row"><span class="dot dead"></span><b>Idle session</b></li>
</ul>
```

Hover + selected highlights route through a `--row-bg` variable so a JS-set inline
`background:var(--row-bg,transparent)` can't clobber them. Selected uses the
theme-aware `--sel-bg` token plus an inset accent edge (carbon needs a far higher
mix, and the edge carries the cue even where the wash is subtle).

`.list-row` is **display by default** (no pointer cursor). The `.sel` class is
**visual only** — convey state to AT too: `aria-current` for the active item in a
status list, or `aria-selected` in a listbox. If rows are **clickable**, add `.link`
(opt-in pointer) and make each a real `<a>`/`<button>`, or use listbox semantics
(`role="listbox"` on the container, `role="option"` + roving `tabindex` on rows) —
don't ship a bare `<div onclick>`.

## Row action + inline confirm

A per-row destructive action without a modal or native `confirm()`. The action is a
two-step inline confirm wired by `fdConfirm`.

```html
<div class="row-host">
  <div class="list-row sel"><span class="dot"></span><b>manifesto-gt</b></div>
  <span class="row-act" id="rowDel"></span>
</div>
<script>
  fdConfirm('rowDel', {
    label: 'Delete', cancel: 'Cancel',
    icon: '<svg …trash…></svg>',
    onConfirm: () => fetch('/x', {method:'DELETE'}).then(r => { if(!r.ok) throw 0; /* re-render */ }),
  });
</script>
```

`fdConfirm` builds the idle trash button, arms on click (accent **Delete** + ghost
**Cancel**), moves focus to the safe Cancel, cancels on Esc (focus returns to the
trigger), and flashes `.failed` then reverts if `onConfirm` rejects. On success it
reverts to idle and refocuses the trigger if the row is still there; if `onConfirm`
removed the row, pass `onDone` to hand focus to a stable target (next row / list)
so focus isn't orphaned on the detached node.

Three gotchas it handles for you (and you must respect when extending):
- **No button-in-button.** A control can't nest inside a row that is itself a
  `<button>`; the `.row-act` slot is a sibling of `.list-row` inside `.row-host`
  (`position:relative`), and the slot is a *container*, not a button, so its
  Delete/Cancel buttons don't nest either.
- **Inset over the divider.** The absolute action would cover the row's bottom
  border; it's inset `top/bottom:2px` so the divider still reads.
- **Always-visible-muted, not hover-revealed** — a per-row destructive action that
  only appears on hover is undiscoverable; it sits muted at rest, accent on hover/focus.

Touch note: the inline confirm is compact (dense rows). For touch-primary contexts
prefer the `<dialog>` modal confirm, which has full-size targets.

### Row action on a taller/multi-line row

The default `.row-act` insets `top/bottom:2px`, which only reads right against a
single-line `.list-row`. Stretched to a taller two-line row, the action grows
chunky. Add `.centered` to center a fixed-height strip instead — it's opt-in, so
plain single-line usage is unaffected:

```html
<div class="row-host">
  <div class="list-row sel" style="flex-direction:column;align-items:flex-start;padding:10px 14px">
    <b>manifesto-gt</b>
    <span class="kick" style="margin-left:0">started 2h ago</span>
  </div>
  <span class="row-act centered" id="rowDel" style="--row-act-h:28px"></span>
</div>
<script>fdConfirm('rowDel', { label: 'Delete', cancel: 'Cancel', onConfirm: () => fetch('/x', {method:'DELETE'}) });</script>
```

`.centered` sets `top:50%;bottom:auto;transform:translateY(-50%)` and drives its
height from `--row-act-h` (falls back to `32px`) — set that custom property per use
case rather than hard-coding a height in the kit. Everything else (`fdConfirm`, the
three gotchas above) is unchanged.

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
accent (`--shadow` = accent); in light it stays ink. Theme flips are handled
automatically (an observer re-applies the right light/dark variant); the returned
`.reapply()` is kept for manual use but is no longer required.

## Off-canvas drawer

```html
<button class="iconbtn" aria-controls="nav" aria-expanded="false" onclick="fdDrawer('nav','navScrim')">☰</button>
<aside class="drawer" id="nav">…</aside>
<div class="scrim-bg" id="navScrim" style="display:none" onclick="fdDrawer('nav','navScrim')"></div>
```

`fdDrawer` slides the panel in/out and shows/hides the scrim; Escape closes any open
drawer. It also keeps the trigger's `aria-expanded` in sync (when present) and
restores focus to the opener on close — same as the accent popover. On desktop, make the panel static at your breakpoint (see the Responsive &
touch section in SKILL.md). (Escape closes *all* open drawers/scrims — fine for the
usual single drawer; pages with several simultaneous drawers need their own handling.)

## Toggle

```html
<div class="toggle on"><i></i></div>
```

`futurism.js` flips `.on` on click. Read state via `.classList.contains('on')`.
`fdInit` makes it `role="switch"`, focusable, and Space/Enter-operable; add an
`aria-label` so its purpose is announced. (Or use a native `<button class="toggle">`.)

## Cards

```html
<div class="card">
  <span class="badge red">001</span>
  <h3>Dynamism</h3>
  <p>Static display card — does not move on hover.</p>
  <a href="#">Open<span class="arr"> →</span></a>
</div>

<!-- Whole card is a control → .link adds cursor + the hover-lunge.
     Use a REAL <a>/<button> so it's keyboard-operable + focus-ringed for free. -->
<button class="card link" onclick="…">…</button>
<a class="card link" href="…">…</a>
```

The hover-lunge (translate + deeper offset shadow) is **opt-in via `.card.link`** —
add it only when the entire card is clickable, so static cards don't move under the
cursor. A card with just an inner link/button stays plain `.card`. Put `.link` on a
real `<a>`/`<button>` (not a bare `<div onclick>`, which is keyboard-unreachable) —
`a.card`/`button.card` are normalized to lay out like a div card, and `.card.link`
gets a `:focus-visible` ring.

## Stepper

A −/value/+ numeric control. The value is a native `<input type="number">` (an implicit
spinbutton — the user can **type** a value, use ↑/↓ to step, and it clamps to
`min`/`max`/`step`), welded between the −/+ buttons. `fdInit` wires the buttons to
`stepUp`/`stepDown` the input and re-clamps on change, so it needs no inline handlers.
The `+`/`−` buttons carry `tabindex="-1"` (the input is the single tab stop and its
native arrow keys do the stepping); give the input an `aria-label`. The OS spinner is
already suppressed by the kit's `input[type=number]` rule.

```html
<div class="stepper">
  <button type="button" class="step-dn" aria-label="Decrease DPI" tabindex="-1">−</button>
  <input class="num" type="number" min="50" max="26000" step="50" value="6400" aria-label="DPI">
  <button type="button" class="step-up" aria-label="Increase DPI" tabindex="-1">+</button>
</div>
```

Use a stepper when the user needs both quick ±nudges **and** direct entry (any range).
For a pure ±1 toggle with a tiny range, `.seg` or a plain number field also work.

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

`fdInit` wires `role="tablist"/"tab"/"tabpanel"` + roving tabindex; ←/→ move and
activate the focused tab.

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
<div class="seg" role="group" aria-label="View">
  <button class="on" aria-pressed="true">LIST</button>
  <button aria-pressed="false">GRID</button>
  <button aria-pressed="false">MAP</button>
</div>
```

Toggle `.on` + `aria-pressed` in JS. Real `<button>`s, so they're keyboard-reachable;
`role="group"` + `aria-pressed` announce it as a single-choice set.

## Pagination

```html
<nav class="pager" aria-label="Pagination">
  <button disabled aria-label="Previous">‹</button>
  <button class="on" aria-current="page">1</button>
  <button>2</button>
  <button>3</button>
  <button aria-label="Next">›</button>
</nav>
```

Welded square cells; current page fills ink (matches `.seg`/`.tab` — accent stays
the live/attention role) and carries `aria-current="page"`; disabled prev/next go `--muted`.

## Breadcrumb

```html
<nav class="crumb" aria-label="Breadcrumb">
  <a href="#">GARAGE</a><span class="sep">›</span>
  <a href="#">TIPO 1909</a><span class="sep">›</span>
  <span class="cur" aria-current="page">ENGINE</span>
</nav>
```

Links carry the same darting accent underline as the nav on hover.

## Tooltip

```html
<span class="tip" data-tip="Delete">
  <button class="iconbtn danger" aria-label="Delete">…</button>
</span>
```

`data-tip` on the wrapper; an ink box darts down toward the trigger on hover/focus.
No arrow (a pointy triangle fights the square grid) — a butt-joined block. The
tooltip is **visual only** (CSS `::after` isn't in the accessibility tree), so the
control inside must carry its own `aria-label` — don't rely on the tip for the name.

## Toast

```html
<button class="btn btn-primary" onclick="fdToast('Saved')"><span>SAVE</span></button>
<button class="btn btn-ghost" onclick="fdToast('Upload failed',{type:'err'})"><span>FAIL</span></button>
```

`fdToast(msg, {type, timeout})` darts a card in from the bottom-right and slides it
out — never fades. **Default is neutral** (line border + accent left-rule);
`{type:'err'}` raises the full accent border for errors/attention. Success rides on
the label, not a green (law 4). `timeout` ms before auto-dismiss (default 3200).

## Pull to refresh

A touch-driven refresh affordance: a square accent bar fills as the user pulls down
from the top of the page, then marches the kit barber-pole (reusing `fd-march`, the
same recipe as `.skel` — never a rotary spinner) while the refresh is in flight.

```html
<div class="pull" role="status" aria-live="polite">
  <div class="pull-fill"></div><span class="pull-label"></span>
</div>
<script>
  fdPull(document.querySelector('.pull'), {
    onRefresh: () => fetch('/api/data').then(r => r.json()).then(renderData),
  });
</script>
```

Single instance per page (like `.toaster`) — one `.pull` element sits at the top of
the scrolling area at `height:0` and only grows while dragged. `fdPull(el, opts)`
tracks the gesture on `opts.container` (default `document.body`, since the
zero-height indicator itself can never receive the touch that starts the drag), and
toggles `.armed`/`.refreshing` on `el` as the pull crosses `opts.threshold` and then
releases. `opts.onRefresh(done)` fires on release once armed — return a `Promise` or
call `done()` when the refresh completes, and the barber-pole keeps marching until
then. `opts.shouldStart(e)` can veto a touch that starts inside a scrollable child
(a terminal, a panel, an open dialog) so the gesture doesn't fight nested scrolling.

`role="status"`/`aria-live="polite"` are on the container per the kit's "state that
changes without focus moving" rule (match `.toast`). Once the accent fill is behind
the label, the label flips to `--on-accent` — the exact case the kit's "partial
fill" theming rule exists for (see SKILL.md Theming). The live-drag fill uses
`transition:width 60ms linear`, a narrow, documented exception to law #5's `--ease`
requirement (see SKILL.md law 5) — a value tracked 1:1 to a finger every frame isn't
a discrete state transition, and the standard easing visibly lags a fast drag.

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
