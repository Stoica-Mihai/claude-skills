---
name: compare-screenshots
description: Compare two screenshots and report every visual difference between them. Use this skill whenever the user gives you two image files (before/after, expected/actual, v1/v2, baseline/candidate) and wants to know what changed, spot the differences, diff two UI states, do visual-regression checking, or confirm two screens look identical. Triggers on "compare these screenshots", "what's different between these two images", "diff these UIs", "did the layout change", "spot the difference", "/compare-screenshots", or any before/after image pair. The skill first checks the pair is similar enough to be worth comparing, then produces a similarity percentage, a third image with the changed regions boxed in red, and a written rundown of what actually changed in each region.
---

# Compare Screenshots

Two screenshots in, three things out: a **similarity score**, a **highlighted
overlay image** with each changed region boxed and numbered, and a **written
rundown** of what changed in each box.

The work splits cleanly:

- **A bundled script does the pixel math** — alignment, similarity scoring,
  the similarity gate, region clustering, and drawing the overlay. This is
  deterministic and exact; eyeballing pixels is not, so do not try to compute
  diffs by hand.
- **You do the semantic part** — looking at the boxed regions and the cropped
  before/after pairs the script saves, then describing *what* changed ("the
  button turned green", "the heading reads 'Hello there' instead of 'Hello
  world'"). The script knows *where* differs; only vision knows *what* it means.

## Why the similarity gate exists

If the two images are of completely different screens, a pixel diff is noise —
every region "changed", and a rundown would be meaningless. So the script
scores structural similarity (SSIM) first and refuses to diff a pair that
falls below a threshold, telling the user the images are too dissimilar to
compare. This keeps the output honest: a diff is only produced when there is a
shared structure to diff against.

## Workflow

1. **Resolve the two image paths.** The user supplies them (often as command
   arguments). If only one or zero paths are given, ask for the missing
   one — do not guess.

2. **Pick an output directory** for the overlay and crops. Default to a
   `compare-screenshots-out/` folder next to the first image, or a scratch
   directory. Tell the user where it lands.

3. **Run the engine** (see below). Read its JSON.

4. **Branch on the gate:**
   - If `comparable` is `false`, report the similarity percentage and the
     script's `message` verbatim — the images are too different to diff. Stop
     here; do not invent differences.
   - If `comparable` is `true`, continue.

5. **Look at the results with your own eyes.** Read `overlay_path` to see the
   boxed regions in context, then read each region's `crop_before` /
   `crop_after` pair to see the change up close. The crops are why the script
   saves them — they are your evidence for the rundown.

6. **Write the report** in the format below.

## Running the engine

The script declares its own dependencies inline (PEP 723), so `uv run`
installs them in an isolated environment on first use — nothing to set up.

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/skills/compare-screenshots/scripts/compare.py" \
  <image1> <image2> --out-dir <output-dir>
```

It prints a JSON object:

```json
{
  "similarity_percent": 81.0,
  "ssim": 0.9989,
  "alignment": "translation",
  "comparable": true,
  "changed_pixel_percent": 5.8,
  "has_alpha": false,
  "regions": [
    {"id": 1, "box_xywh": [43,43,215,85], "area_px": 18275,
     "confidence": "high", "edge_change": 0.86,
     "crop_before": ".../region1_before.png", "crop_after": ".../region1_after.png"}
  ],
  "overlay_path": ".../diff_overlay.png",
  "minor_regions_collapsed": 0,
  "confidence_counts": {"high": 1, "medium": 1, "low": 0},
  "message": "2 primary changed region(s) reported (ranked by size). Boxes coloured by confidence…"
}
```

`regions` are **merged and ranked**. Adjacent diffs on the same line (the
glyphs of a menu bar, a footer) are unioned into one region so you get
element-level findings, not per-letter specks, and the list is sorted
largest-first — the first region is the most significant change. Only the top
`--max-regions` get crops and numbered boxes; any beyond that are drawn as thin
unnumbered boxes on the overlay and counted in `minor_regions_collapsed`
(usually peripheral reflow or background). Work through the ranked regions in
order; the long tail is rarely the real story.

Each region carries a **`confidence`** that it is a genuine change rather than
alignment residual, and the overlay box is coloured to match: **red = high**,
**amber = medium**, **gray = low**. The judgment comes from `edge_change` (how
much the edge structure inside the box differs — content that appeared or
vanished scores high) combined with alignment trust: under a reliable
same-size alignment any flagged change is high-confidence (a pure recolour with
no edge change still counts), but under a warped or `resize-fallback` alignment
a change with little edge structure is treated as likely residual and demoted.
Lead the rundown with the high-confidence regions; treat gray boxes
skeptically and confirm them against the crop before reporting them as real.
`confidence_counts` summarises the tally.

`similarity_percent` is the headline number and it is **content-based**, not
raw SSIM. It scores only the foreground — the pixels that differ from each
image's dominant background colour — so it answers "how alike are the actual
UIs". This matters because two completely unrelated screens that share a pale
background score ~70% on plain SSIM (a number that misleads a viewer into
thinking they are similar); content similarity scores them near 0%, which is
what a human sees. Report `similarity_percent` as the similarity. `ssim` is
kept only as a secondary signal — do not present it as "the similarity".

`alignment` reports how the second image was registered onto the first, and
the engine picks the method from the inputs:

- `translation` / `resize` — used when the two images are the **same size**
  (a regression before/after). Only a whole-frame scroll is cancelled;
  element moves are left in place so a layout shift still shows as a boxed
  region rather than being warped away.
- `similarity` — used when the two images are **different sizes** (captures at
  different zoom / aspect / crop, which is normal — you cannot assume the two
  shots match). Feature matching estimates a scale + rotation + translation and
  registers the shared content so the diff lines up regardless of size. It is
  only a 4-DOF similarity transform, never a perspective warp, so it still
  cannot hide a local element move. The diff is restricted to the overlapping
  region, and because a scale warp never lines up anti-aliased edges perfectly,
  expect a few more regions than on a same-size pair — lean on the crops.

If `alignment_note` appears, feature registration failed and the engine fell
back to a plain stretch-resize; treat the boxes as unreliable and rely on the
crops and your own read of the two images.

`has_alpha` is true when either image carries transparency. The engine folds
the alpha channel into the diff, so two screenshots that are identical in
color but differ in transparency are still flagged.

`comparable` is false when `similarity_percent` falls below the gate — the two
images share too little common foreground to be a meaningful before/after.
When it is false, report the `message` verbatim: it states the content
similarity and explains the pair looks like different screens, not a
before/after. Do not dig out the raw SSIM and present it as a reassuring
similarity figure — that is the exact trap this number is designed to avoid.

### Knobs

Defaults suit UI screenshots. Adjust only when the output calls for it, and
say so when you do:

| Flag | Default | Use when |
|---|---|---|
| `--tolerance N` | `30` | Raise to ignore more anti-aliasing/compression noise; lower toward `0` for pixel-strict asset checks. |
| `--gate F` | `0.4` | The content-similarity floor (0–1) below which the pair is declared too dissimilar to diff. Raise if the user only wants near-identical pairs compared; lower to force a diff on a heavily-redesigned pair. |
| `--min-area N` | `80` | Smallest region (px²) to report. Raise to suppress tiny specks; lower to catch single-glyph changes. |
| `--max-regions N` | `10` | How many ranked regions get crops + numbered boxes. The rest are drawn faintly and counted in `minor_regions_collapsed`. Raise if you genuinely need every small diff itemized. |

If a first run looks too noisy (dozens of tiny boxes) or too coarse (one giant
box over everything), re-run with adjusted `--tolerance` / `--min-area` rather
than apologizing for the output.

## Report structure

Use this shape:

```markdown
## Screenshot comparison

**Similarity: 99.5%** — N changed region(s). _(alignment: homography)_

![diff overlay](path/to/diff_overlay.png)

### What changed
1. **<region 1 short label>** — <what changed, before → after>.
2. **<region 2 short label>** — <what changed, before → after>.

<one-line takeaway: e.g. "Changes are cosmetic (color + copy), no layout shift."
or "Layout shifted — the nav moved down 40px.">
```

Number the rundown to match the numbered boxes in the overlay so the user can
map each description to its location. Keep each region to one line: name the
thing, then the before→after. If the script found zero regions above
threshold but similarity is high, say the images are visually identical (within
tolerance) rather than padding with non-findings.

## When the pair won't compare

If the gate trips, the user still deserves a clear answer. Report the
similarity percentage, state plainly that the images don't share enough
structure to diff meaningfully, and offer the likely cause — different screens,
wrong file pair, or a genuine wholesale redesign. If you suspect the gate is
just slightly too strict for an intentional big change, mention they can re-run
with a lower `--gate`.
