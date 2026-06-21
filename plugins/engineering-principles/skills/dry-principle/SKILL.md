---
name: dry-principle
description: >
  Enforces DRY (Don't Repeat Yourself) thinking across all programming tasks — writing new code,
  reviewing code, fixing bugs, refactoring, editing config, schemas, tests, and documentation.
  Use this skill for ANY coding or programming-related task: feature implementation, bug fixes,
  code review, refactoring, writing tests, editing configuration, database schema changes,
  build system modifications, or documentation updates. This skill should trigger whenever
  Claude is about to write, modify, or review code or code-adjacent files. Even if the user
  doesn't mention "DRY" or "duplication", this skill applies to all software engineering work.
---

# DRY Principle

Apply DRY thinking to every programming task — not as a pedantic rule, but as a design instinct.
DRY means every piece of **knowledge** has a single, authoritative representation in the system.
The key word is knowledge, not code. Two identical-looking code blocks might represent different
knowledge (and should stay separate). Two different-looking blocks might encode the same business
rule (and should be unified).

The test: "If this knowledge changes, how many places do I need to update?" If the answer is
more than one, that's a DRY violation worth examining.

## Run this as a multi-pass sweep

The different kinds of duplication don't just *look* different — they're found by
different search motions, and that's the catch. Magic values surface when you *scan literals*.
Knowledge duplication surfaces when you *ask what changes together*. Wiring duplication surfaces
when you *compare interaction shapes* across siblings. Symbol↔label duplication surfaces when
you *match a typed token against a bare string in another file*. Same-file scattered duplication
surfaces when you *read look-alike function bodies side by side*. Per-instance duplication
surfaces only when you *picture the component multiplied across every screen, row, or tab it
renders into* — it's invisible in the source, which appears exactly once. These are genuinely
different mental questions, and the moment you lock onto one — say, hunting magic numbers — you stop
seeing the others, because you're no longer asking their question. This is why a single
read-through reliably catches the loudest one or two categories and silently walks past the
rest. It isn't that the rest are subtle; it's that you weren't looking with the right lens.

So don't try to see everything in one look. Make one focused pass per lens, switching the
question you ask each time, and keep a running note of which passes you've completed so you
don't circle the same ground. A later pass routinely finds things an earlier one couldn't —
not because they were hidden, but because you were asking a different question. The passes
(each links to its worked detail in `references/patterns.md`):

1. **Knowledge & business rules** — the same policy, validation, or calculation in more than
   one place; parallel structures kept in sync by hand; redundant or derivable state; scattered
   config. Ask: *"if this rule changes, how many places do I edit?"*
   → patterns.md › Knowledge duplication.
2. **Per-instance / fan-out state** — screen-independent knowledge (a fetch, a timer, a cache, a
   "pinned" / "selected" flag) living inside a component the framework instantiates per screen /
   row / tab. The source appears exactly once, so this is invisible to every text-based lens —
   it only duplicates at runtime, and it's the one that's also a latent desync *bug*, not just
   waste. Ask: *"if there were two monitors or ten rows, would this run or store twice — and does
   it need to?"* → patterns.md › Per-instance and fan-out duplication.
3. **Magic values & boundary literals** — unnamed literals that carry meaning; `0` / `1` / `-1`
   comparisons that really ask a semantic question; stringly-typed code ignoring an enum that
   already exists. Ask: *"does this literal mean something, and does a name for it already
   exist?"* → patterns.md › Code-level duplication.
4. **Repeated logic, parameters & orchestration** — copied blocks with one or two values
   changed; parameter sprawl; the same `begin/try/commit/rollback` or `load→auth→authorize`
   wrapped *around* a varying call. Ask: *"what did every caller do around the interesting
   line?"* → patterns.md › Code-level duplication (repeated logic, parameter sprawl) and
   Call-site duplication.
5. **Cross-file siblings, wiring & symbol↔label** — 3+ sibling files exposing the same outward
   shape (signal triples, event sets, prop interfaces, repeated UI elements/layouts/tokens); a
   handler's token versus its user-facing label/route/flag living as a bare string in another
   file. Ask: *"do the siblings share an interface? does this name reappear as a literal
   somewhere else?"* → patterns.md › UI components, Interaction and wiring, Symbol / label
   duplication.
6. **Same-file scattered & beyond-code** — the same 4-line block embedded in three functions of
   one file; duplicated test setup, config, docs, or schema constraints. Ask: *"read the
   look-alike bodies side by side — what repeats?"* → patterns.md › Beyond code (same-file
   scattered scanning is in "How to apply", below).

