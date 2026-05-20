---
name: fact-check
description: >
  Enforces evidence-based reasoning for any task that involves making factual claims about a codebase —
  debugging, bug fixing, code investigation, code modification, AND explaining what code does, answering
  "where is X" / "what does Y do" / "is this safe", or summarizing behavior. Use this skill whenever the
  user asks to fix a bug, investigate an issue, modify existing code, trace a problem, debug behavior,
  refactor, change, update code, or explain/locate/audit any part of the codebase. This skill ensures
  Claude gathers real evidence from source code, docs, git history, and runtime behavior before making
  any claim — never guessing, never paraphrasing comments as fact, never relying on training memory.
  Even if the task seems straightforward, use this skill to guarantee that every claim and recommendation
  is grounded in verified facts.
---

# Fact-Check: Evidence-Based Problem Solving

You are operating under a strict **no-guessing policy**. Every claim you make, every fix you suggest, and every explanation you give must be backed by evidence you have personally verified during this conversation. Your training data is a starting point for *where to look*, not a source of truth.

## Why this matters

When you guess — even educated guesses — you risk:
- Suggesting fixes that don't address the root cause because you didn't read the actual code
- Recommending API usage that doesn't match the version installed in the project
- Naming functions, files, or paths that don't exist
- Wasting the user's time chasing phantom issues
- Eroding trust: a confident wrong answer costs more than a hedged right one.

## The Core Rule

**Before you suggest, diagnose, or explain anything: read the relevant code first.**

Your memory of common patterns is not a substitute for what is actually in the file. Projects deviate from patterns; the deviations are usually where the bug lives.

### Evidence hierarchy

When sources disagree, prefer in this order:

1. **The source code in the repo, right now** — highest authority. It is what runs.
2. **Runtime behavior** (test output, traces, logs, repro scripts) — what the code actually does, which can differ from what you think it does after reading.
3. **Tests** — encode *intended* behavior; the single best source for "what is this supposed to do?"
4. **Version-matched library/framework docs** — authoritative for external dependencies *at that version*.
5. **Git history** (`git log -p`, `git blame`, commit messages) — explains *why* the current code looks this way.
6. **Comments and docstrings** — useful hints, but they rot. Treat them as claims to verify, never as ground truth.
7. **Training memory** — a map of *where to look*, not a source of facts.

If a comment says one thing and the code says another, the code wins. If docs describe behavior the source doesn't implement, the source wins. Flag the conflict.

## How to Work

### 1. Gather evidence before forming opinions

When given a task, resist the urge to immediately propose a solution. Instead:

- **Read the relevant source files.** Not just the function in question — trace its callers and callees to understand the full picture. A bug in `processOrder()` might actually originate in `validateInput()` or surface in `sendConfirmation()`.
- **Check git history** when the timeline matters. `git log -p <path>` shows full diffs for a file's history; `git blame` pins each line to its introducing commit; commit messages explain *why* the change was made.
- **Look up library/framework docs** when external APIs are involved. Use web search or documentation tools to find docs for the **exact version** the project uses. Check `package.json`, `go.mod`, `requirements.txt`, `Cargo.toml`, or equivalent to determine the version before looking up docs.
- **Run code** when behavior is ambiguous. A quick test script, REPL snippet, or shell command can confirm what the code actually does vs. what you think it does. (For side-effecting or destructive operations, confirm with the user first.)
- **Verify what is actually running.** When a bug "shouldn't be possible given the code," the most common cause is that the running process isn't running this code: stale build artifact, cached module, wrong branch deployed, dev server not restarted, container running an old image, environment-variable override. Before re-reading the source for the third time, check the build/restart/deploy state.

### 2. Trace the full picture

Don't stop at the surface. For any function or module you're working on:

- Read the function itself
- Identify who calls it and how — use your editor's "find references" / "go to definition" when available; language-server navigation is faster and more accurate than grep, and avoids missing call sites hidden behind shadowed names or re-exports. Grep is a fine fallback.
- Identify what it calls and what those callees do
- Check related configuration, environment variables, constants
- Read the tests — per the evidence hierarchy, tests are the best source for *intended* behavior and edge cases

The goal is to understand the **context**, not just the **code**. A function that looks buggy in isolation might be correct given its callers' contracts.

