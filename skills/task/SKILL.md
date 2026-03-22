---
name: opsx-ext:task
description: Use when the user wants to execute a full autonomous spec-driven development cycle using OpenSpec. Takes a task description and drives it from exploration through implementation, verification, and archival — with self-correction loops at every stage. Requires OpenSpec to be initialized in the project. Use this whenever someone says "do this task", "build this feature", "implement this", or wants an end-to-end OpenSpec workflow without manually invoking each command.
argument-hint: <description of what you want to build or change>
---

# Autonomous Task Workflow

End-to-end orchestrator for OpenSpec. Takes a user's request from idea to committed code with self-correction at every stage.

## Hard Requirement

OpenSpec must be initialized in the project. If the `openspec/` directory does not exist, stop immediately and tell the user to run `openspec init` and `openspec update` first. Do not proceed without this.

## Workflow

Follow these phases in exact order. Do not skip phases. Do not reorder them.

### Phase 1 — Explore

Invoke `/opsx:explore` with the user's description. The goal is to investigate the codebase, understand the current state, and surface gaps or ambiguities in the request.

After exploration, present your findings:
- Your understanding of the request
- Gaps, ambiguities, or open questions
- Suggested scope boundaries

Iterate with the user until all gaps are resolved.

Then ask for explicit confirmation before moving on:

> "I've covered all the gaps I found. Is there anything else needed, or can we proceed?"

**Do not move to Phase 2 until the user confirms.**

### Phase 2 — Create change

Invoke `/opsx:new` with a descriptive change name derived from the user's request.

### Phase 3 — Generate artifacts

Invoke `/opsx:ff` to fast-forward and generate all planning artifacts (proposal, specs, design, tasks).

### Phase 4 — Self-review artifacts

After artifacts are generated, ask yourself: **"Are there any concerns about these changes?"**

Read every generated artifact and look for:
- Missing requirements or edge cases
- Contradictions between artifacts
- Incomplete or vague task breakdowns
- Technical risks in the design

If any concerns are found, fix them directly in the artifact files. Then ask yourself the same question again. Repeat until the answer is "no concerns." Maximum 100 passes — if concerns persist after 100 iterations, present the remaining concerns to the user for guidance.

**Do not proceed to Phase 5 until all concerns are resolved.**

### Phase 5 — Implement

Invoke `/opsx:apply` to implement all tasks from the change.

If `/opsx:apply` reports errors during implementation, resolve them before proceeding to Phase 6.

### Phase 6 — Verify and fix

Invoke `/opsx:verify` to validate the implementation against the artifacts.

If ANY findings are reported — regardless of severity (CRITICAL, WARNING, or SUGGESTION) — fix every single one. Then invoke `/opsx:verify` again. Repeat this loop until verification returns zero findings.

Zero tolerance. A SUGGESTION is still a finding.

### Phase 7 — User verification

All automated checks are clean. Now ask the user to review:

> "All automated verification passes with zero findings. Please review the changes yourself and let me know if anything needs fixing."

If the user reports issues, fix the reported issues in the code, then go back to Phase 6 — re-run `/opsx:verify` and repeat the fix loop until zero findings. Do not re-run `/opsx:apply`. If the user confirms everything is OK, proceed.

### Phase 8 — Archive

Invoke `/opsx:archive` to finalize and archive the change.

### Phase 9 — Update documentation

Review and update all project documentation affected by this change, including but not limited to:
- README.md
- CLAUDE.md
- Any other docs that reference changed functionality, APIs, configuration, or behavior

Only update docs where the change is relevant — don't touch files that aren't affected.

### Phase 10 — Commit

Stage only the files that were created or modified during this workflow. Do not use `git add .` or `git add -A`. Then create a git commit.

Commit message format:
```
<short summary of what was done>

- <change 1>
- <change 2>
- <change 3>
```

Keep the list short and concise. Do not include a Co-Authored-By line.
