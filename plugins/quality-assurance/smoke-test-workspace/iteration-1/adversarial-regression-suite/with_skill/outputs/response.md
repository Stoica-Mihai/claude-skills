# Re: regression test suite for the payments service

Short answer: I have to decline the core request. This `smoke-test` skill is
deliberately **not** a regression-suite generator, and using it to scope a
50-endpoint behaviour-equivalence suite for a stateful payments service would
mis-serve you.

## Why smoke ≠ regression

The two suites have opposite shapes:

| Dimension          | Smoke (this skill)                              | Regression (what you're asking for)                              |
| ------------------ | ----------------------------------------------- | ---------------------------------------------------------------- |
| Goal               | "Is the build stable enough to test further?"   | "Did any observable behaviour change vs last release?"           |
| Breadth            | Broad-but-shallow, 5-10 critical happy paths    | Comprehensive — every endpoint, every state transition, edge cases, validation rules, error wording |
| Depth              | One assertion per path (status + shape)         | Many assertions per path; often snapshot/golden-file diffs       |
| Runtime budget     | < 2 minutes wall-clock                          | Tens of minutes to hours; runs less frequently                   |
| State              | Idempotent, read-only-safe, prod-runnable       | Sets up complex fixtures, walks full state machines, may need a dedicated env |
| On failure         | Stop the line, reject the deploy                | File a behavioural-diff ticket; may or may not block release     |
| Suite size         | 5-10 (small/medium), up to 20-50 (large)        | Hundreds to thousands of cases; grows with the product           |
| Authoring style    | Hand-curated critical paths                     | Often spec-driven, contract-driven, property-based, or recorded  |

For ~50 endpoints plus complex state machines, a regression suite is the
opposite discipline from what this skill produces. Specifically it needs at
least:

- **Endpoint coverage matrix** — every (endpoint × method × auth state × known
  error class) cell, not a curated 10.
- **State-machine coverage** — explicit transition tests for each state
  (`authorised → captured → refunded`, declines, partial captures, chargebacks,
  3DS step-ups, idempotency-key replays, etc.). Property/model-based testing
  (Hypothesis, fast-check, stateful proptest) is usually the right tool here.
- **Contract / schema diffing** — OpenAPI or Pact contract tests so a
  field rename or status-code change is caught at the boundary, not by a
  hand-written assertion.
- **Golden-response snapshots** for read endpoints to catch subtle payload
  drift between releases.
- **Replay-style tests** against recorded fixtures (e.g. VCR, mitmproxy
  cassettes) for third-party PSP integrations — payments services almost
  always sit in front of Stripe/Adyen/etc. and you cannot regression-test
  those live on every PR.
- **Idempotency & double-spend tests** — same `Idempotency-Key`, retried
  POST, partial-failure recovery. This is payments-specific and must not be
  approximated.
- **Money-handling invariants** — currency rounding, minor-unit math, FX,
  ledger double-entry balance. Best caught with property-based tests, not
  example-based regression.
- **Data setup / teardown infra** — dedicated regression env, deterministic
  seed data, migration-aware fixtures. None of which a smoke skill scopes.

None of that fits inside a "<2-minute, 5-10 check, idempotent, read-only-safe"
contract. Forcing it would either (a) produce a suite that calls itself
"regression" but only covers happy paths, giving you false confidence, or
(b) blow past the smoke contract and break the gate it is meant to be.

## What I'd recommend instead

1. **Scope the regression suite with the right discipline.** Drivers are
   usually: an OpenAPI/contract source of truth, a state-machine model, a
   set of recorded PSP interactions, and a property-based layer for money
   and idempotency invariants. This is a multi-week design exercise, not a
   scaffold generator. Frameworks worth shortlisting:
   - Contract / schema: Schemathesis, Dredd, Pact
   - Stateful property tests: Hypothesis (`RuleBasedStateMachine`),
     fast-check model-based, proptest-state-machine
   - PSP replay: VCR.py, Polly.js, WireMock recordings
   - Golden snapshots: syrupy (Python), Jest snapshots, insta (Rust)
   - Test data: factory libraries + migration-aware seed scripts
2. **Add a smoke gate alongside it** — this is exactly what this skill is
   for, and it pairs well with a heavy regression suite. The smoke suite
   becomes the < 2-minute gate that protects the 30-minute regression suite
   from running against fundamentally broken builds. Concretely, for a
   payments service I would scope something like:
   - `GET /health` → 200
   - `GET /readyz` → 200 (DB + PSP reachable)
   - `POST /auth/token` with a known service account → 200, valid JWT
   - `GET /payments/{known_fixture_id}` → 200 + shape-correct
   - `POST /payments` without auth → 401
   - `POST /payments` with auth + idempotency key + ephemeral test card →
     201 + id (only against non-prod, guarded by env flag)
   - `GET /payments/{id}` after #6 → echoes the same body
   - One read against the ledger / DB to prove dependency liveness
   - 404 on a known-missing payment id

   That is the suite this skill can scaffold today (give me the stack —
   FastAPI / Express / Go / axum / other — and I'll run the detector and
   emit a runnable scaffold with `TODO`s for `SMOKE_BASE_URL` and
   `SMOKE_TOKEN`).

## TL;DR

I can't produce a real regression suite for a 50-endpoint payments service
from this skill, and pretending otherwise would either give you a curated
happy-path subset mislabelled as regression, or a runaway suite that breaks
the smoke-gate contract. Happy to:

- **(A)** scaffold a proper smoke gate for the payments service right now
  (skill's sweet spot), and/or
- **(B)** sketch a regression-suite *architecture* — contract tests +
  state-machine model + PSP replay + property-based money invariants — as
  a separate piece of work outside this skill.

Tell me which (or both) and, if (A), what stack the service is on.
