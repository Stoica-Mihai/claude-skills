---
name: opsx-ext:task
description: Use when the user wants new code written or new behavior added — "add X", "build X", "implement X", "create X", "migrate X", or "do this task". Drives a single OpenSpec change end-to-end in the current working tree — explore, plan, self-review, implement, test, verify, then hand back for review and commit. Prefer `opsx-ext:task-queue` when the request clearly splits into multiple independent changes that benefit from isolated worktrees. Skip for questions, explanations, bug fixes, single-line patches, console.log debugging, version bumps, and /opsx command runs.
argument-hint: <description of what you want to build or change>
effort: max
model: opus[1m]
---

# Autonomous Task Workflow

End-to-end orchestrator for a single OpenSpec change. Takes a user's request, plans it, implements it, and verifies it in the current working tree — then hands back to the user for final review and commit.

## Core Principles

1. **One change, one workflow**: This skill handles a single discrete change. If the request splits into independent pieces, hand off to `opsx-ext:task-queue` instead.
2. **Verify before commit**: The change is implemented and verified automatically, but only committed after the user reviews it.
3. **Parallel where possible**: Maximize parallelization within phases — spawn as many subagents as the work allows.

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

### Phase 1 — Explore

Invoke `/opsx:explore` with the user's description to investigate the codebase, understand the current state, and surface gaps or ambiguities.

**Parallelization:** If the request spans multiple areas (frontend + backend, multiple services, etc.), dispatch one subagent per area to explore concurrently. Merge all findings before presenting to the user.

After exploration, present:
- Your understanding of the request
- Gaps, ambiguities, or open questions
- A short, descriptive change name (kebab-case)

If the request clearly splits into multiple independent changes (e.g., "add the user model AND the auth endpoints AND the middleware"), stop and recommend `opsx-ext:task-queue` instead — that case warrants worktree-per-change isolation. Otherwise, proceed directly to Phase 2 without asking for confirmation. The user reviews everything in Phase 3; gating the start of implementation on a confirmation prompt just adds friction.

### Phase 2 — Plan & Implement

Run steps 2a through 2f without stopping. The next user interaction point is Phase 3.

#### 2a — Create Change

Invoke `/opsx:new` with the change name from Phase 1.

#### 2b — Generate Artifacts

Invoke `/opsx:ff` to fast-forward and generate all planning artifacts (proposal, specs, design, tasks).

#### 2c — Self-Review Artifacts

Ask yourself: **"Are there any concerns about these artifacts?"**

