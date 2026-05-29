# Smoke test suite for `fastapi-app`

I added a single-file smoke suite at `outputs/test_smoke.py` that exercises every route in `app.py` on both its happy path and its documented error paths. It uses FastAPI's `TestClient` (synchronous, in-process) so it needs no running server and no async fixtures.

## What's covered

12 tests across 4 routes:

| Route | Tests |
|---|---|
| `GET /health` | 200 OK + body shape |
| `GET /users/{user_id}` | happy (200), unknown user (404), non-int path param (422) |
| `POST /orders` | happy (200), missing `Authorization` (401), wrong scheme `Basic` (401), unknown user (400), missing required field (422), id auto-increment across two calls |
| `GET /orders/{order_id}` | happy (200, round-trips a freshly-created order), unknown id (404) |

## State isolation

`app.py` keeps orders in a module-level dict `_ORDERS` and an `_NEXT_ORDER_ID` counter. The `client` fixture resets both before each test, so tests are independent regardless of run order.

## How to run

```bash
cd outputs/
python -m pytest -q test_smoke.py
```

The fixture's `pyproject.toml` already declares `pytest`, `pytest-asyncio`, and `httpx` under the `test` extra, which is all that's needed — `fastapi.testclient.TestClient` is shipped with FastAPI itself.

## Result

```
12 passed
```

## Files

- `/home/mcs/Documents/git/claude-skills/plugins/quality-assurance/smoke-test-workspace/iteration-1/fastapi-no-tests/without_skill/outputs/test_smoke.py`

## Notes / what was deliberately left out

- **No load / concurrency tests.** This is a smoke suite — it answers "is the app wired up at all?", not "does it survive 1k rps?".
- **No schema-drift tests against `/openapi.json`.** Worth adding later if the API gets external consumers.
- **No persistence tests.** The fixture has no DB; orders live in a dict that resets on process restart. The id-increment test (`test_create_order_increments_id`) is the closest proxy.
- **Async client not used.** `TestClient` is sync and sufficient here; switching to `httpx.AsyncClient` would only matter if the suite grew to need real concurrency.
