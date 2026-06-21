# Applying dedup fixes (audit → refactor)

A DRY audit produces a list of findings; this is how to *act* on it without trading duplication
for breakage. Finding duplication is the cheap, low-risk half. **Removing** it is where DRY
actually goes wrong: a hoist that changes lifecycle, a "shared" helper that merged two things
which only looked alike, an abstraction that grows a boolean the moment the second caller hits
it. Every guardrail in the skill's "when NOT to deduplicate" section is tested here — at apply
time, against real code, not at find time against a hunch.

## Sequence the batch

Order is not cosmetic. Wrong order means refactoring code you're about to delete, or updating
call sites against a single source that doesn't exist yet.

1. **Foundational first.** A fix that *creates the single source* others will reference goes
   before the fixes that consume it. Add the `Theme.percent()` helper / the registry singleton /
   the shared component first; *then* update its call sites. An audit usually lists both halves
   as separate findings — they're one ordered job, not two.
2. **Subsuming first.** A fix that deletes or rewrites a span ranks before any cosmetic fix
   inside that span. If hoisting a registry erases 25 bare literals, don't first go name those
   25 literals — the hoist deletes them. Do the structural move; the cosmetic findings inside it
   evaporate.
3. **Mechanical last.** Pure token sweeps (magic number → constant) are independent and
   low-risk; do them after the structural moves settle, or they churn against the bigger
   refactors and you resolve the same merge twice.
4. **Independent fixes can run in parallel** (separate worktrees) — but only ones touching
   disjoint files. Two fixes editing the same file must serialize.

## One dedup per commit, behaviour-preserving

Each fix is its own commit, and each commit must not change behaviour — a dedup is a refactor,
not a feature. This keeps a regression bisectable: if something breaks, the offending
unification is one revert away, not buried in a 20-fix mega-commit. Resist folding "while I was
here" tweaks into a dedup commit; they destroy the one property that makes the batch safe.

## Per-fix verification — the failure mode is specific to the fix

The dangerous step is the unification itself. Each kind fails its own way, so each has its own
check:

| Fix | How it goes wrong | Check before committing |
|---|---|---|
| Extract shared helper / component | The call sites only *looked* identical (coincidental similarity); you've now coupled things that change for different reasons. | Diff every site you're folding in. Confirm they encode the *same knowledge*, not the same shape today. If one carries an edge case, comment, or error the others lack — stop, they're different. |
| Replace magic literal with a constant | Near-identical numbers that mean different things get merged (`_pillSkew -0.3` is not `cardSkew -0.03`). | Confirm the literal means the *same thing* at every site. Same value ≠ same concept. Two concepts that happen to share a number stay separate. |
| Merge parallel data structures | A site relied on touching one half alone; the index-coupling wasn't actually total. | Confirm every reader and writer treated them as one unit. If any code mutated one array without the other, the coupling was incomplete and merging breaks it. |
| Lift call-site orchestration into a wrapper | The "identical" preludes had a subtle ordering or error-handling difference. | Confirm the wrapper reproduces each caller's order, error path, and early returns exactly. |
| **Hoist per-instance state → singleton/service** | Changes runtime structure, not just text — the delicate one. | See "The singleton hoist" below. |

## The singleton hoist (the per-instance / fan-out fix)

This is the fix for the Pass-2 lens and the riskiest in the batch, because it changes *runtime
structure*. You're moving state out of a component the framework instantiates N times into one
shared owner. Done wrong it breaks reactivity, or commits the **inverse bug**: globalizing state
that was supposed to stay per-instance.

1. **Split the state precisely.** List every member of the per-instance component and label each
   *screen-dependent* (this bar's hover, this row's measured geometry, this instance's
   open/closed) or *screen-independent* (the fetch, the timer, the parsed global config, the
   "pinned"/"selected" value that should be one shared decision). Only the screen-independent
   half moves.
2. **Move the independent half to the singleton/service** — the data, the timer, the network
   client, the cache. One owner now.
3. **Rewire each instance as a thin view that *binds* to the service.** Do not copy values out
   of the service into local state — that re-creates the duplication you just removed.
4. **Guard the inverse bug.** Re-read what you moved: did any genuinely per-instance state ride
   along by accident? A singleton holding what should be per-bar makes *all* monitors share one
   cursor / one selection / one scroll position — a worse desync than the one you set out to fix.
5. **Preserve lifecycle.** A singleton initialises once and never tears down with a bar. Confirm
   nothing depended on per-instance construction/destruction order, and that the service starts
   before its first reader and outlives every reader.
6. **Verify with the multiplier that exposed the bug.** Two monitors, ten rows — confirm one
   fetch, one timer, and that *all* views update together. That's the proof the hoist both
   removed the duplication and kept the behaviour.

## Re-sweep after the batch

Hoisting and extracting routinely uncover a second layer — once the registry is a singleton, the
duplication *it* was hiding becomes visible. After applying a batch, re-run the lenses that
touched the changed files, carrying the rejection ledger so cleared items don't return. Converge
when a fresh pass over the changed area turns up only one-line nits — the same stop rule as the
sweep itself.
