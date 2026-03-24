---
name: opsx-ext:task
description: Use when the user wants to execute a full autonomous spec-driven development cycle using OpenSpec. Takes a task description and drives it from exploration through implementation, verification, and archival — with self-correction loops at every stage. Requires OpenSpec to be initialized in the project. Use this whenever someone says "do this task", "build this feature", "implement this", or wants an end-to-end OpenSpec workflow without manually invoking each command.
argument-hint: <description of what you want to build or change>
effort: max
model: opus[1m]
---

# Autonomous Task Workflow

End-to-end orchestrator for OpenSpec. Takes a user's request from idea to committed code with self-correction at every stage.

## Core Principle: Maximum Parallelization

Speed is the top priority. Every phase must maximize throughput by dispatching as many subagents as possible to work concurrently. There is no limit on the number of subagents — spawn as many as the work allows. If a phase has N independent units of work, dispatch N subagents simultaneously. Never serialize work that can run in parallel.

When dispatching subagents:
- Launch all independent subagents in a single tool-call turn — do not wait between dispatches
- Give each subagent a complete, self-contained prompt with all context it needs (file paths, requirements, constraints) so it can work autonomously without follow-up questions
- Use background execution for subagents whose results are not blocking the next immediate action
- Only serialize work when there is a true data dependency (one subagent's output is another's input)

## Hard Requirement

OpenSpec must be initialized in the project. If the `openspec/` directory does not exist, stop immediately and tell the user to run `openspec init` and `openspec update` first. Do not proceed without this.

## Workflow

Follow these phases in exact order. Do not skip phases. Do not reorder them.

### Phase 1 — Explore

Invoke `/opsx:explore` with the user's description. The goal is to investigate the codebase, understand the current state, and surface gaps or ambiguities in the request.

**Parallelization:** If the user's request spans multiple areas of the codebase (e.g., frontend + backend, multiple services, several modules), dispatch one subagent per area to explore concurrently. Each subagent should investigate its area and report back findings. Merge all findings before presenting to the user.

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

**Parallelization:** Dispatch one subagent per artifact file to review simultaneously. Each subagent reviews its assigned artifact and reports concerns. This turns a sequential multi-file review into a single parallel pass.

Each subagent should look for:
- Missing requirements or edge cases
- Contradictions with other artifacts (provide cross-references in each subagent's prompt)
- Incomplete or vague task breakdowns
- Technical risks in the design

Collect all concerns from all subagents, then fix them. After fixes, dispatch another round of parallel review subagents to re-check. Repeat until all subagents report zero concerns. Maximum 100 passes — if concerns persist after 100 iterations, present the remaining concerns to the user for guidance.

**Do not proceed to Phase 5 until all concerns are resolved.**

### Phase 5 — Implement

Invoke `/opsx:apply` to implement all tasks from the change.

**Parallelization:** After `/opsx:apply` generates the task list, identify which tasks are independent (no shared file edits, no data dependencies between them). Dispatch one subagent per independent task to implement concurrently. For tasks that depend on each other, chain them sequentially but parallelize everything else.

If tasks touch different files or modules, they are almost certainly independent — parallelize them. If multiple tasks modify the same file, serialize those but run them in parallel with tasks touching other files.

If any subagent reports errors during implementation, dispatch fix subagents in parallel for independent errors. Resolve all errors before proceeding.

**Config file update:** After all implementation tasks are complete, check whether the change introduces config-driven behavior — new environment variables, feature flags, settings keys, or service configuration. If it does, update the relevant config files:
- `.env.example` / `.env.template` — add new env vars with sensible defaults and comments
- Config templates and default config files (e.g., `config.yaml`, `settings.json`, `appsettings.json`)
- Schema files that define valid config (e.g., JSON Schema, Zod schemas, pydantic models)
- Docker/compose files if new env vars or service config were introduced

Only update files that already exist in the project — do not create new config infrastructure. If unsure whether a variable needs a default, add it with a placeholder and a comment explaining what it controls.

### Phase 6 — Test

After implementation is complete, check whether the project has an existing test suite. Look for test directories (`tests/`, `test/`, `__tests__/`, `spec/`), test files (files matching `*test*`, `*spec*`), and test runner configuration (`jest.config.*`, `pytest.ini`, `pyproject.toml [tool.pytest]`, `.mocharc.*`, `vitest.config.*`, `Cargo.toml [dev-dependencies]`, etc.).

If the project has tests:

1. **Run the full test suite.** Use the project's test runner. If it fails, diagnose and fix every failure before moving on. Re-run until all tests pass.

2. **Check test coverage.** Run the test suite with coverage enabled (e.g., `--coverage`, `--cov`, `cargo tarpaulin`). Review the coverage report to identify untested code paths — particularly in code that was added or modified by this change.

3. **Add missing tests.** Write tests to cover uncovered code paths introduced by this change. **Parallelization:** Dispatch one subagent per file or module that needs test coverage. Each subagent writes tests for its assigned scope. This is one of the biggest parallelization wins — test writing is almost always independent across files. The goal is to get coverage as close to 100% as possible. Focus on:
   - New functions, methods, and branches added in this change
   - Edge cases and error paths
   - Integration points between new and existing code

4. **Remove stale tests.** If this change removed or significantly altered functionality, find and remove tests that reference deleted code, test behavior that no longer exists, or are otherwise broken by the change. Dead tests are noise — clean them up. **Parallelization:** If stale tests span multiple test files, dispatch one subagent per file to clean up concurrently.

5. **Re-run the full suite with coverage.** Confirm all tests pass and coverage has improved. If coverage gaps remain in changed code, dispatch subagents in parallel to add more tests for each gap. Repeat until coverage on the changed files is as close to 100% as practical.

If the project has no tests at all, skip this phase entirely — do not create a test framework from scratch unless the user specifically asked for it.

### Phase 7 — Verify and fix

Invoke `/opsx:verify` to validate the implementation against the artifacts.

If ANY findings are reported — regardless of severity — fix every single one, including SUGGESTIONs. Low-severity findings left unfixed accumulate into real problems, and fixing them now while context is fresh is cheaper than revisiting later. **Parallelization:** Group findings by file. Dispatch one subagent per file to fix all findings in that file concurrently. Then invoke `/opsx:verify` again. Repeat this loop until verification returns zero findings.

### Phase 8 — User verification

All automated checks are clean. Now ask the user to review:

> "All automated verification passes with zero findings. Please review the changes yourself and let me know if anything needs fixing."

If the user reports issues, fix the reported issues in the code (parallelize across files when multiple issues are reported), then go back to Phase 7 — re-run `/opsx:verify` and repeat the fix loop until zero findings. Do not re-run `/opsx:apply`. If the user confirms everything is OK, proceed.

### Phase 9 — Archive

Invoke `/opsx:archive` to finalize and archive the change.

### Phase 10 — Update documentation

Review and update all project documentation affected by this change, including but not limited to:
- README.md
- CLAUDE.md
- Any other docs that reference changed functionality, APIs, configuration, or behavior

**Parallelization:** Dispatch one subagent per documentation file that needs updating. Each subagent reads the current doc, understands the changes made, and applies the relevant updates. All doc updates are independent of each other.

Only update docs where the change is relevant — don't touch files that aren't affected.

### Phase 11 — Commit

Stage only the files that were created or modified during this workflow. Do not use `git add .` or `git add -A`. Then create a git commit.

Commit message format:
```
<short summary of what was done>

- <change 1>
- <change 2>
- <change 3>
```

Keep the list short and concise. Do not include a Co-Authored-By line.