**Parallelization:** Dispatch one subagent per artifact file to review simultaneously. Each reviews its artifact looking for:
- Missing requirements or edge cases
- Contradictions between artifacts (provide cross-references in each subagent's prompt)
- Incomplete or vague task breakdowns
- Technical risks in the design

Collect all concerns, fix them, re-review. Repeat until zero concerns. Maximum 100 passes — if concerns persist, present remaining to the user.

#### 2d — Implement

Run implementation in **parallel waves**, orchestrated by this skill directly. Do **not** invoke `/opsx:apply` here — that command's step 6 is an in-process serial loop ("for each pending task: implement, mark complete, continue"), so once it starts there is no task list left to fan out from. Parallelism must be planned before any task is touched.

**Step 1 — Read the task list.** Open `openspec/changes/<change-name>/tasks.md` and the change's other artifacts (`proposal.md`, `design.md`, `specs/`).

**Step 2 — Group tasks by primary edit target.** Tasks within tasks.md are usually grouped into sections that each map to one source file (e.g. Section 4 → `src/paint.rs`). All tasks within one such file group MUST be handled by the same subagent — concurrent edits to the same file by separate subagents corrupt each other. Identify each group's primary file(s) and the inter-group dependencies (does group B's file `use`/`import`/re-export from group A's file?).

**Step 3 — Build a wave plan.** A typical wave structure:

- **Wave 0 — Scaffolding.** Cargo.toml / package.json / pyproject.toml / workspace registration / module declarations / error types and other primitives that every later group depends on. Run as a single subagent or do directly — usually small enough to not need fan-out.
- **Wave 1 — Independent modules.** Every file group whose only inter-group dependency is on Wave 0 artifacts. Fan out: one subagent per group, dispatched in parallel.
- **Wave 2+ — Aggregators.** Files that re-export from or wire together Wave 1 modules (e.g. `lib.rs`, `index.ts`, `mod.rs`, top-level `__init__.py`). Run after Wave 1 is fully complete.
- **Test wave.** Test files. Usually one subagent per test file, in parallel — but only after the code under test is complete.
- **Verify wave.** Build / typecheck / lint / `openspec validate` commands. Sequential; the orchestrator runs these directly via Bash.

When in doubt, prefer one extra wave with cleaner dependency lines over packing borderline-independent groups into the same wave.

**Step 4 — Dispatch each wave.** For each wave, send all subagent calls in a single tool-use turn (multiple Agent tool calls in one assistant message). Each subagent prompt MUST include:

- The exact tasks it owns, by their tasks.md numbering (e.g. "implement tasks 4.1 through 4.7")
- The full text of those tasks copied inline (don't make subagents re-read tasks.md)
- The relevant cross-references from `proposal.md` / `design.md` / spec deltas inline
- The list of files it is allowed to create/edit (its primary file(s))
- An explicit instruction to **return a JSON list of completed task numbers** in its final summary, e.g. `completed: ["4.1","4.2","4.3","4.4","4.5","4.6","4.7"]`
- An explicit instruction to **NOT edit `tasks.md`** — that file is owned by the orchestrator

**Step 5 — Mark tasks complete after each wave.** Once every subagent in the current wave has returned, the orchestrator reads `tasks.md` and edits each `- [ ] N.M` → `- [x] N.M` for the task numbers the subagents reported as complete. This is the only place tasks.md is mutated. Then proceed to the next wave.

**Step 6 — Errors.** If any subagent in a wave reports errors or partial completion, dispatch fix subagents in the next turn (still parallel for independent errors). Do not start the next wave until the current wave's outputs are clean.

**Config file update:** After implementation, check whether the change introduces config-driven behavior (env vars, feature flags, settings). If so, update relevant existing config files (`.env.example`, config templates, schema files, Docker/compose files). Only update files that already exist — do not create new config infrastructure.

#### 2e — Test

Check whether the project has an existing test suite (test directories, test files, test runner config).

If tests exist:

1. **Run the full suite.** Fix all failures before moving on.
2. **Check coverage.** Run with coverage enabled. Identify untested code paths in changed code.
3. **Add missing tests.** **Parallelization:** Dispatch one subagent per file/module needing coverage. Target close to 100% on changed files.
4. **Remove stale tests.** Clean up tests referencing deleted code or obsolete behavior.
5. **Re-run with coverage.** Confirm all pass and coverage improved. Repeat if gaps remain.

If no test suite exists, skip this step — do not create a test framework unless the user asked for it.

#### 2f — Verify Loop

Invoke `/opsx:verify` to validate implementation against artifacts. Verification catches drift between what was planned and what was built — fixing suggestions too prevents spec debt from accumulating.

Fix ALL findings — including suggestions. **Parallelization:** Group findings by file, dispatch one subagent per file to fix concurrently. Re-run `/opsx:verify`. Repeat until zero findings. Maximum 100 passes — if findings persist, log the remaining ones and proceed to Phase 3.

### Phase 3 — Summary & User Verification

Present a summary of what was changed and a smoke test the user can run to verify it. Use `-` if nothing is testable from outside.

| Change | Status | Files Changed | Smoke Test |
|--------|--------|---------------|------------|
| add-user-model | Verified | 4 files | `npm test -- --grep User` |

> "Change is verified and ready for review. Let me know if it looks good to finalize, or what needs fixing."

If the user reports issues, fix them, re-run `/opsx:verify` until clean, then return and wait for confirmation.

**Do not proceed until the user confirms.**

### Phase 4 — Finalize

Once approved:

1. Invoke `/opsx:archive` to finalize the change.
2. Update documentation (README.md, CLAUDE.md, any docs referencing changed functionality). **Parallelization:** Dispatch one subagent per doc file needing updates.
3. Stage only files created or modified during this workflow — do not use `git add .` or `git add -A`.
4. Commit:
   ```
   <short summary>

   - <change 1>
   - <change 2>
   - <change 3>
   ```
   Do not include a Co-Authored-By line.

Present a one-line confirmation:

> "`<change-name>` is committed and ready."
