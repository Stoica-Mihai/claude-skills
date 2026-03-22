---
name: improve
description: Use when the user wants to improve an existing skill in this repository. Reads a skill's SKILL.md (and any supporting files), analyzes it for quality and clarity, applies improvements, increments the plugin version in marketplace.json, and updates README.md if anything user-facing changed. Trigger this whenever someone says "improve this skill", "make this skill better", "refine skill X", "clean up the task skill", or wants to enhance an existing skill's instructions, description, or structure.
argument-hint: <skill name or path, e.g. "task" or "skills/task">
---

# Skill Improvement Workflow

Takes an existing marketplace skill and makes it better — clearer instructions, stronger triggering description, better structure — then bumps the version, keeps docs in sync, and commits.

## Phase 1 — Locate and Read

Resolve the target skill from the argument:

- **Name** (e.g., `task`): look in `skills/<name>/SKILL.md`
- **Qualified name** (e.g., `opsx-ext:task`): strip the plugin prefix and resolve as above
- **Directory path**: look for `SKILL.md` inside it
- **File path**: use directly if it ends in `SKILL.md`

Also check `plugins/` if nothing is found under `skills/`.

Read the full SKILL.md and scan for any referenced resources (scripts, references, assets directories). Read those too — you need the complete picture to improve anything.

If the skill cannot be found, tell the user and stop.

## Phase 2 — Analyze

Evaluate the skill against these dimensions:

### Triggering Description

The `description` field in frontmatter determines whether Claude invokes the skill. A weak description means missed triggers or false triggers.

Check for:
- **Specificity**: Does it say what the skill does AND when to use it?
- **Trigger phrases**: Does it include realistic phrases users would actually say?
- **Boundaries**: Does it clarify when NOT to use the skill?
- **Assertiveness**: Claude tends to under-trigger skills, so descriptions should lean toward eagerness rather than restraint

### Instruction Quality

- **Imperative form**: "Read the file" not "You should read the file"
- **Why over what**: Each significant instruction should explain the reasoning, not just the action. LLMs respond much better to understanding motivation than to rigid rules
- **Avoid heavy-handed directives**: If a draft has ALWAYS/NEVER in all caps, reframe as reasoning. Explaining why something matters is more effective than shouting
- **Progressive disclosure**: Is the SKILL.md under 500 lines? If it's growing long, should reference files absorb some of the detail?
- **Examples**: Are concrete examples provided where instructions would be ambiguous without them?

### Structure

- **Frontmatter**: `name` and `description` required, `argument-hint` recommended
- **Logical flow**: Do phases follow a natural order?
- **Parallelization**: For multi-step skills, are independent steps called out for concurrent execution?
- **Edge cases**: Are failure modes and recovery paths addressed where they matter?

### Consistency

- **Naming**: Does the skill name match sibling skills' conventions?
- **Style**: Does the tone match the rest of the plugin?

## Phase 3 — Plan Improvements

Present findings to the user before touching anything:

- What's working well (don't fix what isn't broken)
- What needs improvement, grouped by priority
- Suggested version bump type:
  - **Patch** (x.x.+1): Typo fixes, minor wording clarifications, formatting
  - **Minor** (x.+1.0): New sections, restructured workflow, improved instructions, added examples
  - **Major** (+1.0.0): Complete rewrite, fundamentally changed behavior

Ask for confirmation:

> "Here's what I'd improve. Want me to go ahead, or adjust anything?"

**Do not edit files until the user confirms.**

## Phase 4 — Apply Improvements

Edit the SKILL.md with the planned changes. Preserve the skill's intent and voice — improve clarity and structure without changing what the skill fundamentally does.

Guidelines:
- Keep changes focused and traceable
- Don't add unnecessary complexity
- Preserve existing examples and references that are still valid
- If the skill has supporting files (scripts, references), improve those too when relevant

## Phase 5 — Increment Version

Open `.claude-plugin/marketplace.json` and find the plugin that contains this skill (match by checking each plugin's `skills` array for a path that resolves to this skill's directory).

Bump the version according to the change type from Phase 3.

If the skill isn't registered in any plugin's `skills` array, tell the user and skip this phase.

## Phase 6 — Update README

Check `README.md` for references to this skill or its parent plugin. Update only if:

- The skill's user-facing description changed significantly
- The skill was renamed
- New invocation patterns or capabilities were added that users should know about

If nothing user-facing changed, leave the README alone. Say why you did or didn't update it.

## Phase 7 — Commit

Stage only the files modified during this workflow. Do not use `git add .` or `git add -A`.

Commit message format:
```
Improve <skill-name> skill

- <change 1>
- <change 2>
- <change 3>
```

Keep the list short and to the point. No Co-Authored-By line.

## Phase 8 — Summary

Show the user:
- Files modified and key improvements made
- New version number (if bumped)
- Whether README was updated and why
- Commit hash
