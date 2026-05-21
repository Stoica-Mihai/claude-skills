# Analyst pass — iteration 3

## Headline

| Metric | v3 skill (glyph-sharpened) | v2 skill (lang-agnostic, no glyphs) | Δ |
|---|---|---|---|
| Pass rate | 100% (9/9) | 89% (8/9) | **+11pp** |
| Time | 246s ± 55s | 207s ± 32s | +39s |
| Tokens | 70k ± 4k | 63k ± 6k | +7k |

v3 passes all 3 evals; v2 failed plan.rs (hit 3/7 ground-truth, threshold 4). v2's failure here is partly variance — same v2 skill hit 6/7 on plan.rs in iter-2.

## Real story: detection density across all three skill versions

The pass-rate metric is binary. The interesting view is *raw
ground-truth coverage*:

| File | v3 skill (iter-3) | v0 skill (iter-1) | **no-skill baseline (iter-1)** |
|---|---|---|---|
| commit.rs | 8/8 (100%) | 6/8 (75%) | 8/8 (100%) |
| structural.rs | 6/7 (86%) | 4/7 (57%) | 7/7 (100%) |
| plan.rs | 4/7 (57%) | 6/7 (86%) | 6/7 (86%) |
| **Sum** | **18/22 (82%)** | **16/22 (73%)** | **21/22 (95%)** |

Key reads:

1. **v3 closed 9pp of the gap vs v0** (73% → 82%). Glyph examples
   for `field_name_for_child`-style index-vs-id, `b as char` UTF-8
   corruption, and durability ordering all paid off.

2. **v3 still trails no-skill baseline by 13pp.** Raw detection
   density is highest when the agent is given the problem cold,
   without a checklist. The skill imposes structure but does cost
   some breadth.

3. **v3 regressed on plan.rs vs iter-2 (4/7 vs 6/7).** Specific
   misses: `par_iter` Vec materialization, scripted Rhai
   convergence re-run, `Permissions` Option always Some. The
   agent's transcript shows it *deliberately dropped* the Option
   finding ("test fixtures legitimately pass `None`") — a
   defensible judgment, but the assertion can't tell "correctly
   excluded" from "missed". For the other two, looks like ordinary
   variance — n=1 per cell.

## Where v3 wins over baseline

- **Format compliance** — every finding has `file:line` + symptom +
  `Fix:` sketch in a categorized list. Baseline outputs vary
  wildly: some use H/M/L severity tables, some prose paragraphs,
  some unnumbered bullets. Scannability is much higher with v3.
- **Token cost** — v3 averages 70k vs iter-1 baseline avg 71k. ~Par.
- **Axis coverage** — durability/ordering + concurrency axes
  surfaced findings (delete-before-fsync, `--threads` pool
  placement) the v0 skill missed. These were the iter-1 baseline-
  only findings; v3 absorbed them.

## Why baseline still wins on raw detection

Best hypothesis: without a skill, the agent treats each file as an
unknown and reads every line with no preconception. With a skill,
the agent matches each line against the skill's smell catalogue —
faster but biased toward smells it has explicit examples for.

The fix would be a `meta` axis ("look for anything that surprises
you, even if no axis above applies") to license non-catalogued
findings. Skipping this for now — incremental gain unclear and
adds skill bloat.

## Cost analysis

- **Time +19% vs v2** — reading two extra axes plus glyph lists.
- **Tokens +12% vs v2** — same reason.
- Acceptable cost for closing the structural.rs detection gap that
  was the iter-2 failure.

## Recommended next steps

The skill content is now defensibly close to no-skill baseline (-13pp
on detection, +0pp on cost, +∞ on format). Two remaining items
from the original plan, not yet done:

1. **Widen code-audit-deep description** so it fires on
   `hotspots`-style phrasings — currently the trigger surface is
   `audit / review / find bugs`, but the user's natural phrasing
   for line-level audit is "what are the hotspots?".

2. **Edit architectural-hotspots SKILL.md** to chain into
   code-audit-deep on the top-N flagged files. So a single
   "hotspots" query gets file rankings *and* line-level findings,
   matching what no-skill baseline produced in iter-0.

Then re-test the original "what are the hotspots?" prompt with
both skills installed to see if the gap to no-skill baseline closes
completely.

## Reproducibility caveat

Still n=1 per cell. The plan.rs cell variance (iter-2 hit 6/7,
iter-3 hit 4/7 with same task and ostensibly-better skill) is the
clearest sign that single-run benchmarks have ±2-3 finding
variance. Conclusions are directional, not precise.