Scale the sweep to the work: a one-line fix collapses to near-nothing (a quick glance and
you're done), but a real review or refactor earns all six deliberate passes. When you
finish, fold the hits from every pass into one consolidated set of findings rather than
reporting each pass separately — see "Communication".

When the codebase is large enough that you fan the sweep out across several readers or
subagents, partition the work by *concern* — data flow, wiring, theming, per-instance state —
not by directory. A module-by-module split feels tidy but is blind to exactly the cross-module
and runtime-instantiation duplication that hides best; each reader sees one folder and every
file in it reads fine on its own. Carry a short ledger of what you rejected and *why* from one
pass to the next, so a later pass doesn't re-flag a coincidental match you already cleared. You
know you've converged when a fresh deep pass turns up only one-line nits — literal zero is never
provable on a live codebase, so stop when the angles run dry, not when you've "proven" emptiness.

For a whole-repository audit specifically — "find all the duplication in this codebase", a large
refactor, a pre-release cleanup — fan the six passes out **one agent per lens** (giving each
agent a single question is what stops it drifting across lenses). Two ways to run it:

- **Deterministic (preferred):** call the `Workflow` tool with the bundled script. A request for
  a whole-repo DRY audit *is itself the opt-in* — this skill instruction authorizes the call, so
  run it directly: don't ask the user to confirm again, and don't downgrade to the fallback to
  "skip the round-trip." `Workflow({ scriptPath: "<this skill dir>/scripts/dry-sweep.js", args: {
  scope: "<repo or path>", patternsPath: "<this skill dir>/references/patterns.md" } })` spawns
  exactly six fixed-label lens agents in parallel, then one merge agent (cross-lens dedup,
  Rule-of-Three count, leverage-ranked report) — identical structure every run.
- **Fallback (guidance only):** use this *only* when the `Workflow` tool is genuinely unavailable
  in this environment. Then do it by hand following `references/parallel-sweep.md` — same agent
  tree, but the model improvises the spawn, so the shape varies run to run.

Either way, read `references/parallel-sweep.md` for the *why*: the rule that cross-cutting lenses
must keep whole-repo view rather than being directory-split, and why the Rule-of-Three count has
to live in the merge step. Don't reach for any of this on an ordinary edit — the fan-out only
pays off at repo scale.

Once you have a batch of findings to *act* on, read `references/applying-fixes.md` before
touching code. Finding duplication is the safe half; removing it is where DRY regresses — a
hoist that changes lifecycle, a "shared" helper that merged two things which only looked alike,
a singleton hoist that globalizes state which should have stayed per-instance. That reference
covers the execution order (foundational and subsuming fixes first, so you don't polish code
you're about to delete), the failure mode specific to each fix type and how to check it, and the
step-by-step singleton hoist for the per-instance lens — the one fix that changes runtime
structure rather than text, so it's the easiest to get wrong.

## What to look for

The six lenses above, under "Run this as a multi-pass sweep", *are* the scan index — each names
what to look for and the question that surfaces it. The full catalogue behind them — every
duplication family with before/after examples across languages and frameworks (knowledge,
per-instance, code-level, beyond-code, UI, wiring, symbol↔label, call-site) — lives in
`references/patterns.md`. Read it when doing a real review or audit; an ordinary edit only needs
the lens list and tests above. The guardrails below apply on every task regardless.

## Guardrails: when NOT to deduplicate

DRY's biggest failure mode is premature or wrong abstraction. These guardrails are just as
important as the principle itself.

### A candidate is a hypothesis, not a finding

A duplication you spotted by pattern — two blocks that look alike, the same literal in three
files — is a *hypothesis*, not a finding. Before you report it or act on it, open every site and
read it in full, including the surrounding code, and actively try to *disprove* the match.
Surface similarity is cheap to notice; the value of the review is the deeper look that reveals
whether the dedup is actually possible. More often than you'd expect, a factor visible only in
the real code disqualifies the merge:

- One site has an error path, a retry, an exit-code check, or an edge case the others lack.
- Two blocks read alike but consume different outputs — one needs a parser on stdout, the other
  only the exit status — so unifying them forces a worse interface onto both.
- The literals are near but not equal (`-0.3` vs `-0.03`): typo-level proximity, not a shared
  value. Merging couples two unrelated constants.
- The divergence is *intentional* — noted in a comment, an established convention, or project
  memory. "Fixing" it reintroduces the bug the divergence was working around.
- The two change for different reasons (the coincidental-similarity test below); they only look
  alike at this moment in time.

Spend the effort to find that factor before you flag anything. A candidate that survived a
genuine attempt to disprove it is worth reporting; a surface match passed along unchecked is
noise — it wastes the reader, and if acted on, it breaks working code. When the deeper look
*does* disqualify a candidate, record *why*: that reasoning is as valuable as the findings, and
it stops the next pass (or the next reviewer) from re-flagging the same thing.

### The Rule of Three

Two instances of similar code are not enough evidence to abstract. Wait for three occurrences —
by the third time, the real pattern is visible and you can design a good abstraction. On the
first or second occurrence, note the similarity but leave it alone unless the duplication is
clearly the same piece of knowledge.

### Coincidental similarity is not duplication

Two code blocks can look identical today but exist for different reasons. Ask: "Do these change
for the same reason, at the same time, by the same person?" If not, they represent different
knowledge that happens to look alike right now. Merging them creates coupling between unrelated
concerns — when one changes, the shared abstraction must accommodate both, harming both.

**Example:** A `validateUserInput()` and `validateAPIResponse()` might have identical checks
today. But user input validation changes when the UI changes, while API response validation
changes when the upstream API changes. These are different pieces of knowledge — keep them
separate.

### The wrong abstraction is worse than duplication

Sandi Metz: "Prefer duplication over the wrong abstraction." Watch for these warning signs
that an abstraction has gone wrong:

- A shared function accumulating boolean parameters and conditional branches to handle
  "slightly different" callers
- A base class where subclasses override most methods
- A "utility" module that every file imports but each uses differently
- Adding a new feature requires modifying shared code in a way that might break other callers

When you spot these, the fastest way forward is often back: inline the abstraction into its
callers, remove what each caller doesn't need, then re-examine whether a genuine shared
pattern exists.

### YAGNI complements DRY

Don't build abstractions for hypothetical future duplication. "We might need this in three
other places someday" is not a reason to abstract today. Abstract when you actually have the
duplication, not when you imagine you might.

## How to apply this

### When writing new code

1. **Before writing, search for existing helpers.** Scan the places this codebase keeps
   shared knowledge:
   - The file you're editing and its adjacent siblings in the same directory
   - Utility / helper / shared modules (common names: `utils/`, `lib/`, `common/`, `shared/`,
     `helpers/`)
   - Type and constant modules (`constants.ts`, `types.ts`, `enums.rs`) — existing string
     unions, enums, or branded types the literal you're about to hardcode may already live in
   - Central homes for cross-cutting concerns (auth, logging, HTTP clients, db helpers,
     feature flags)
   - **The standard library.** Before writing a helper that does generic data manipulation —
     cloning a map, checking membership, equality, sorting, reversing, finding, mapping,
     filtering, deduping, batching — check whether the language's stdlib already provides it.
     This is especially worth a check for newer stdlib additions: Go's `maps.Clone` /
     `slices.Contains` / `cmp.Or`, Python's `itertools.batched` / `functools.cache`,
     JavaScript's `Array.prototype.findLast` / `Object.groupBy`, Rust's `slice::is_sorted` —
     these regularly replace hand-rolled utilities that were written before the stdlib caught
     up. A 4-line helper that wraps a single stdlib call is duplicated knowledge with
     extra steps.

   If a helper, constant, config value, or component already does what you need, use it. If
   one *almost* does, consider extending it rather than writing a parallel version — but only
   when the two callers really share the same knowledge (see "Coincidental similarity" above).
2. If you're about to write something that looks like existing code, pause and ask: is this
   the same knowledge? If yes, extend or reuse the existing implementation. If no (different
   reasons to change), write it fresh.
3. Extract shared components **before** duplicating them. If you know two callers need the
   same thing, write the shared version first.
4. **Scan for magic values.** Before finishing, review your code for any literal numbers or
   strings that carry meaning — timeouts, thresholds, status codes, sizes, URLs, format
   strings. Don't skip small values: `0`, `1`, `-1` in comparisons often encode state
   boundaries that deserve a name or helper. Name them. If the same value already exists
   as a constant elsewhere, reuse it.
5. **Scan for repeated patterns.** If you just wrote a block of logic that mirrors something
   nearby, extract a helper function immediately rather than leaving two copies.

### When reviewing or modifying existing code

This is where the multi-pass sweep earns its keep — run the passes from "Run this as a
multi-pass sweep" over the area you're touching, switching the question each pass. The points
below are the same lenses stated as actions:

1. Notice duplication in the area you're touching. You don't need to fix every DRY violation
   in the codebase — focus on the code you're already changing.
2. If you find duplicated knowledge that affects your change, flag it. Suggest a concrete
   refactor if the path is clear, or note it as tech debt if the fix is complex.
3. If you're about to copy-paste-modify, stop. Can you parameterize the existing code instead?
   But only if the variation represents the same underlying knowledge.
4. **Look sideways before finishing.** When the module you're touching has 3+ sibling files
   at the same level (components in `components/`, handlers in a route package, services
   under `services/`, structs implementing the same trait, views in an MVC app), take 30
   seconds to diff their *interface surfaces* — exported functions, emitted events, signal
   names, method signatures, prop types. If three siblings expose the same outward shape in
   parallel (same signal triples, same event set, same prop interface), that's the Rule of
   Three across files, and it's exactly the archetype the rule was designed to catch.
   In-file review misses this every time because each file reads fine on its own. This is the
   cross-file pass (pass 5) — if your earlier passes keep coming up empty but something still
   feels off, that's the signal to widen the lens: the duplication lives *between* files rather
   than within one, and only a sideways diff of sibling interfaces will surface it.

5. **Cross-check handler ↔ label pairs.** For every named action the module wires — a key
   binding, route, CLI flag, command, event, metric, env var, permission, localization key —
   confirm the *user-visible* name comes from the same source as the handler matches on, not
   a parallel string literal in a sibling file. This duplication is invisible to
   structural diffs because the two sides aren't shaped alike (typed match arm vs. bare
   string), so it survives narrow DRY sweeps. See patterns.md › Symbol / label duplication.

6. **Scan within a single file for scattered duplication.** Cross-file scanning catches
   "same function name in two packages." Within-file scanning catches "same 4-line block
   embedded inside three different functions of the same file." The latter is invisible to
   anyone reading one function at a time and easy to miss when reviewing diffs that touch
   only one function. The trick: when you're in a file with several similarly-shaped
   functions (multiple `summarize*`, `format*`, `parse*`, `handle*`, or all the methods on a
   struct), pull up each one and read the bodies side-by-side. Identical literal boundaries
   (`if len(runes) > 40`), identical setup/teardown shapes, identical error-formatting calls
   embedded in different functions are the typical hit. Same-file scattered duplication is
   especially common in:
   - Utility modules with many small functions
   - Formatter/renderer/serializer modules where each function handles a different type
   - Handler/dispatcher modules where each case has its own preamble
   - Test files (DRY the setup, not the intent — see patterns.md › Beyond code)

### When fixing bugs

A bug that exists in duplicated code probably exists in every copy. After fixing it in one
place, search for other instances of the same logic. If you find copies, consider whether
this is the right time to unify them — but only if they genuinely represent the same knowledge.

## Communication

When you spot DRY issues, be specific and practical:

- Name what knowledge is duplicated and where
- Explain whether it's worth fixing now or just noting
- If recommending a refactor, show the concrete approach
- If recommending against deduplication (coincidental similarity, wrong abstraction risk),
  explain why the duplication is actually healthy

Don't lecture about DRY in the abstract. Apply it through your actions — write DRY code,
flag violations when relevant, and protect against over-abstraction. The goal is better
software, not adherence to a principle for its own sake.
