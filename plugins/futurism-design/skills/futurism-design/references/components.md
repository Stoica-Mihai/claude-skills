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
