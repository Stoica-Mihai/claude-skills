---
name: opsx-ext:task
description: Use when the user wants new code written or new behavior added — "add X", "build X", "implement X", "create X", "migrate X", or "do this task". Applies to any scope, from a single route to a full architectural overhaul. Orchestrates structured codebase exploration, change queue planning, isolated worktree execution, and spec verification. Skip for questions, explanations, bug fixes, single-line patches, console.log debugging, version bumps, and /opsx command runs.
argument-hint: <description of what you want to build or change>
effort: max
model: opus[1m]
---

# Autonomous Task Workflow

End-to-end orchestrator for OpenSpec. Takes a user's request, breaks it into a queue of discrete changes, and processes each one in an isolated git worktree — from planning through verified implementation — before handing back to the user for final review and commit.

## Core Principles

1. **Queue-first**: Break the request into discrete, independent changes before touching any code.
2. **Isolated execution**: Each change runs in its own git worktree so changes never interfere with each other.
3. **Verify before commit**: Each change is implemented and verified automatically, but only committed after the user reviews it.
4. **Parallel within, sequential across**: Maximize parallelization within each change's phases (spawn as many subagents as the work allows), but process changes one at a time through the queue.

When dispatching subagents within a phase:
- Launch all independent subagents in a single tool-call turn — do not wait between dispatches
- Give each subagent a complete, self-contained prompt with all context it needs so it can work autonomously
- Use background execution for subagents whose results are not blocking the next immediate action
- Only serialize work when there is a true data dependency

## Hard Requirement

OpenSpec must be initialized in the project. If the `openspec/` directory does not exist, stop immediately and tell the user to run `openspec init` and `openspec update` first. Do not proceed without this.

## Running OpenSpec CLI Commands

The sub-skills invoked throughout this workflow (`/opsx:ff`, `/opsx:apply`, etc.) run `openspec` CLI commands that produce JSON output. Run each command as a standalone Bash call — the Bash tool returns stdout directly. Do NOT pipe `openspec` output through Python, jq, or any other inline processor. Do NOT use `2>&1` — stderr mixed into stdout corrupts JSON parsing. If you need to inspect specific fields from large JSON output, save the output to a temp file with `> /tmp/openspec-out.json` and use the Read tool.

## Workflow

Follow these phases in exact order. Do not skip phases. Do not reorder them.

### Phase 1 — Explore & Build Queue

Invoke `/opsx:explore` with the user's description to investigate the codebase, understand the current state, and surface gaps or ambiguities.

**Parallelization:** If the request spans multiple areas (frontend + backend, multiple services, etc.), dispatch one subagent per area to explore concurrently. Merge all findings before presenting to the user.

After exploration, present:
- Your understanding of the request
- Gaps, ambiguities, or open questions
- The **change queue** — a numbered list of discrete, independent changes that together fulfill the request. Each entry has a short name and a one-line scope description.

Example:
> 1. **add-user-model** — Create the User database model and migration
> 2. **add-auth-endpoints** — Add login/register/logout API endpoints
> 3. **add-auth-middleware** — Add JWT middleware to protected routes

Changes should be ordered so foundational work comes first. Each change must be independently implementable in its own worktree off the current HEAD — if change B depends on change A being merged first, combine them into one change.

**HARD STOP — Queue confirmation is mandatory.**

After presenting the queue, you MUST stop and ask the user:

> "Would you like to add, reorder, merge, split, or remove any items before we proceed?"

Then WAIT for the user's response. Do NOT proceed, do NOT create worktrees, do NOT generate artifacts, do NOT invoke any Phase 2 steps. The user may modify the queue in any way. If they add or change items, present the updated queue and ask again.

**Phase 2 is BLOCKED until the user explicitly says the queue is confirmed (e.g., "looks good", "go ahead", "confirmed"). Absence of objection is NOT confirmation — you must receive an affirmative response.**

### Phase 2 — Execute Queue

Process the entire queue without stopping for user input. Run steps 2a through 2h for each change, then immediately start the next. The only user interaction point is Phase 3 — after every change in the queue is complete.

#### 2a — Create Worktree

Create a git worktree branching from HEAD. Append the current Unix timestamp to the branch name to avoid collisions:

```bash
git worktree add -b <change-name>-$(date +%s) "../$(basename "$PWD")-<change-name>" HEAD
```

Record the original project directory. All subsequent work for this change happens in the worktree — `cd` into it before proceeding.

If OpenSpec is not initialized in the worktree (e.g., `openspec/` is gitignored), run `openspec init` and `openspec update` in the worktree first.

#### 2b — Create Change

Invoke `/opsx:new` with a descriptive change name derived from the queue entry.

#### 2c — Generate Artifacts

