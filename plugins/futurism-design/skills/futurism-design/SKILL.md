---
name: futurism-design
description: >
  Apply the Futurism Design System — a Paper-Futurist web aesthetic (bold italic
  display type, a single red accent, square corners, solid offset shadows, and
  fast directional motion) with paired light and dark themes. Use this skill
  whenever the user asks to build, style, or restyle any web UI — a page,
  component, landing hero, dashboard, form, or full app — AND wants it to follow
  the Futurism look, OR invokes /futurism-design, OR references "futurism",
  "futurist", "paper futurism", "the red/cream design", or "our design system"
  in this repo. Trigger it even when the user only says "make a page" or "build a
  component" in a project that has adopted this system, so the output stays
  on-brand instead of defaulting to generic styling. This is an explicit,
  web-only design language — do not use it for terminal/CLI output.
---

# Futurism Design System

A web design language: **Italian-Futurist energy, restrained editorial execution.**
Motion, diagonals, one red, bold italic display — on warm paper (light) or warm
carbon (dark).

Use this skill to produce UI that obeys the system instead of generic AI styling.
The look is fully specified; your job is to apply it faithfully.

## How to apply

1. **Reuse the stylesheet — do not re-derive it.** The complete kit lives in
   `assets/futurism.css`. Link or inline it; never hand-rewrite the tokens or
   component CSS. Behaviour for interactive parts is in `assets/futurism.js`.
2. For a single self-contained file (artifact, demo), inline both assets.
3. For a project, copy `assets/futurism.css` + `assets/futurism.js` in and
   import them once at the root.
4. When you need exact values or component markup, read the references:
   - `references/tokens.md` — color/spacing/type/motion tokens + the `:root`
     and `[data-theme="dark"]` blocks.
   - `references/components.md` — copy-paste HTML for every component, with the
     classes and the small JS hooks they need.
5. Default theme is **light**. Enable dark by setting `data-theme="dark"` on the
   root element (`<html>`); call `fdTheme()` to flip it.

## The eight laws

These are what make output read as *this* system rather than a red-tinted
generic site. Break one and the aesthetic collapses, so hold them unless the
user explicitly overrides:

1. **Square corners always.** `border-radius: 0`. The system has no rounding —
   the tension between hard rectangles and skewed type is the point.
2. **Solid offset shadows, never blur.** `box-shadow: 6px 6px 0 var(--shadow)`.
   A blurred shadow instantly reads as Material/SaaS, not Futurism.
   *Gotcha 1:* the offset shadow is **clipped by any `overflow:auto/hidden`
   ancestor**. Keep the shadowed element's scroll container at `overflow:visible`
   and move the scroll inward (this is why the modal sets `dialog{overflow:visible}`
   and scrolls inside `.modal`).
   *Gotcha 2:* in dark, `--shadow` follows the accent, so an **accent-filled control
   must throw an ink shadow, not `--shadow`** — an accent shadow under an accent fill
   is the same hue and smears into one blob. Surfaces (cards/modals on `--surf`) are
   fine with `--shadow`; only same-hue fills need the override (see `.btn-primary:hover`).
3. **2px ink borders** on surfaces and controls — structure is drawn, not
   implied by elevation.
4. **One accent only.** Red (`--accent`) carries links, CTAs, rules, highlights.
   Adding a second hue dilutes the manifesto. If you need differentiation, use
   ink vs. red vs. outline, not new colors. To show a **scale or ordinal range**
   (DPI low→high, weak→strong), use a single-hue **intensity ramp**
   (`linear-gradient(90deg, var(--muted), var(--accent))`) — never a rainbow
   blue→red gradient or a set of multi-hue swatches. And don't hand-roll
   multi-color "category" chips: a single-select set is `.seg`, a static tag is
   `.badge.out`.
