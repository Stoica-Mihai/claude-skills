# Tokens

Single source of truth is `assets/futurism.css`. These tables mirror it for quick
reference. If you change a value, change it in the CSS — not just here.

## Color

| token | role | light | dark |
|---|---|---|---|
| `--bg` | page ground | `#efe9dc` | `#16140f` |
| `--surf` | raised surface (cards, lists) | `#f7f3ea` | `#211d16` |
| `--ink` | display + heavy text, borders | `#1a1714` | `#efe9dc` |
| `--muted` | body / secondary text | `#4a4339` | `#a89f8e` |
| `--accent` | the one red — links, CTAs, rules | `#d22f1a` | `#ff4d33` |
| `--line` | border color | `#1a1714` | `#efe9dc` |
| `--shadow` | solid offset shadow color | `#1a1714` | `#ff4d33` |
| `--field` | input / control fill | `#f7f3ea` | `#211d16` |
| `--on-accent` | text/icon on an accent fill | `#efe9dc` | `#16140f` |
| `--scrim` | overlay / backdrop dim | `rgba(0,0,0,.55)` | *(same — theme-independent)* |

Light is default. Dark activates via `[data-theme="dark"]` on the root.

`--scrim` is deliberately the **same in both themes** — overlays must dim, not
tint. Never reach for `--ink` on a backdrop: ink is the cream foreground in dark,
so an ink scrim would *lighten* the page instead of dimming it.

## Type

| token / rule | value |
|---|---|
| `--font` | `'Helvetica Neue', Arial, sans-serif` |
| `--mono` | `'SFMono-Regular', ui-monospace, Menlo, Consolas, monospace` (keycaps, data, code) |
| display (h1/h2) | weight 900, italic, letter-spacing −1 to −2px, line-height .86–.9 |
| h3 | weight 900, italic, letter-spacing −.5px |
| body `p` | 15px, line-height 1.55, color `--muted` |
| `.kick` / labels | 11px, uppercase, letter-spacing 2–4px, weight 700 |

## Motion

| token | value | use |
|---|---|---|
| `--fast` | `.12s` | hovers, presses, toggles, opens |
| `--med` | `.2s` | theme flips, panel slides, progress width |
| `--ease` | `cubic-bezier(.2,.9,.1,1)` | all transitions |

Motion is always directional (translate/slide/scaleY/march), never opacity-only
fades or springy bounces. `prefers-reduced-motion: reduce` disables all of it.

## Shape & spacing

| token | value |
|---|---|
| `--border` | `2px` — standard control/surface border (primary dividers stay a literal 3px: nav, table head, tabs) |
| `--shadow-off` | `6px` (grows to 9px on card hover) |
| corner radius | `0` — always |

## CSS source blocks

```css
:root{
  --bg:#efe9dc; --surf:#f7f3ea; --ink:#1a1714; --muted:#4a4339;
  --accent:#d22f1a; --line:#1a1714; --shadow:#1a1714; --field:#f7f3ea; --on-accent:#efe9dc;
  --ease:cubic-bezier(.2,.9,.1,1); --fast:.12s; --med:.2s;
  --border:2px; --shadow-off:6px;
  --font:'Helvetica Neue',Arial,sans-serif;
  --mono:'SFMono-Regular',ui-monospace,Menlo,Consolas,monospace;
  --scrim:rgba(0,0,0,.55);
  --hover-bg:color-mix(in srgb,var(--accent) 14%,var(--surf));
  --sel-bg:color-mix(in srgb,var(--accent) 26%,var(--surf));
  --tint:color-mix(in srgb,var(--accent) 12%,var(--bg));
  --skel-stripe:color-mix(in srgb,var(--accent) 22%,transparent);
}
[data-theme="dark"]{
  --bg:#16140f; --surf:#211d16; --ink:#efe9dc; --muted:#a89f8e;
  --accent:#ff4d33; --line:#efe9dc; --shadow:#ff4d33; --field:#211d16; --on-accent:#16140f;
  --hover-bg:color-mix(in srgb,var(--accent) 20%,var(--surf));
  --sel-bg:color-mix(in srgb,var(--accent) 26%,var(--surf));
  --tint:color-mix(in srgb,var(--accent) 36%,var(--bg));
  --skel-stripe:color-mix(in srgb,var(--accent) 45%,transparent);
}
```

State washes (`--hover-bg`, `--sel-bg`, `--tint`, `--skel-stripe`) are **theme-aware**,
but not uniformly so — `--tint`/`--skel-stripe` do need much higher mixes in dark to
stay visible against the near-black base. `--hover-bg`/`--sel-bg` are only modestly
higher in dark (and `--sel-bg` is identical in both themes): selection there leans on
the inset accent edge to carry the cue, not the wash alone, so the wash's own gap
matters less. Match the actual `:root`/`[data-theme="dark"]` values in `futurism.css`
if you're re-deriving these — don't assume a uniform "dark needs much higher %" rule
across all four.