Invoke `/opsx:ff` to fast-forward and generate all planning artifacts (proposal, specs, design, tasks).

#### 2d — Self-Review Artifacts

Ask yourself: **"Are there any concerns about these artifacts?"**

**Parallelization:** Dispatch one subagent per artifact file to review simultaneously. Each reviews its artifact looking for:
- Missing requirements or edge cases
- Contradictions between artifacts (provide cross-references in each subagent's prompt)
- Incomplete or vague task breakdowns
- Technical risks in the design

Collect all concerns, fix them, re-review. Repeat until zero concerns. Maximum 100 passes — if concerns persist, present remaining to the user.

#### 2e — Implement

Invoke `/opsx:apply` to implement all tasks from the change.

**Parallelization:** After `/opsx:apply` generates the task list, identify independent tasks (no shared file edits, no data dependencies). Dispatch one subagent per independent task. Serialize tasks that modify the same file, but run them in parallel with tasks touching other files.

If any subagent reports errors, dispatch fix subagents in parallel for independent errors. Resolve all before proceeding.

**Config file update:** After implementation, check whether the change introduces config-driven behavior (env vars, feature flags, settings). If so, update relevant existing config files (`.env.example`, config templates, schema files, Docker/compose files). Only update files that already exist — do not create new config infrastructure.

#### 2f — Test

Check whether the project has an existing test suite (test directories, test files, test runner config).

If tests exist:

1. **Run the full suite.** Fix all failures before moving on.
2. **Check coverage.** Run with coverage enabled. Identify untested code paths in changed code.
3. **Add missing tests.** **Parallelization:** Dispatch one subagent per file/module needing coverage. Target close to 100% on changed files.
4. **Remove stale tests.** Clean up tests referencing deleted code or obsolete behavior.
5. **Re-run with coverage.** Confirm all pass and coverage improved. Repeat if gaps remain.

If no test suite exists, skip this step — do not create a test framework unless the user asked for it.

#### 2g — Verify Loop

Invoke `/opsx:verify` to validate implementation against artifacts. Verification catches drift between what was planned and what was built — fixing suggestions too prevents spec debt from accumulating.

Fix ALL findings — including suggestions. **Parallelization:** Group findings by file, dispatch one subagent per file to fix concurrently. Re-run `/opsx:verify`. Repeat until zero findings. Maximum 100 passes — if findings persist, log the remaining ones and proceed to 2h.

#### 2h — Exit Worktree

This change is verified. Return to the original project directory:

```bash
cd <original-project-directory>
```

Log progress inline — do NOT stop or wait for user input:
> "Change N/M complete: **change-name** — verified. Worktree: `<path>`, branch: `<branch>`. Continuing to next change..."

Immediately proceed to the next change in the queue (back to 2a). Do not ask the user to review, confirm, or approve anything between queue items. The user reviews everything in Phase 3.

### Phase 3 — Summary & User Verification

After all changes are processed, present a summary table with smoke test steps the user can run to verify each change. Use `-` if nothing is testable from outside:

| # | Change | Branch | Worktree Path | Status | Smoke Test |
|---|--------|--------|---------------|--------|------------|
| 1 | add-user-model | add-user-model-1711234567 | ../project-add-user-model | Verified | `cd ../project-add-user-model && npm test -- --grep User` |
| 2 | add-auth-endpoints | add-auth-endpoints-1711234589 | ../project-add-auth-endpoints | Verified | `curl -X POST localhost:3000/auth/login -d '{"email":"test@test.com"}'` |

> "All changes are verified and ready for review. Each worktree is independent — review them in any order. Let me know which to finalize, and if any need fixes."

If the user reports issues with a change, `cd` into that worktree, fix the issues, re-run `/opsx:verify` until clean, then return and wait for confirmation.

**Do not proceed until the user confirms which changes to finalize.**

### Phase 4 — Finalize Approved Changes

For each approved change, in queue order:

1. `cd` into the worktree
2. Invoke `/opsx:archive` to finalize the change
3. Update documentation (README.md, CLAUDE.md, any docs referencing changed functionality). **Parallelization:** Dispatch one subagent per doc file needing updates.
4. Stage only files created or modified during this workflow — do not use `git add .` or `git add -A`
5. Commit:
   ```
   <short summary>

   - <change 1>
   - <change 2>
   - <change 3>
   ```
   Do not include a Co-Authored-By line.
6. Return to the main working directory

After all approved changes are committed, present the final summary:

> "All approved changes are committed:
> - `add-user-model` — ready to merge
> - `add-auth-endpoints` — ready to merge
>
> Merge in order with `git merge <branch>` or create PRs."

If any changes were rejected, offer cleanup:
```bash
git worktree remove <path>
git branch -D <branch>
```
