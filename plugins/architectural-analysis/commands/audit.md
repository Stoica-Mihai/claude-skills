---
description: Run code-audit-deep on the given files (line-level perf/correctness/durability/memory/complexity/coupling audit)
---

Invoke the `code-audit-deep` skill. Use the SKILL.md at
`${CLAUDE_PLUGIN_ROOT}/skills/code-audit-deep/SKILL.md` to guide
the audit.

Target(s): $ARGUMENTS

If `$ARGUMENTS` is empty, ask the user which file(s) to audit
before proceeding. Do not assume; the skill explicitly requires
named targets or hotspots-driven target selection.

Output follows the format the skill specifies: categorized
findings with `file:line` references and one-line fix sketches,
ending with a "Top targets" summary of the 3-5 highest-leverage
fixes.
