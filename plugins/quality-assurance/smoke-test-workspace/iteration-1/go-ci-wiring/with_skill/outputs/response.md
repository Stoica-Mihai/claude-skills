# Smoke-test wiring for `go-http-app`

**Stack detected:** Go 1.22, `net/http` + `httptest`, `go test` runner.
**Routes confirmed in `main.go`:** `GET /health`, `GET /users/{id}`,
`POST /orders` (Bearer-guarded), `GET /orders/{id}`.
**CI detected:** none — scaffolded a fresh GitHub Actions workflow.

## Proposed smoke suite (6 checks, capped at 10)

1. `GET /health` → 200 and body `{"status":"ok"}`
2. `GET /users/1` → 200, shape-correct (`id`, `name`)
3. `GET /users/99999` → 404 (negative path)
4. `POST /orders` without `Authorization` → 401 (auth gate works)
5. `POST /orders` with Bearer token + known user → 201 + returns `id`
6. `GET /orders/{id}` round-trips the order created in #5

The suite is API-first, idempotent (ephemeral data, in-memory store),
gives diagnose-able failure logs (method + URL + status + body), and is
bounded by a 5 s per-request client timeout plus a 90 s `go test`
wall-clock cap.

## Artefacts

- **Test file:** `outputs/smoke_test.go`
  Drop in alongside `main.go` at:
  `plugins/quality-assurance/skills/smoke-test/evals/fixtures/go-http-app/smoke_test.go`
  (lives in `package main` so it can call the unexported `newRouter()`
  directly — no need to export anything in the fixture).
  Gated by `//go:build smoke`, so a normal `go test ./...` ignores it.
- **CI workflow:** `outputs/smoke.yml`
  Install at: `.github/workflows/smoke.yml` (repo root).

## How to run

Locally, from the fixture directory:

```bash
go test -tags smoke -run TestSmoke -v -count=1 -timeout 90s ./...
```

Against a deployed environment:

```bash
SMOKE_BASE_URL=https://api.example.com \
SMOKE_TOKEN=eyJ... \
go test -tags smoke -run TestSmoke -v -count=1 -timeout 90s ./...
```

Verified locally against the fixture: 5 test functions, all pass,
total runtime ~3 ms (well under the <2 min budget).

## CI gate

`smoke.yml` runs on:

- every `pull_request` targeting `main`
- every `push` to `main` (post-merge sanity)

It builds (`go vet` + `go build`) and then runs the tagged smoke suite.
Job timeout is 5 minutes; concurrency cancels stale runs on the same PR.

**To actually block merge** (GitHub Actions only *reports* status by
itself), add the job to branch protection:

> Settings → Branches → Branch protection rules → `main` →
> "Require status checks to pass before merging" → add `smoke (go-http-app)`.

That is the step that turns a red smoke run into a hard merge block.

## Failure-debugging expectations

- Failures log method, URL, status, and response body — not just
  "assertion failed" — so a 3 AM on-call has something to act on.
- Treat a red smoke run as stop-the-line: do not chase regression
  failures downstream until smoke is green again.
- If a smoke test flakes, quarantine (skip with a tracking issue) — do
  not delete — and fix it inside the sprint.

## Caveats

- The fixture has no `go.sum` (stdlib-only), so the workflow sets
  `cache: false` on `setup-go`. Re-enable caching once real deps are
  added.
- `SMOKE_TOKEN` is set to a placeholder (`ci-smoke-token`) in CI; the
  fixture's auth check only validates the `Bearer ` prefix, so this
  works in-process. For a deployed run, wire a real secret via
  `${{ secrets.SMOKE_TOKEN }}` in `smoke.yml`.
- The suite stops at 6 checks on purpose. If you find yourself wanting
  to add validation-rule coverage or error-message wording assertions,
  those belong in a regression suite, not here.
