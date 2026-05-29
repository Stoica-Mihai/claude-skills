# Smoke suite for `fastapi-app`

**Detected stack:** Python 3.10+, FastAPI ≥0.110, pytest + httpx (declared in
`pyproject.toml` `[project.optional-dependencies].test`). One entry point
(`app.py`), four HTTP routes:

| Method | Route             |
|--------|-------------------|
| GET    | `/health`         |
| GET    | `/users/{user_id}`|
| POST   | `/orders`         |
| GET    | `/orders/{order_id}` |

No CI config detected — I did not scaffold one. Say the word if you want a
GitHub Actions job appended.

## Proposed checks (6 — confirm before relying on it as the contract)

1. `GET /health` returns `200` + `{"status": "ok"}` — liveness gate.
2. `GET /users/1` returns `200` and the known fixture user (alice).
3. `GET /users/99999` returns `404` — error path wired.
4. `POST /orders` with no `Authorization` header returns `401` — auth gate works.
5. `POST /orders` with `Bearer <token>` + known user returns `200/201`, body
   has integer `id`, `user_id == 1` — primary write happy path.
6. `GET /orders/{id}` for the order created in #5 returns the same `id` —
   write/read round-trip proves the store is reachable.

This stays inside the smoke discipline: broad, shallow, <2 min, idempotent
on the in-process `TestClient` path. The POST in check 5 mutates state — for
deployed-env runs against prod you should either gate it behind
`if BASE_URL is None`, supply an idempotency-key header, or accept that it
leaves one order behind per smoke run. Flagged as TODO at the top of the
file.

## Files written

- `tests/smoke/test_smoke.py` — the suite (6 checks, ~80 LOC).
- `tests/smoke/__init__.py` — empty, makes the dir a package.
- `conftest.py` (repo root) — puts the repo root on `sys.path` so
  `from app import app` resolves under pytest. Without it pytest fails
  collection with `ModuleNotFoundError: No module named 'app'`.

Both `test_smoke.py` and `conftest.py` are mirrored into this iteration's
`outputs/` dir.

## How to run

In-process (the recommended CI gate path — no network, <1 s):

```
pytest tests/smoke -q
```

Verified locally — **6 passed in 0.4 s** against the fixture.

Against a deployed environment:

```
SMOKE_BASE_URL=https://api.example.com \
SMOKE_TOKEN=eyJhbGc... \
pytest tests/smoke -q
```

The `client` fixture switches transport automatically: if `SMOKE_BASE_URL` is
set it uses `httpx.Client(base_url=...)`; otherwise it uses FastAPI's
in-process `TestClient`.

## TODO markers in the scaffold

- `SMOKE_BASE_URL` — set in CI for the post-deploy smoke job; leave unset for
  in-repo runs.
- `SMOKE_TOKEN` — wire a real bearer in CI secrets. The fixture only checks
  the `Bearer ` prefix, so the placeholder passes the in-process suite, but
  any real auth backend will reject it.
- Adjust `from app import app` if you move the app object.

## Fail-well reminders

- A red smoke run is stop-the-line — block the deploy, don't retry past it.
- The assertions include `r.text` on failure so the failing payload lands in
  pytest output. For prod runs, add your correlation-id header to the log
  capture so on-call can trace from the assert back to the request.
- Flaky checks get quarantined (skip marker + ticket), not deleted. Fix them
  inside the sprint or the gate stops mattering.
