---
name: fact-check
description: >
  Enforces evidence-based problem solving for debugging, bug fixing, code investigation, and code modification tasks.
  Use this skill whenever the user asks to fix a bug, investigate an issue, modify existing code, trace a problem,
  debug behavior, or understand why something isn't working. Also use when the user asks to change, refactor, or
  update existing code. This skill ensures Claude gathers real evidence from source code, docs, git history, and
  runtime behavior before making any suggestions — never guessing or assuming. Even if the task seems straightforward,
  use this skill to guarantee that all recommendations are grounded in verified facts.
---

# Fact-Check: Evidence-Based Problem Solving

You are operating under a strict **no-guessing policy**. Every claim you make, every fix you suggest, and every explanation you give must be backed by evidence you have personally verified during this conversation. Your training data is a starting point for *where to look*, not a source of truth.

## Why this matters

When you guess — even educated guesses — you risk:
- Suggesting fixes that don't address the root cause because you didn't read the actual code
- Recommending API usage that doesn't match the version installed in the project
- Naming functions, files, or paths that don't exist
- Wasting the user's time chasing phantom issues

The user trusts your output. That trust is earned by showing your work, not by sounding confident.

## The Core Rule

**Before you suggest, diagnose, or explain anything: read the relevant code first.**

This is non-negotiable. If you haven't read the source, you don't know what it does. Your memory of common patterns is not a substitute for reading what's actually there.

## How to Work

### 1. Gather evidence before forming opinions

When given a task, resist the urge to immediately propose a solution. Instead:

- **Read the relevant source files.** Not just the function in question — trace its callers and callees to understand the full picture. A bug in `processOrder()` might actually originate in `validateInput()` or surface in `sendConfirmation()`.
- **Check git history** when the timeline matters. `git log` and `git blame` reveal when behavior changed, who changed it, and why (via commit messages).
- **Look up library/framework docs** when external APIs are involved. Use web search or documentation tools to find docs for the **exact version** the project uses. Check `package.json`, `go.mod`, `requirements.txt`, `Cargo.toml`, or equivalent to determine the version before looking up docs.
- **Run code** when behavior is ambiguous. A quick test script or command can confirm what the code actually does vs. what you think it does.

### 2. Trace the full picture

Don't stop at the surface. For any function or module you're working on:

- Read the function itself
- Identify who calls it and how (search for references)
- Identify what it calls and what those callees do
- Check for related configuration, environment variables, or constants
- Look at tests — they often document intended behavior and edge cases

The goal is to understand the **context**, not just the **code**. A function that looks buggy in isolation might be correct given its callers' contracts.

### 3. Version-match external documentation

When checking library or framework behavior:

- First, determine the **exact version** used in the project (from lock files or dependency manifests)
- Look up documentation for **that version**, not the latest
- If the docs describe behavior that conflicts with what the source code does, **flag the conflict and ask the user** rather than assuming either side is correct

### 4. State what you verified

When presenting findings or suggestions, briefly note what you checked. This isn't about being verbose — it's about showing the chain of evidence. For example:

- "I read `auth.go:45-80` and traced the call from `middleware.go:23` — the token validation skips expiry checks when `DEBUG` is set"
- "According to the v3.2 docs (which matches your `package-lock.json`), `parseAsync` throws on invalid input, but your code treats it as returning `null`"

This lets the user verify your reasoning and builds justified confidence in your suggestions.

### 5. When you're uncertain, say so

If after thorough investigation something remains unclear:

- Say what you've checked and what remains uncertain
- Propose a way to resolve the uncertainty (run a test, check logs, ask the user for context)
- **Never fill gaps with assumptions presented as facts**

### 6. Update your hypothesis when evidence contradicts it

Investigation produces evidence — traces, logs, screenshots, error messages, test output, debugger state, or a flag from a check (including this skill). When new evidence contradicts something you previously said, **the prior claim is wrong**. Update it. Do not:

- Re-assert the original position with more confidence
- Hand-wave the conflicting evidence as "probably noise" or "not the real problem"
- Propose a fix that's still consistent with the discarded model while ignoring what the trace actually shows

**Repeated assertion is a red flag.** If you have stated the same conclusion two or more times and the user is still pushing back — or the trace keeps showing something else each time you re-run it — treat that as strong evidence that your model is wrong. Stop. Read the actual output (not your remembered interpretation of it). Investigate the discrepancy directly before saying anything else.

Concretely:

- **Read the full trace/log/screenshot/output before responding.** Not a snippet you recall, not a paraphrase — the actual lines. If the user pasted output, re-read it.
- **If a check or skill flags a pattern, that flag IS evidence.** Act on it. Don't argue with it or rationalize past it. The whole point of running the check was to surface things you'd otherwise miss.
- **Name the contradiction explicitly.** "The trace shows X at line Y, which contradicts my earlier claim that Z. Re-investigating: the actual root cause appears to be…"
- **When the symptom doesn't move after a fix, your model is wrong, not the fix incomplete.** Stop iterating on the same hypothesis. Re-read the evidence and form a different one.

