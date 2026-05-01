---
version: 1.1.0
name: tdd
description: >
  Test-Driven Development workflow. Use when the user asks to work test-first,
  says "tdd", "/tdd", "write tests first", "red green refactor", "test-driven",
  or explicitly wants failing tests before implementation. Also trigger when
  the user says "add tests for X then implement" or "start with a test".
  Do NOT trigger on general coding requests that don't mention test-first intent.
user-invocable: true
argument-hint: "[feature or bug description]"
---

# Test-Driven Development

TDD uses tests as a design tool. The test suite is a byproduct — the real output
is clean design that emerges from writing tests first. Code is only written to
satisfy a failing test.

---

## Before Starting

Gather context before writing anything. A wrong assumption means wrong tests.

1. **Find existing tests.** Match their framework and style exactly. Only ask
   about tooling if nothing exists yet.
2. **Read code this task integrates with.** Discover interfaces rather than
   inventing them.
3. **Clarify behavior if vague.** If the request is ambiguous ("add authentication"),
   ask for a concrete scenario: "What should happen when a user logs in with the
   wrong password?" One focused question beats a checklist.

---

## The Cycle: Red -> Green -> Refactor

Every unit of work follows three steps. Never skip the third.

### Red — Write a failing test

- Pick the next smallest piece of behavior
- Write a test that will pass once that behavior exists
- Assert what you actually expect, not a placeholder. If you don't know the
  exact value (e.g., a specific error message string), assert the contract
  you care about (e.g., "raises `ValueError`") rather than guess. Tweaking
  the assertion later to match whatever the implementation happens to emit
  is test-after, not test-first — see Pitfalls.
- Run it — confirm it **fails for the right reason** (not a syntax error or import failure)
- If writing the test is hard, that's a design signal: the interface isn't clear yet

### Green — Minimal code to pass

- Write only enough production code to make the failing test pass
- Inelegant or hardcoded is fine here — correctness first
- Run all tests — the new one passes and nothing else broke

### Refactor — Clean up, behavior unchanged

- Improve names, remove duplication, simplify logic
- Refactor both production code and test code
- Run tests after every small change
- This step is mandatory. Skipping it turns TDD into messy code accumulation

Repeat for each new behavior.

---

## Picking What to Test Next

Before writing any code, list the scenarios:

- What's the simplest behavior that must exist?
- What are the edge cases and boundaries?
- What should happen on invalid input?

Work simplest to most complex. Each test should force a small, specific
generalization in the production code. As tests get more specific, the code
gets more generic — if logically equivalent cases wouldn't pass without
changes, the production code is still too specific.

**For bug fixes:** write a test that reproduces the bug first (it fails),
fix it (it passes), refactor. The test is regression protection forever.

---

## Test Structure: Arrange -> Act -> Assert

```
Arrange (Given):  set up the object/state under test
Act     (When):   call the behavior being tested
Assert  (Then):   verify the result matches expectation
```

One behavior per test. Multiple assertions are fine if they verify the same
behavior — split the test if they don't.

---

## Test Doubles

Default to real objects. Only introduce doubles when the real dependency is:
- **Slow** (database, network, filesystem, external API)
- **Non-deterministic** (current time, randomness, third-party service)
- **Hard to set up** to the required state

Prefer the classical (Detroit) approach: verify state (what changed), not
interactions (what was called). Over-mocking couples tests to implementation
and breaks on refactoring.

Types: **stub** (canned return value), **mock** (verifies calls happened),
**fake** (simplified working implementation), **spy** (records calls for later assertion).

---

## Special Cases

### Legacy code without tests

You can't safely refactor untested code. The approach:
1. Write **characterization tests** that capture current behavior (even if buggy)
2. Once covered, modify using normal Red-Green-Refactor
3. For known bugs: write a test exposing the bug, then fix it

### Spikes (unclear requirements)

TDD requires knowing what "correct" looks like. If you don't:
1. Do a **spike** — exploratory code, no tests, to understand the problem
2. Throw the spike away
3. Write the real implementation test-first, informed by what you learned

Never let spike code become production code.

---

## The Test Pyramid

```
       /\
      /E2E\        few, slow — critical user journeys only
     /------\
    / Integr \     moderate — components work together
   /----------\
  /  Unit (TDD)\   many, fast, cheap — TDD's home
 /--------------\
```

TDD unit tests are the foundation but not sufficient alone. Combine with
integration and acceptance tests for full coverage.

---

## Pitfalls

| Pitfall | Fix |
|---------|-----|
| Skipping refactor step | It's mandatory — the #1 TDD failure mode |
| Tests depending on each other | Each test must be fully independent |
| Testing implementation, not behavior | Test interfaces and outputs, not internal calls |
| Over-mocking | Default to real objects; mock only what's genuinely awkward |
| Writing code before a failing test | If there's no red, go back and write the test |
| Editing the test's expected value to match what the implementation produced | Tests specify the contract; implementation conforms to tests. If the assertion was wrong or over-specific, change it **deliberately** (back to red, then green again) — not silently while debugging to green. If the exact value was incidental, assert the looser contract (type, shape, key invariant) instead of pinning a string you guessed at. |
