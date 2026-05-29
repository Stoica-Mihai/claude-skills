# Smoke test for express-app

**Stack detected:** Node + Express 4, Vitest + supertest already in `devDependencies`. Single entry point at `src/index.js`, app exported as `app`. No CI config in the fixture.

**Routes confirmed (from `src/index.js`):** `GET /health`, `GET /users/:id`, `POST /orders`, `GET /orders/:id`. (The detector also surfaced `/authorization` — that's a false positive from `req.get("authorization")`; ignored.)

## Proposed smoke suite — 6 checks, in-process, <2 s

1. `GET /health` → 200 + `{status: "ok"}` — liveness
2. `GET /users/1` → 200 + `{id: 1, name: <string>}` — primary read of known fixture
3. `GET /users/99999` → 404 — error path wired up
4. `POST /orders` no auth → 401 — auth gate works
5. `POST /orders` with `Bearer` + known user → 201 + `{id, userId}` — primary write happy path
6. `GET /orders/<id from #5>` → 200, same id — read-after-write round-trip

That covers liveness, auth, primary read, primary write, an error path, and a dependency-shape check (the in-memory store), in one suite. It maps 1:1 to the smoke principles: broad-not-deep, API-first (no UI), idempotent against the in-memory fixture, fail-fast.

## Artefact

Scaffold written to:

`outputs/tests/smoke/smoke.test.js`

Drop it into the repo at `tests/smoke/smoke.test.js`. It imports `../../src/index.js` for the in-process path, and switches to `SMOKE_BASE_URL` when that env var is set, so the *same file* runs both locally and against a deployed environment.

## Runtime + how to run

Local, in-process (the deploy-gate path you want for CI):

```
npx vitest run tests/smoke
```

Should complete in well under 2 seconds — supertest hands the Express app object directly to Node's HTTP stack with no socket, no port binding.

Against a deployed environment (the "is the deploy actually alive?" use case):

```
SMOKE_BASE_URL=https://staging.example.com \
SMOKE_TOKEN=<real bearer> \
SMOKE_USER_ID=<known good user> \
npx vitest run tests/smoke
```

## TODO markers in the file

- `SMOKE_TOKEN` — the placeholder lets the in-process run pass because the fixture doesn't validate the token, only the `Bearer ` prefix. For a real deployed run, set it to a real token.
- `SMOKE_USER_ID` — defaults to `1` (alice in the fixture). Change to a known-good user id in your target env.
- `SMOKE_BASE_URL` — leave unset to run in-process; set to hit a deployed instance.

## Caveats

- The create-order step (#5) writes to the in-memory `orders` Map. Against the deployed service this leaves an order behind every smoke run — fine for staging, not fine for prod. If you want prod-safe smoke, gate the write block behind `if (process.env.SMOKE_ALLOW_WRITES === "1")` and skip #5/#6 in prod, or point at a teardown endpoint.
- No CI snippet included (you didn't ask, no CI config detected). If you want a GitHub Actions / GitLab job that runs this on every PR + every deploy, say the word and I'll add it.

## Fail-well reminders

- Treat red smoke as stop-the-line: do not promote the build, do not hand off to QA.
- Vitest already prints the failing assertion + response body on failure — that's the on-call diagnostic.
- Flaky smoke tests get quarantined (skipped with a ticket), not deleted. Fix them inside the sprint.
