---
description: Compare two screenshots — similarity %, a red-boxed diff overlay, and a written rundown of what changed
---

Invoke the `compare-screenshots` skill. Use the SKILL.md at
`${CLAUDE_PLUGIN_ROOT}/skills/compare-screenshots/SKILL.md` to guide
the comparison.

Image pair: $ARGUMENTS

`$ARGUMENTS` should be two image paths. If fewer than two paths are
given, ask the user for the missing one before proceeding — do not
guess which images to compare.

Follow the skill: run the bundled engine to score similarity and
draw the overlay, branch on the similarity gate, then look at the
overlay and per-region crops yourself to write the what-changed
rundown in the skill's report format.
