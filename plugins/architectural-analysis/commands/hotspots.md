---
description: Run architectural-hotspots (file rankings) and chain into code-audit-deep on top files
---

Invoke the `architectural-hotspots` skill on the target path. Use
the SKILL.md at `${CLAUDE_PLUGIN_ROOT}/skills/architectural-hotspots/SKILL.md`
to guide the analysis.

Target path: $ARGUMENTS

If `$ARGUMENTS` is empty, default to the current working
directory.

After producing the file-level rankings, **follow the "Chain to
code-audit-deep" section of the architectural-hotspots SKILL.md**:
pick the top 3-5 files by combined signal, then invoke the
`code-audit-deep` skill on those files using the SKILL.md at
`${CLAUDE_PLUGIN_ROOT}/skills/code-audit-deep/SKILL.md`.

Present both layers in the final response — rankings first, then
line-level findings per top file.
