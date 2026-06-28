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

## The seven laws

These are what make output read as *this* system rather than a red-tinted
generic site. Break one and the aesthetic collapses, so hold them unless the
user explicitly overrides:

1. **Square corners always.** `border-radius: 0`. The system has no rounding —
   the tension between hard rectangles and skewed type is the point.
2. **Solid offset shadows, never blur.** `box-shadow: 6px 6px 0 var(--shadow)`.
   A blurred shadow instantly reads as Material/SaaS, not Futurism.
3. **2px ink borders** on surfaces and controls — structure is drawn, not
   implied by elevation.
4. **One accent only.** Red (`--accent`) carries links, CTAs, rules, highlights.
   Adding a second hue dilutes the manifesto. If you need differentiation, use
   ink vs. red vs. outline, not new colors.
5. **Motion is machine, not toy.** Fast (`--fast: .12s`), medium (`--med: .2s`),
   easing `cubic-bezier(.2,.9,.1,1)`, and always **directional** — things slide,
   dart, lurch, march. Never spring, bounce, or fade-puff. Respect
   `prefers-reduced-motion` (the CSS already does).
6. **Skewed CTAs.** Primary actions use `transform: skewX(-8deg)` with the label
   counter-skewed (`skewX(8deg)`) so it stays upright. This is the speed cue.
7. **Never trust native form popups.** `<select>`, date pickers, etc. render with
   OS chrome that ignores the system. Use the custom `.sel` component (and the
   same approach for any other native popup) so the whole control is on-brand.

## Type discipline

- One family: `'Helvetica Neue', Arial, sans-serif` (the `--font` token).
- **Display/headings carry the drama**: weight 900, italic, negative tracking,
  tight line-height. **Body stays calm**: regular weight, line-height 1.55,
  `--muted` color, comfortable size. Do not make body text italic or heavy.
- Kickers/labels: 11px, uppercase, wide letter-spacing, in accent or ink.

## Theming

Every component is built on CSS variables, so light/dark is a single attribute
flip — no per-component dark overrides. When adding a new component, express all
colors as the existing tokens (`--bg`, `--surf`, `--ink`, `--muted`, `--accent`,
`--line`, `--shadow`, `--field`, `--on-accent`) and it will theme for free. If a
value can't be expressed in tokens, add a new token to both theme blocks rather
than hard-coding a hex.

## When extending the kit

New components must obey the seven laws and use only tokens. Match the existing
motion vocabulary (slide/dart/lurch/march at `--fast`/`--med`). Add the component
to `references/components.md` so the kit stays the single source of truth.
