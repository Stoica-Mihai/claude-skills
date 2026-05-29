# Post-deploy smoke suite for axum-app

**Detected stack**: Rust / axum 0.7, tokio runtime, `cargo test` runner.
Routes from `src/main.rs`: `GET /health`, `GET /users/:id`, `POST /orders`,
`GET /orders/:id`. No CI config found.

**Target mode**: HTTP against a **live deployed environment** (not in-process
`router().oneshot()`), driven by `reqwest` and gated on `SMOKE_BASE_URL`.

## Idempotency design (the key constraint)

The user said these run against the live env. The fixture's only write path
is `POST /orders`, which mutates persistent state. Running the canonical
`create_order_happy_path` check from the axum template against prod would
leak a fake order **every deploy**. So:

- The write check is **replaced** with two auth-rejection probes
  (`create_order_without_auth_is_rejected`, `create_order_with_invalid_auth_is_rejected`)
  that POST to `/orders` but are guaranteed to be rejected at the auth gate
  **before any state mutation**.
- Verified in `src/main.rs:53-56`: `create_order` checks
  `auth.starts_with("Bearer ")` and returns `401` **before** acquiring the
  state lock. No `next_id` increment, no `orders.insert`.
- All other checks are GETs.

Result: the entire suite is safe to run on every prod deploy.

## Proposed checks (6, well inside the 5-10 budget)

1. `GET /health` → 200, body `{"status":"ok"}` — basic liveness.
2. `GET /users/1` → 200, shape-correct — primary read path + user store live.
3. `GET /users/99999999` → 404 — error path wired, routing intact.
4. `POST /orders` with no `Authorization` header → 401 — auth gate live,
   no state mutation.
5. `POST /orders` with non-Bearer auth scheme → 401 — auth prefix check is
   the actual gate, not just header presence.
6. `GET /orders/99999999` → 404 — order store reachable, error path wired.

Dropped from the canonical template:
- `create_order_happy_path` — non-idempotent against a live env.

## Files written

- `tests/smoke.rs` — the 6-check suite, all idempotent, gated on
  `SMOKE_BASE_URL`. Each check logs `status`, correlation id
  (`x-request-id` / `x-correlation-id`), and response body to stderr on
  every run so failures at 3 AM are diagnosable from CI logs alone.
- `Cargo.toml.snippet` — `[dev-dependencies]` additions: adds `reqwest`
  with `rustls-tls` + `json` (no openssl in CI). `tokio` and `serde_json`
  are already in the fixture's `Cargo.toml`.

## How to run

```bash
# Against a deployed environment:
SMOKE_BASE_URL=https://api.staging.example.com \
    cargo test --test smoke -- --nocapture

# Against local `cargo run`:
SMOKE_BASE_URL=http://localhost:8080 \
    cargo test --test smoke -- --nocapture

# In CI, make missing env a hard error instead of skip:
SMOKE_BASE_URL=... SMOKE_REQUIRE_BASE_URL=1 \
    cargo test --test smoke -- --nocapture
```

By default, when `SMOKE_BASE_URL` is unset each test logs a skip line and
passes — so unrelated `cargo test` runs in CI don't fail on missing env.
Setting `SMOKE_REQUIRE_BASE_URL=1` flips that to a hard failure for the
production gate job.

## Runtime budget

Wall-clock: ~1-3 s against a healthy environment (6 parallel `#[tokio::test]`
calls, 5 s per-request timeout, 3 s connect timeout). Well inside the
2-minute smoke budget.

## TODOs the user must wire in

- `KNOWN_USER_ID = 1` and `MISSING_USER_ID = 99_999_999` are placeholders.
  Confirm `id=1` is a seeded fixture in every environment (staging, prod).
  If user ids are namespaced per env, lift these to env vars.
- The fixture's `/health` is unauthenticated. If the deployed service puts
  `/health` behind auth, plumb `SMOKE_TOKEN` through the `client()`
  builder (`.default_headers(...)`).
- Optional: gate prod promotion in the deploy pipeline on
  `cargo test --test smoke` exit code. No CI config was detected in the
  fixture, so no Actions/GitLab snippet is included by default — happy
  to add one if you point at the pipeline.

## Failure-debugging expectations

- Every check writes status, correlation id, and body to stderr on every
  run (not just failures) so a flaky test gives one full last-known-good
  vs. failing diff.
- Treat a failing smoke run as **stop-the-line** — do not promote.
- If a test starts flaking, quarantine via `#[ignore]` and fix within
  the sprint; do not delete.
