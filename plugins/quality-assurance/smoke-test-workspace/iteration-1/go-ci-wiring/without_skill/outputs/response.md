# Build-verification CI for the Go HTTP API

## What was delivered

Two files under `outputs/`:

1. **`main_test.go`** — drop next to `main.go` inside the fixture. Uses `net/http/httptest` against the exported `newRouter()`, so no port binding, no flakes, no goroutine leaks.
2. **`ci.yml`** — drop at `.github/workflows/ci.yml` at the repo root. Runs on every PR targeting `main` (and on pushes to `main` to keep the branch baseline green).

## What `main_test.go` covers

Every route in `main.go`, both happy and sad paths:

| Test | Route | Asserts |
|---|---|---|
| `TestHealth` | `GET /health` | 200, JSON body `{status:ok}`, `application/json` content-type |
| `TestGetUser_Found` | `GET /users/1` | 200, body decodes to seeded alice |
| `TestGetUser_NotFound` | `GET /users/9999` | 404 |
| `TestGetUser_BadID` | `GET /users/notanint` | 400 |
| `TestPostOrder_MissingAuth` | `POST /orders` | 401 when no `Bearer` header |
| `TestPostOrder_BadJSON` | `POST /orders` | 400 on malformed body |
| `TestPostOrder_UnknownUser` | `POST /orders` | 400 when `userId` not in seed |
| `TestPostOrder_CreateThenGet` | `POST /orders` then `GET /orders/{id}` | 201 then 200, round-trips ID + items |
| `TestGetOrder_NotFound` | `GET /orders/424242` | 404 |
| `TestGetOrder_BadID` | `GET /orders/abc` | 400 |

Each test calls `newRouter()` fresh, but note the fixture has module-level `orders` / `nextID` state — that's a property of the code under test, not the harness. The create-then-get test relies only on the ID it just got back, so it is order-independent.

A small `itoa` helper avoids pulling `strconv` into the test (the fixture already imports it; this is just to keep the test file self-contained without adding another import that gofmt would have to police).

## What `ci.yml` does

Triggered on `pull_request` to `main` and pushes to `main`. One job, `build-and-test`, with `working-directory` pinned to the fixture so every step runs in the right module.

Steps:

1. **checkout** — `actions/checkout@v4`.
2. **set up go** — `actions/setup-go@v5`, Go 1.22 to match `go.mod`, with module cache keyed on `go.sum` (path is harmless when `go.sum` is absent — the cache step just no-ops on miss).
3. **go mod tidy check** — runs `go mod tidy` and fails if it would dirty `go.mod`/`go.sum`. Catches dependency drift on PRs.
4. **go vet** — static checks. Failures block.
5. **gofmt check** — `gofmt -l .`; any output means unformatted files, fails the job.
6. **build** — `go build -v ./...`. This is the build-verification gate.
7. **test** — `go test -race -count=1 -covermode=atomic -coverprofile=coverage.out ./...`. `-race` catches the shared-map concurrency the fixture protects with `sync.Mutex`. `-count=1` disables test caching so PRs always rerun.
8. **upload coverage artifact** — uploads `coverage.out` for inspection (non-blocking, runs `if: always()`).

`permissions: contents: read` is locked to least-privilege. `concurrency` cancels superseded runs on the same PR branch.

## How merge gets blocked

GitHub Actions itself does not block merges — branch protection does. To finish the wiring on the repo:

**Settings → Branches → Branch protection rule for `main`:**

- Require a pull request before merging
- **Require status checks to pass before merging** → add `build & test (go)` (the job's `name:`) as a required check
- Require branches to be up to date before merging

Until that required-status-check entry is added in branch protection, the workflow will run on every PR and post red/green status but will not technically block merge. The job name in the workflow is `build & test (go)` — that's the exact string to enter in branch protection.

## Install

```
# tests
cp outputs/main_test.go plugins/quality-assurance/skills/smoke-test/evals/fixtures/go-http-app/main_test.go

# workflow (path is relative to repo root)
mkdir -p .github/workflows
cp outputs/ci.yml .github/workflows/ci.yml
```

Then push a PR and confirm the check appears. Once green, add `build & test (go)` as a required status check in branch protection.

## Caveats

- The fixture has no `go.sum` yet (no external deps). `go mod tidy` will not create one until a dep is added, and the cache step tolerates the missing file. If deps land later, `go.sum` will be created by the tidy check step on the first PR that adds one.
- The fixture's `main()` ignores the error from `http.ListenAndServe` — out of scope for build-verification, but worth flagging for a future cleanup pass.
- Module-level `users` / `orders` / `nextID` make true test isolation impossible without refactoring the fixture; the tests above are written to tolerate that (they don't assume `nextID == 1`).
