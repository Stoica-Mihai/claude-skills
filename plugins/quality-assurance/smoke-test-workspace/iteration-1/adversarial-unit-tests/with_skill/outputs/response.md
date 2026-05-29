# Not a smoke-test task — this is unit testing

What you're describing — **full branch coverage for the `order-pricing`
function in your checkout module, including the negative-total edge
case** — is a *unit test* job, not a smoke test. I want to flag the
mismatch before scaffolding anything, because the two disciplines have
opposite shapes and I'd produce the wrong artefact if I treated this as
smoke.

## Why this isn't smoke testing

The `smoke-test` skill is explicitly scoped to **build-verification
suites**: 5–10 broad-but-shallow checks that prove a fresh build is
*stable enough to bother testing further*. Its own "skip" list calls
out:

> Skip it for: Unit testing or full regression testing (different
> discipline, larger scope).

Your request hits every anti-pattern for smoke:

| Property                          | Smoke test            | Your request                |
|-----------------------------------|-----------------------|-----------------------------|
| Scope                             | Whole service / API   | One function                |
| Depth                             | Broad, shallow        | Deep — every branch         |
| Edge cases (e.g. negative totals) | **Explicitly excluded** | **Explicitly required**   |
| Layer                             | API-first, end-to-end | Pure function, in-process   |
| Count                             | 5–10 checks           | As many as branches need    |
| Runtime budget                    | <2 min for the suite  | Milliseconds per case       |
| Failure semantics                 | Gate the deploy       | Gate the merge / red-green  |

A smoke suite that drilled into discount math would be too detailed
to stay under the 2-minute budget and too fragile to survive routine
pricing-rule changes — exactly the failure mode the skill is designed
to prevent.

## What you actually want

Pick whichever of these fits your workflow:

1. **`tdd` skill** (`/tdd`) — if you want to drive the implementation
   test-first: write a failing test for each branch (happy path, zero
   discount, discount == total, discount > total → clamped or negative,
   currency rounding, etc.), watch it fail, implement, watch it pass.
   This is the right tool if `order-pricing` is still being shaped or
   you want red/green/refactor discipline.

2. **A plain unit-test scaffolding pass** — if `order-pricing` already
   exists and you just want coverage. Tell me:
   - language + test runner (pytest? vitest? jest? go test? cargo test?
     junit?),
   - the function signature and a pointer to the file,
   - what "negative total" *should* do in your domain (clamp to zero?
     return an error? surface a refund credit?),

   and I'll generate a parametrised test table that covers every
   branch including the negative-discount edge case, with the
   ambiguous-spec branches flagged so you can confirm the intended
   behaviour rather than freezing in a bug.

3. **Branch-coverage tooling** — if you want the coverage *measured*,
   not just *attempted*, wire `coverage.py --branch` /
   `vitest --coverage` / `go test -cover` / `cargo llvm-cov` into the
   same pass. Happy to do that alongside option 2.

## What I will not do

Generate a `tests/smoke/` file pretending unit tests are a smoke
suite. That would dilute your real smoke gate (when you build one) and
mis-shelve coverage work that belongs in the unit-test tier.

Tell me which of the three options above you want and share the
function — I'll take it from there.