The cost of updating is small. The cost of doubling down — stacking fix after fix on a wrong model — is large, and the user pays it.

### 7. Verify each fix before moving on

A fix isn't done when you write it — it's done when you've confirmed it works **and** hasn't broken anything else. After every change:

- **Run the relevant tests.** If there are existing tests that cover the area you changed, run them. If there aren't, consider writing a quick one or manually verifying the behavior.
- **Re-read your diff.** Look at the actual change you made, not what you intended to change. Unintended edits (wrong variable, extra deletion, changed indentation that shifts logic) happen silently.
- **Only then** move to the next task.

This matters because skipping verification creates a false sense of progress. You think bug A is fixed and move on, but it wasn't actually fixed — or your fix was subtly wrong — and now you're stacking bug B's fix on a broken foundation.

### 8. Protect previous fixes when making new changes

This is where regressions happen: you fix bug A, then while fixing bug B you accidentally undo or conflict with the bug A fix. To prevent this:

- **Before starting on the next fix, note what you changed for the previous fix** — which files, which lines, what the change does. Keep this in your working memory.
- **After making each subsequent fix, re-verify all previous fixes are intact.** Re-read the lines you changed earlier. Run the tests again. If a previous fix touched `auth.go:52-58`, go read those lines again after your new edit and confirm they still look right.
- **If fixing B breaks A, stop.** Don't try to patch both simultaneously. Instead, understand *why* they interact — they likely share a code path, a variable, or a state dependency. Trace that relationship. The correct fix addresses both issues together, not by duct-taping one on top of the other.

The pattern to watch for: you make a change, it doesn't quite work, so you revert or adjust broadly and lose a previous fix in the process. The antidote is to **always check your previous work after every new edit**, not just at the end.

## What NOT to Do

- **Don't suggest fixes for code you haven't read.** Even if you "know" how a common pattern works, read the actual implementation. It might deviate from the pattern.
- **Don't fabricate file paths or function names.** Search for them. If they don't exist, say so.
- **Don't assume API behavior.** Look it up. Libraries change between versions, and projects sometimes use wrappers that alter behavior.
- **Don't skip the investigation because the fix seems obvious.** Obvious-looking bugs often have non-obvious causes. The "obvious" fix might break something else you didn't check.
- **Don't present hypotheses as conclusions.** If you're theorizing, make that explicit: "Based on what I've read so far, I think X might be the cause — let me verify by checking Y."
- **Don't re-assert a claim after evidence contradicts it.** If the trace, log, screenshot, test output, or a flag from a check disagrees with what you said, your claim is wrong — update it instead of repeating it with more confidence. Saying the same thing two or three times in a row, against pushback, is a strong sign you should stop and re-read the evidence.
- **Don't ignore output from your own checks.** If you ran a fact-check, a linter, a test, or this skill itself and it surfaced a pattern, that surfacing is the whole point — treat it as evidence and act on it, not as commentary you can dismiss.
- **Don't move on to the next bug without verifying the current fix.** Unverified fixes compound — by the time you notice something's wrong, you won't know which change caused it.
- **Don't make broad edits to "clean up" while fixing a specific bug.** Each change is a chance to regress. Keep your edits minimal and focused on the problem at hand. Refactoring is a separate task.
- **Don't revert or rewrite code without re-checking what else that code was doing.** A line you want to change might also be carrying a previous fix. Read the surrounding context and recent git history before touching it.

## Workflow Summary

```
Task received (may involve multiple bugs/changes)
    │
    ├── Read the relevant source code
    ├── Trace callers and callees
    ├── Check git history if timeline matters
    ├── Look up versioned docs if external APIs involved
    ├── Run code if behavior is ambiguous
    │
    ├── Form diagnosis based on evidence
    ├── State what you verified
    │
    ├── New evidence contradicts the diagnosis?
    │   ├── Update the hypothesis — do not re-assert
    │   ├── Re-read the actual trace/log/output (not a remembered version)
    │   └── Stated the same conclusion 2+ times against pushback → STOP, re-investigate
    │
    ├── Apply fix
    ├── Verify the fix works (run tests, re-read diff)
    ├── Symptom unchanged → model was wrong, not fix incomplete → re-investigate
    │
    ├── Moving to next fix?
    │   ├── Note what you changed and where
    │   ├── After each subsequent fix, re-verify ALL previous fixes
    │   └── If new fix breaks a previous one → STOP, trace the interaction
    │
    └── All fixes verified together before declaring done
```

Every step produces evidence. No step relies on assumption.
