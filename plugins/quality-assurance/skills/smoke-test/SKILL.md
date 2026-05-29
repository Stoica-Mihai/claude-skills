---
name: smoke-test
description: >
  Designs and scaffolds smoke-test suites (build-verification tests) for web
  services, APIs, and software systems. Use this skill whenever the user
  asks to "add smoke tests", "set up build verification", "write a fast
  test that proves the deploy isn't broken", "what should my smoke tests
  cover", "wire smoke tests into CI", or anything else about catching
  catastrophic failures before downstream testing. Also trigger on
  "BVT / BAT", "intake testing", "sanity vs smoke", "build acceptance".
  The skill detects the project's stack (Python/FastAPI, Node/Express,
  Go net/http, Rust/axum, etc.), proposes a focused 5-10 check suite
  following the API-first, <2-minute, idempotent discipline, and emits a
  runnable scaffold in the right framework — with `TODO` markers for
  environment-specific values like base URL and auth tokens. Even if the
  user has not explicitly said "smoke", trigger when they ask for a
  "fast CI gate", "deploy-readiness check", "is-the-build-up test",
  "happy-path coverage", or describe symptoms like "we keep running a
  20-minute regression suite against broken builds".
---

# Smoke Test

A smoke test (a.k.a. build-verification test / build-acceptance test /
intake test) is a small, fast, broad-but-shallow suite that verifies a
fresh build is *stable enough to bother testing further*. It is the
release gate that protects the rest of the pipeline from wasting time on
fundamentally broken code. The name comes from electrical engineering:
power on the board and watch for smoke. If it smokes, stop.

This skill helps you design + scaffold one for the user's project. It is
**not** a regression-suite generator and not a full QA strategy: smoke
tests stay focused on a handful of critical happy-paths and connectivity
checks.

## When to invoke this skill

Use it when the user wants any of:

- A *new* smoke-test suite for a service that has none
- A review of an *existing* smoke-test suite for scope, speed, flakiness
- CI/CD wiring so smoke runs as a gate before regression
- Help picking the 5-10 checks that should make the cut

Skip it for:

- Unit testing or full regression testing (different discipline, larger
  scope)
- Pure performance / load testing (overlaps but lives elsewhere)
- "Fix this failing test" — that is debugging, not suite design

## Core principles (compressed)

Smoke tests have a different shape from other tests. The user may not
know these, so anchor every recommendation in them:

- **Broad, not deep.** Cover the most important user-facing paths. Skip
  edge cases, validation rules, error-message wording. If the smoke
  suite is failing on something that needs a debate, it is too detailed.
- **API-first, UI as last resort.** API-level checks finish in
  milliseconds and rarely flake. UI checks finish in seconds and flake
  often. Reserve UI smoke for flows that cannot be observed at the API
  layer (login redirects, SPA boot).
- **<2 minutes wall-clock** for the whole suite in CI. >2 min and
  developers will start skipping the gate; >15 min and the gate is
  effectively dead.
- **5–10 checks for a small/medium service**, up to 20–50 for a large
  enterprise app. More than that is a regression suite in disguise.
- **Idempotent and read-only-safe.** Smoke tests run on every deploy,
  often in production. They must not leave artefacts behind. Write
  paths either use ephemeral test data with cleanup, or are guarded so
  they can be skipped against prod.
- **Fail fast, gate hard.** If smoke fails, the deploy is rejected.
  Subsequent test stages do not run.
- **Diagnose-able failures.** When the gate trips at 3 AM, the engineer
  on call needs the failing payload, the response, the correlation id —
  not just "test 4 failed".

The full research distillation is in `references/principles.md`. Read it
when the user asks "why" about any of the above, or when you need the
formal definitions of smoke vs sanity vs regression vs retest.

## Workflow

### Step 1 — Detect the stack

Run the bundled detector and read its JSON output:

```bash
python <skill-path>/scripts/detect_stack.py <repo-path>
```

It identifies the language(s), web/API framework, test runner(s),
candidate entry points, discovered HTTP routes, and existing CI config.
Route discovery is greedy/grep-based — treat the list as candidates the
user should confirm, not ground truth.

If detection finds **no language manifest** (`Analyzed 0` style result)
or no framework and the user is asking specifically about HTTP smoke,
say so plainly to the user and ask for the stack. Do not invent.

### Step 2 — Propose the 5–10 checks

Before writing any code, present a short numbered list of what the smoke
suite *will* cover. Each check should fit one line. Default shape:

1. Health/readiness endpoint returns 200 (`/health`, `/healthz`,
   `/readyz`, or framework default)
2. Authentication path mints a valid token (or rejects missing token
   with 401)
3. Primary read endpoint returns shape-correct data for known fixture
4. Primary write endpoint (optional, only if idempotent) creates a
   record and returns its id