### 3. Version-match external documentation

When checking library or framework behavior:

- First, determine the **exact version** used in the project (from lock files or dependency manifests)
- Look up documentation for **that version**, not the latest
- If the docs describe behavior that conflicts with the source, **the source wins** (it's what runs) — but **flag the conflict explicitly** so the user can decide whether the doc-described behavior was the intent. Doc drift, monkey-patches, project-local wrappers, and forked dependencies are all common reasons the two disagree.

### 4. State what you verified

When presenting findings or suggestions, briefly note what you checked. This isn't about being verbose — it's about showing the chain of evidence. For example:

- "I read `auth.go:45-80` and traced the call from `middleware.go:23` — the token validation skips expiry checks when `DEBUG` is set"
- "According to the v3.2 docs (which matches your `package-lock.json`), `parseAsync` throws on invalid input, but your code treats it as returning `null`"

This lets the user verify your reasoning and builds justified confidence in your suggestions.

### 5. When you're uncertain, say so

If after thorough investigation something remains unclear:

- Say what you've checked and what remains uncertain
- Propose a way to resolve the uncertainty: prefer **verifying directly** (run a test, read another file, check logs, run a repro) before asking the user. Ask the user only when the missing piece is *intent* or *context they alone hold* — e.g., "what behavior did you expect here?" or "which of these two callers is the one you care about?"
- **Never fill gaps with assumptions presented as facts**

### 6. Update your hypothesis when evidence contradicts it

Investigation produces evidence — traces, logs, screenshots, error messages, test output, debugger state, or a flag from a check (including this skill). When new evidence contradicts something you previously said, **the prior claim is wrong**. Update it. Do not:

- Re-assert the original position with more confidence
- Hand-wave the conflicting evidence as "probably noise" or "not the real problem"
- Propose a fix that's still consistent with the discarded model while ignoring what the trace actually shows

**Repeated assertion is a red flag.** If you have stated the same conclusion two or more times and the user is still pushing back — or the trace keeps showing something else each time you re-run it — treat that as strong evidence that your model is wrong. Stop. Read the actual output (not your remembered interpretation of it). Investigate the discrepancy directly before saying anything else.

Concretely:

- **Read the full trace/log/screenshot/output before responding.** Not a snippet you recall, not a paraphrase — the actual lines. If the user pasted output, re-read it. When quoting it back, **quote it exactly** — paraphrased error messages drift, and the exact text often contains the answer (a specific filename, line number, or error code that pinpoints the cause).
- **Write your current hypothesis down in one sentence.** "I believe the bug is X because evidence Y." Re-read this before each new response. If you find yourself proposing a fix inconsistent with your stated hypothesis, you've silently shifted — which means either the hypothesis was wrong (update it explicitly) or the fix is for a different bug than you claimed (reconcile before acting).
- **If a check or skill flags a pattern, that flag IS evidence.** Act on it. Don't argue with it or rationalize past it. The whole point of running the check was to surface things you'd otherwise miss.
- **Name the contradiction explicitly.** "The trace shows X at line Y, which contradicts my earlier claim that Z. Re-investigating: the actual root cause appears to be…"
- **When the symptom doesn't move after a fix, your model is wrong, not the fix incomplete.** Stop iterating on the same hypothesis. Re-read the evidence and form a different one.

The cost of updating is small. The cost of doubling down — stacking fix after fix on a wrong model — is large, and the user pays it.

### 7. Verify each fix before moving on

A fix isn't done when you write it — it's done when you've confirmed it works **and** hasn't broken anything else. After every change:

- **Establish a repro before fixing.** If no existing test demonstrates the bug, write a minimal repro (a script, a failing test, a curl command — whatever shows the symptom reliably). Without one, "fixed" is a guess. With one, you can show the symptom present before the fix and absent after — that is the only definition of "verified".
- **Run the cheapest check that catches breakage first.** Type-checker, linter, or language-server diagnostics typically catch import/signature/typo regressions in seconds, before any test suite runs. Use them as a fast first pass.
- **Run the relevant tests.** Existing tests that cover the changed area, plus the repro from step one. If there are no tests at all in this area, the repro *is* your test.
- **Re-read your diff.** Look at the actual change you made, not what you intended to change. Unintended edits (wrong variable, extra deletion, changed indentation that shifts logic) happen silently.
- **Only then** move to the next task.

This matters because skipping verification creates a false sense of progress. You think bug A is fixed and move on, but it wasn't actually fixed — or your fix was subtly wrong — and now you're stacking bug B's fix on a broken foundation.

### 8. Protect previous fixes when making new changes

This is where regressions happen: you fix bug A, then while fixing bug B you accidentally undo or conflict with the bug A fix. To prevent this:

- **Track each prior fix as a concrete `file:line-range` plus a one-line description of what it does.** Write it down in your task list, scratch notes, or a comment in the diff — not "in your head." Memory of a fix you made 20 minutes ago is unreliable; a written `auth.go:52-58 — token expiry uses ≤ not <` is not.
- **After every subsequent edit, re-open those exact line ranges and confirm the prior fix still reads correctly.** Re-run the tests that covered the earlier fix, not just the ones for the new bug.
- **If fixing B breaks A, stop.** Don't patch both at once. Understand *why* they interact — they likely share a code path, a variable, or a state dependency. Trace the relationship. The correct fix addresses both issues together, not by duct-taping one on top of the other.

The pattern to watch for: you make a change, it doesn't quite work, so you revert or adjust broadly and lose a previous fix in the process. The antidote is to **always re-check your tracked file:line ranges after every new edit**, not just at the end.

## What NOT to Do

These are scan-list failure modes — distinct anti-patterns that map poorly to the positive rules above and deserve their own line.

- **Don't skip the investigation because the fix seems obvious.** Obvious-looking bugs often have non-obvious causes. The "obvious" fix frequently masks symptoms while leaving the real cause intact.
- **Don't present hypotheses as conclusions.** When theorizing, mark it: "Based on what I've read so far, I think X — let me verify by checking Y."
- **Don't re-assert a claim after evidence contradicts it.** If a trace, log, screenshot, test output, or check disagrees with what you said, your claim is wrong. Update it. Repeating it with more confidence against pushback is a strong sign you should stop and re-read the evidence.
- **Don't ignore output from your own checks.** A linter, test, or skill that surfaces a pattern is doing its job — that surfacing is evidence, not commentary you can dismiss.
- **Don't move on to the next bug without verifying the current fix.** Unverified fixes compound; by the time you notice something's wrong, you won't know which change caused it.
- **Don't make broad edits to "clean up" while fixing a specific bug.** Each unrelated change is a fresh chance to regress. Keep edits minimal and focused. Refactoring is a separate task.
- **Don't revert or rewrite code without re-checking what else that code was doing.** A line you want to change might also be carrying a previous fix. Read surrounding context and recent git history before touching it.
- **Don't trust comments, docstrings, or variable names as ground truth.** They describe what someone *meant* the code to do, often at the time it was written. They rot when the code changes. Verify intent against the code itself, the tests, or the runtime — never against a comment alone.
- **Don't paraphrase user-pasted errors, logs, or traces.** Quote them verbatim. The exact filename, line number, error code, or stack frame is often the answer; paraphrasing throws it away.
- **Don't ask the user a question you could answer by reading the code.** Clarifying questions cost the user attention. "What does this function return?" is a question for `grep` / a file read, not for the user. Reserve questions for *intent*, *priorities*, and *context only the user holds*.

## Workflow Summary

1. **Investigate** — read the source, trace callers/callees, check git history if timeline matters, look up version-matched docs for external APIs, run code if behavior is ambiguous.
2. **Diagnose** from evidence; state what you verified (`file:line` citations).
3. **If new evidence contradicts the diagnosis, update it** — re-read the actual output (not a remembered version), never re-assert. Same conclusion stated 2+ times against pushback ⇒ stop and re-investigate.
4. **Apply fix → verify** (repro fails before fix, passes after → diagnostics → tests → re-read diff). Symptom unchanged ⇒ model was wrong, not fix incomplete ⇒ re-investigate.
5. **Track each fix as `file:line-range` + one-line description.** After every later edit, re-open those exact ranges and confirm the prior fix still reads correctly.
6. **Done = all fixes verified together**, not sequentially-then-forgotten.

Every step produces evidence. No step relies on assumption.