5. **Motion is machine, not toy.** Fast (`--fast: .12s`), medium (`--med: .2s`),
   easing `cubic-bezier(.2,.9,.1,1)`, and always **directional** — things slide,
   dart, lurch, march. Never spring, bounce, or fade-puff. Respect
   `prefers-reduced-motion` (the CSS already does).
   *Narrow carve-out:* `--ease` is for **discrete state transitions** (open/close,
   hover, armed/refreshing). A value **live-tracked to a pointer every frame** — not
   a state transition — is exempt: `.pull-fill`'s width uses `transition:width 60ms
   linear` because a cubic-bezier visibly lags a 1:1 finger-tracked drag. Don't
   generalize this to anything that isn't following a pointer in real time.
6. **Skewed CTAs.** Primary actions use `transform: skewX(-8deg)` with the label
   counter-skewed (`skewX(8deg)`) so it stays upright. This is the speed cue.
   *Reserve the skew for standalone/hero CTAs and rows of skewed siblings* (a
   confirm+cancel pair, a button group) — there the parallel slants read as
   deliberate. A lone skewed button sitting **flush against a square element** (an
   input+action group, one action in a square toolbar) makes an awkward wedge gap
   against the straight edge: use a **square affordance** there — `.btn-square`
   (un-skewed `.btn`), `.iconbtn`, or a welded group — so edges align.
7. **Never trust native form popups.** `<select>`, date pickers, etc. render with
   OS chrome that ignores the system. Use the custom `.sel` component (and the
   same approach for any other native popup) so the whole control is on-brand.
   Its dropdown uses **progressive enhancement**: the CSS default is
   `position:absolute`, self-anchored under the trigger, so it **works with the
   stylesheet alone** (no JS, or your own select JS) and is immune to ancestor
   transforms. When `futurism.js` is loaded, `fdSelPosition()` promotes it to
   `position:fixed` anchored to the trigger, so it **escapes a scrolling
   `overflow:auto` ancestor** (modal/`<dialog>`, card with internal scroll) and
   flips up near a bottom edge. So: vendor only the CSS → a working (absolute)
   dropdown that's clipped only inside an overflow ancestor; add the JS → the
   top-layer escape too. Any custom popup you build for a native-popup replacement
   should follow the same pattern (a CSS default that stands alone).
   *Gotcha (JS/fixed mode only):* a `position:fixed` element is re-rooted by any
   ancestor with `transform`, `filter`, `perspective`, `will-change`, `contain`, or
   `backdrop-filter` — that ancestor becomes its containing block, breaking the
   anchoring and dropping it behind a modal backdrop in Chromium. Either keep those
   off a scrolling/modal ancestor of a `.sel` (animate modal entrance with
   **`opacity`**, not `transform`), or simply **don't load the anchoring JS for that
   select** — the absolute default is transform-safe.
8. **Theme native `<button>` explicitly.** Buttons don't inherit `color` — the UA
   gives them `ButtonText` (dark), which becomes dark-on-dark in the carbon theme,
   and an inline `background` beats class rules. So every button must set its
   `color`/`background` from tokens; never rely on inheritance. The kit's
   `button{}` reset and each `.btn`/`.iconbtn` variant already do this — match it
   when you add a new button-like control.

## Type discipline

- One family: `'Helvetica Neue', Arial, sans-serif` (the `--font` token).
- **Display/headings carry the drama**: weight 900, italic, negative tracking,
  tight line-height. **Body stays calm**: regular weight, line-height 1.55,
  `--muted` color, comfortable size. Do not make body text italic or heavy.
- Kickers/labels: 11px, uppercase, wide letter-spacing, in accent or ink.

## Iconography

Icons are **inline stroke SVG in `currentColor`**, never emoji. Emoji bring their
own color (breaks law 4's one-red) and soft rounded shapes (breaks the square,
flat look), and they won't theme. A `currentColor` SVG inherits the token color
and flips on hover for free. Keep `stroke-linecap:square` /
`stroke-linejoin:miter` so the icon's corners match the 2px-border hardness.
Monospace text glyphs (keycaps, arrows like `→`) are fine — they're machined, not
pictorial.

## Theming

Every component is built on CSS variables, so light/dark is a single attribute
flip — no per-component dark overrides. When adding a new component, express all
colors as the existing tokens (`--bg`, `--surf`, `--ink`, `--muted`, `--accent`,
`--line`, `--shadow`, `--field`, `--on-accent`, `--scrim`) and it will theme for
free. If a value can't be expressed in tokens, add a new token to both theme
blocks rather than hard-coding a hex.

**Text on an accent fill is `--on-accent`, never `--ink`.** Any text or icon sitting
on a `var(--accent)` background uses `color:var(--on-accent)` — its paired foreground
in each theme (cream-on-red in light, near-black-on-red in dark). `--ink` is the
*opposite* in both themes, so an ink label on an accent fill is the wrong, low-contrast
foreground. Every accent-filled control already does this (`.btn-primary`, `.badge.red`,
`.sel-opt:hover`, the skewed header mark); match it. This also applies to a *partial*
fill — if an accent bar grows under a centered label (a progress/pull indicator), the
label must flip to `--on-accent` once the fill is behind it.

**Overlays use `--scrim`, never `--ink`.** Backdrops must *dim*, so they need a
theme-independent dark wash. `--ink` is the cream foreground in dark — an ink
backdrop would lighten the page. `--scrim` (`rgba(0,0,0,.55)`) is the same in both
themes for exactly this reason.

**Runtime accent.** Law #4 is one accent, but letting the *user* pick that one
accent is on-system — see the `.accpick` component and `fdAccent()`. Three couplings
to respect: in dark the offset shadow follows the accent (`--shadow` = accent),
in light it stays ink; `fdAccent()` also **re-derives `--on-accent`** from the picked
color's luminance (choosing the kit's cream or near-black, whichever contrasts) so
text/icons on an accent fill stay legible for *any* accent — for the shipped red this
reproduces the static tokens, and an accent entry can override with `onLight`/`onDark`;
and a **theme control** (the `.switch` pill or a `.toggle`)
must use **ink** for its active/`.on` state, not accent — otherwise the control that
*picks* the accent visibly absorbs it. (`.switch .act` already fills ink, matching
the `ink = selected` convention of `.seg`/`.tab`/`.pager`.)

## Accessibility

The custom controls are div-built, so `futurism.js` carries their semantics — keep
it loaded. `fdInit()` runs on load and wires ARIA roles + keyboard on `.sel`
(button + listbox popup, Enter/↑↓/Esc), `.tabs` (tablist, ←/→ roving), and `.toggle`
(switch, Space/Enter); call `fdInit()` again after injecting components at runtime.
Every focusable control shows the same 3px accent `:focus-visible` ring — don't
remove it. Native elements stay native on purpose: checkbox/radio are styled
`<input>`s, and the modal is a real `<dialog>` (Tab-trap + Esc); give the dialog
an `autofocus` button. Overlays dim with `--scrim`, motion respects
`prefers-reduced-motion` (the live `.dot` keeps a static ring there), and a
`forced-colors` block re-asserts selected/active state for Windows High Contrast.

**Scope.** The interactive controls require `futurism.js` — with JS off, the custom
select/tabs/toggle/drawer/toast are inert (use native elements if you need a no-JS
fallback). The motion language is directional and LTR-oriented (skews, slide-ins,
darting underlines); for RTL, flip those with `:dir(rtl)` overrides.

**SPA / framework use.** The kit drives state through DOM classes (`.on`/`.open`)
and imperative ARIA, with one set of document-level delegates. Treat those controls
as uncontrolled — don't let React/Vue re-render over the toggled classes — or port
the control to framework state. Call `fdInit()` from your mount hook for components
added after load; the document delegates are attached once and keep working.

## Responsive & touch

The laws are resolution-independent, but the layout patterns below keep an app
usable on a phone without breaking the aesthetic:

- **Off-canvas drawer.** A fixed sidebar slides in over a `--scrim` backdrop on
  mobile and becomes static at your desktop breakpoint. Use `.drawer` /
  `.scrim-bg` + `fdDrawer()`.
- **Touch targets ≥ ~40px.** The kit already grows icon buttons, keycaps, accent
  swatches, pager buttons, and select rows to ~40px+ under `@media (max-width:640px)`
  — the 28–32px desktop sizes are too small for thumbs. Match that bump for any new
  small control you add.
- **No horizontal body scroll.** Contain wide content (tables, tab bars, command
  rows) with `overflow-x:auto` on *that* element; never let the page body scroll
  sideways. Add `min-width:0` to flex children that hold ellipsised text.
- **Collapse header chrome.** Hide the wordmark/subtitle and toggle labels at
  narrow widths, keeping just the logo mark + essential controls. Use `.only-desktop`
  / `.only-mobile` for chrome that swaps entirely (a desktop hint vs. a mobile-worded
  one, not just a shrink) — `.only-desktop` is hidden by default and shown
  (`display:block`) at the `min-width:768px` breakpoint; `.only-mobile` is the
  inverse. The base utility only sets `display:none`/`block`; if the shown state
  needs `flex`/`inline-flex`/`inline-block` instead, mirror the kit's own two-rule
  shape with a compound selector rather than overriding just one side — e.g.
  `.keyhint.only-desktop{display:none}` plus
  `@media (min-width:768px){.keyhint.only-desktop{display:flex}}`. A compound
  selector outranks the utility's single-class rule on any specificity tie, but
  only within the media condition it's written under — a single *unscoped* override
  would win at the hidden breakpoint too and defeat the hide, so give your override
  the same two-rule shape as the utility itself, just with your display value
  swapped in.
- **Popover, not inline rows, on mobile.** A wide control (e.g. the 7-swatch
  accent row) collapses to a single trigger + popover — that's what `.accpick` is.

Drive these with `min-width` media queries (mobile-first): style the compact
layout as the default, then restore the desktop layout at `@media (min-width:768px)`.

## When extending the kit

New components must obey the eight laws and use only tokens. Match the existing
motion vocabulary (slide/dart/lurch/march at `--fast`/`--med`). Add the component
to `references/components.md` so the kit stays the single source of truth.

The kit already carries these conventions on its own components; a new affordance
that doesn't generalize them silently breaks parity. So for any new control:

- **Accent fill → `--on-accent` text** (never `--ink`). See Theming.
- **Loading/progress → reuse `fd-march`** (the barber-pole), never a rotary spinner;
  shape a `.skel`-style placeholder, don't invent a new loader.
- **A status/selected/loading affordance needs a forced-colors fallback.** Color-mix
  fills, gradients, and `box-shadow` are stripped under `@media (forced-colors:active)`
  — re-assert the cue with a border/outline or `Highlight`, the way the kit does for
  `.skel`/`.prog`/`.dot` and the selected states.
- **A state that changes without focus moving** (a toast, a "refreshing" indicator)
  needs `role="status"` + `aria-live` so it's announced — match `.toast`.
- **Progressive enhancement:** a component's CSS should stand alone; if it needs JS to
  be usable (positioning, etc.), give it a working CSS default and let the JS upgrade
  it (see the `.sel` dropdown — absolute default, JS promotes to fixed).
