---
name: opsx-ext:task
description: Use when the user wants new code written or new behavior added — "add X", "build X", "implement X", "create X", "migrate X", or "do this task". Drives a single OpenSpec change end-to-end — explore, plan, self-review, implement, test, verify — as one deterministic workflow, then hands back for review and commit. Prefer `opsx-ext:task-queue` when the request clearly splits into multiple independent changes that benefit from isolated worktrees. Skip for questions, explanations, bug fixes, single-line patches, console.log debugging, version bumps, and /opsx command runs.
argument-hint: <description of what you want to build or change>
effort: max
model: opus[1m]
---

# Autonomous Task Workflow

Drives a single OpenSpec change end-to-end. The whole autonomous pipeline — explore, generate artifacts, self-review, implement, test, verify — runs inside ONE deterministic Workflow. This skill does only what a workflow physically cannot: check preconditions, and handle the parts that need a human or that spawn subagents (the review gate, and archive + commit).

An A/B on this design measured it ~1.8× faster wall-clock-to-done than driving each phase from the main thread, because it collapses the many main-thread round-trips (one per phase, plus one per self-review and verify loop iteration) into a single hand-off. The gap widens with the number of phases and loop iterations.

## Why the split is exactly here

A Workflow runs in the background, returns one result, and its leaf subagents have the `Skill` tool but NOT the `Agent`/`Task` tool. That fixes the boundary:

- **Inside the workflow** (Phases 1–2f): explore, generate artifacts, self-review, implement in waves, test, verify. The workflow invokes the `openspec-explore`, `openspec-ff-change`, and `openspec-verify-change` skills directly — all three run non-interactively (explore has no mandatory prompt; ff/verify are given the change name/description so they never ask). It does NOT use `openspec-new-change` (halts for the user) or `openspec-apply-change` (serial) — `new` is subsumed by `ff`, and `apply` is replaced by script-driven wave fan-out.
- **Outside the workflow** (this skill): the human approval gate, and `openspec-archive-change` — which prompts the user repeatedly and itself spawns a subagent, so it cannot run inside a workflow leaf.

## Hard Requirement

OpenSpec must be initialized: `openspec/` must exist in the project. If it does not, stop and tell the user to run `openspec init` and `openspec update` first.

## Steps

### 1 — Precondition

Confirm `openspec/` exists (Bash). Abort with the message above if not. That is the only thing the main thread does before the gate — everything else is the workflow.

### 2 — Run the full pipeline

Calling the Workflow tool from this skill is sanctioned (these instructions are the opt-in). Invoke the bundled script:

```
Workflow({
  scriptPath: "<this skill's base directory>/scripts/opsx-task-full.js",
  args: {
    description: "<the user's request, verbatim>",
    root: "<absolute path of the project>",
    schema: "<optional openspec schema name, omit for default>"
    // omit `test` — the workflow detects the suite itself. Pass
    // test:{enabled,runCmd,coverageCmd} only to override that detection.
  }
})
```

The workflow returns one of:

- `{ stopped: "should-split", exploration }` — the request is really several independent changes. Stop and recommend `opsx-ext:task-queue`; do not implement.
- `{ changeName, summary, openQuestions, artifactFiles, completed, errors, testStatus, verifyClean, verifyPasses, residualConcerns }` — the pipeline ran to verification.

If `errors` is non-empty or `verifyClean` is false, surface that — those are the seams the pipeline could not close on its own. `residualConcerns` is non-empty when self-review stopped with unresolved cross-artifact blockers (it escalates rather than looping forever) — present those to the user at the gate so they can decide, since the pipeline judged it couldn't reconcile them automatically.

### 3 — Human gate

Present a one-paragraph summary: change name, file count, `verifyClean` state, any `openQuestions`, any `residualConcerns` (unresolved self-review blockers), and a smoke test the user can run. Then:

**Do not proceed until the user confirms.** If they report issues, fix them (re-running `openspec-verify-change` until clean), then return and wait again.

### 4 — Finalize

Once approved:

1. Invoke the `openspec-archive-change` skill for `<changeName>` (it runs here, in the main thread, because it prompts the user and spawns its own subagent).
2. Update documentation affected by the change (README, CLAUDE.md, etc.).
3. Stage only files created or modified during this change — never `git add .`.
4. Commit with a short summary + bullet body. Do not include a Co-Authored-By line.

Present: `"<change-name> is committed and ready."`

## Seams to be honest about

- **Explore runs as a one-shot, not a conversation.** `openspec-explore` is invoked non-interactively, so it investigates and reports once instead of having a back-and-forth about scope. Open questions it raises are surfaced at the gate rather than resolved mid-run.
- **No mid-run visibility or steering.** The pipeline runs opaque in the background until it returns. If the user wants to inspect or redirect between phases, that is the one thing this design trades away.
- **Nested skills run without their own fan-out.** When the workflow's leaf invokes `openspec-ff-change` / `openspec-verify-change`, that leaf cannot spawn subagents, so if those skills would normally parallelize internally they run serially here.
- **No mid-run human input.** Any `openspec-*` step that would normally ask the user a question proceeds on reasonable defaults (we pass the change name/description so they don't ask). Genuinely ambiguous calls surface as `openQuestions` at the gate, not as a mid-run prompt.
