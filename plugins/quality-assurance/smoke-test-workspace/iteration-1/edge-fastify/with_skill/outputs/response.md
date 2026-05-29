# Fastify Smoke Test Scaffold

Stack detected: **Fastify** (Node/TypeScript) with `build()` factory in `src/app.ts`. Test runner: **Vitest**.

Template used: `references/templates/fastify-vitest.md` (canonical — ships with the skill, no adaptation needed beyond JS→TS port).

## Proposed smoke suite (6 checks)

1. `GET /health` returns 200 + `{ status: "ok" }`
2. `GET /users/1` (known seeded record) returns 200 — TODO: replace path with a real seeded resource
3. `GET /users/999999` (missing record) returns 404
4. `POST /orders` without auth returns 401
5. `POST /orders` with bearer token returns 200/201 + an `id`
6. `GET /orders/{id}` for the record created in #5 returns 200 (roundtrip)

All six fit Fastify's `app.inject()` pattern — in-process, sub-millisecond per request, no socket open, every plugin and hook still exercised. The unified `inject()` helper also works against a deployed URL when `SMOKE_BASE_URL` is set, so the same suite gates both local builds and post-deploy environments.

## Artefact

- `smoke.test.ts` — drop at `tests/smoke/smoke.test.ts` in the project.

## Run

```bash
# in-process (default, <1 s)
npx vitest run tests/smoke

# against a deployed environment
SMOKE_BASE_URL=https://api.example.com SMOKE_TOKEN=eyJ... npx vitest run tests/smoke
```

## TODOs to wire up

- `SMOKE_TOKEN` — replace the placeholder with a real bearer for the deployed-env path.
- `/users/1` — swap for a record you know is seeded in every environment.
- If you use `@fastify/swagger`, consider a 7th check on `/docs/json` to catch schema drift.

## Caveats

- Suite is capped at 6 checks; do not let it grow into a regression suite.
- Tests must stay idempotent — the create-order check posts ephemeral data and never asserts on side effects beyond the returned id.
- Treat any smoke failure as stop-the-line: capture status, payload, and correlation id in CI logs before rerunning.