5. Dependency liveness — at least one read query against the DB or
   message bus
6. Error path returns the correct status (404 for missing, 401 for
   unauthenticated)

Adapt this list to the routes the detector found. Cross out items that
do not apply. Add domain-specific items (checkout funnel, login, etc.)
when obvious from the routes table. Cap at 10.

Confirm the list with the user before generating code. The user may
know that "X is owned by another team and not in our smoke contract" or
"the /admin path is irrelevant" — let them prune.

### Step 3 — Pick the template

Match the detected stack to a template in `references/templates/`:

- `fastapi-pytest.md` — FastAPI / Starlette + pytest + httpx (in-process
  TestClient)
- `flask-pytest.md` — Flask + pytest + Flask test_client()
- `django-pytest.md` — Django / DRF + pytest-django + Django Client
- `express-vitest.md` — Express + Vitest + supertest
- `fastify-vitest.md` — Fastify + Vitest + `app.inject()`
- `go-httptest.md` — Go `net/http` + standard `testing` +
  `net/http/httptest.NewServer`
- `gin-httptest.md` — Go + Gin + `gin.Engine.ServeHTTP` + httptest
- `axum-tower.md` — Rust / axum + tokio test + `tower::ServiceExt`

For frameworks not yet covered (Rails, NestJS, Spring, .NET, Actix,
Rocket, …) read the closest template (HTTP-method-based ones for
Rails/NestJS, axum-tower for Actix/Rocket) and adapt the imports +
assertion library. Note explicitly in your response that the template
is adapted rather than canonical, so the user calibrates trust.

### Step 4 — Emit the scaffold

The generated file should:

- Sit in the project's conventional test location (`tests/smoke/`,
  `test/smoke/`, `cmd/<service>/smoke_test.go`, etc.)
- Be **runnable as scaffolding** — the test framework's hello-world
  must pass; assertions reference the real routes — but env-specific
  values (base URL, bearer token, test user id) are clearly marked
  `TODO`/`os.getenv("SMOKE_BASE_URL", "http://localhost:8080")` so the
  user can wire them in.
- Cap the suite at the count agreed in Step 2.
- Include a short comment block at the top stating: purpose (smoke,
  not regression), runtime budget (<2 min), how to run locally, how
  to run in CI.
- Avoid hard-coded `sleep(n)` — use the framework's polling/wait
  primitives (httpx retries, vitest `vi.waitFor`, Go `eventually`
  helpers).

After writing the file, show the user the runnable command. Example:
"`pytest tests/smoke -q -s` — should run in <5 s against the in-process
TestClient; set SMOKE_BASE_URL to hit a deployed environment instead."

### Step 5 — Offer CI wiring (only if asked or obviously useful)

If the detector found GitHub Actions / GitLab CI and the user asked
about CI, append a minimal job snippet to the recommended file path.
Otherwise mention the option in one sentence and stop. Do not stuff CI
config the user did not ask for.

### Step 6 — Tell the user how to fail well

Close with a short reminder of the failure-debugging expectations:

- Capture stderr, response payloads, correlation ids on failure
- Treat a failing smoke run as a stop-the-line event
- Quarantine (don't delete) flaky tests, fix them within the sprint

## Communicating findings

Lead with the *plan* (the 5-10 list), then the *artefact* (the scaffold
file path), then *runtime + caveats*. Do not paste the test code into
the chat — point at the file. Example shape:

> Detected: FastAPI 0.110, pytest + httpx, 4 routes (/health, /users/{id},
> /orders, /orders/{id}). Proposed smoke suite (6 checks):
>
> 1. GET /health returns 200 + {status: ok}
> 2. GET /users/1 returns alice
> 3. GET /users/9999 returns 404
> 4. POST /orders without auth returns 401
> 5. POST /orders with bearer + known user returns 201 + id
> 6. GET /orders/{id} for the order created in #5 returns the same body
>
> Wrote `tests/smoke/test_smoke.py` — pytest will run in <2 s in-process.
> TODO markers at the top set SMOKE_BASE_URL + SMOKE_TOKEN for
> deployed-env runs. Caveat: I did not detect a CI config; let me know
> if you want a GitHub Actions snippet that runs this on every PR.

## Out of scope

The research informing this skill covers smoke testing across many
domains (mobile, ML, ERP, messaging). The current version of this skill
focuses on **web/API/software services**. If the user asks for mobile
or ML-pipeline smoke testing, say so plainly — the principles still
apply (broad/shallow, API-first, fail fast) but the templates do not
yet exist. Point them at `references/principles.md` for the conceptual
guidance and offer to draft something stack-specific by hand.

Process metrics (Defect Escape Rate, MTTD, MTTR) are documented in
`references/principles.md` for the user's awareness but are *not*
emitted by this skill — they belong in a longer-running QA dashboard,
not a per-build gate.
