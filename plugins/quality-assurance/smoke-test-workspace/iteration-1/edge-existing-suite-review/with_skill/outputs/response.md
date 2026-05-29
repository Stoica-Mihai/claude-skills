# Smoke Suite Review — `tests/smoke/test_smoke.py`

Reviewed against the smoke-test skill's principles (broad/shallow, API-first, <2 min wall-clock, idempotent, diagnose-able). **I have not modified your tests** — proposing targeted edits only, as requested.

## Verdict

Overall the suite is in good shape. It hits the right shape — 6 checks, all API-level via FastAPI `TestClient`, sub-second runtime, sensible dual-mode (`SMOKE_BASE_URL` toggles in-process vs deployed). Coverage maps cleanly onto the 4 routes the app exposes (`/health`, `/users/{id}`, `/orders`, `/orders/{id}`). Nothing needs to be ripped out. There are 4 real issues to fix and 3 nice-to-haves.

## Coverage vs principles — at a glance

| Principle | Status | Notes |
|---|---|---|
| Broad, not deep | OK | One assertion per check, no edge-case rabbit holes. |
| API-first | OK | No UI; pure HTTP. |
| <2 min wall-clock | OK | In-process TestClient runs the whole file in <1 s. |
| 5–10 checks | OK | 6 checks for a 4-route API is right-sized. |
| Idempotent / read-only-safe | **WARN** | `test_create_order_happy_path` writes unconditionally — fine against the in-memory fixture, will leak orders against a deployed env. See Issue #1. |
| Fail fast | OK | pytest default. |
| Diagnose-able failures | PARTIAL | `assert ..., r.text` is good. Missing: no correlation-id / request-id capture; no status-line on the body assertions. See Issue #4. |

## Issues to fix (ordered by severity)

### 1. Write path is not prod-safe — guard it or mark it ephemeral

`test_create_order_happy_path` and `test_get_created_order_roundtrip` create real orders. Against the in-process app this is fine (state dies with the process). Against `SMOKE_BASE_URL=https://api.prod...` this leaks an order per smoke run, forever. The skill's "idempotent and read-only-safe" rule wants this guarded.

**Edit:** at the top of the two write tests, gate on an env flag:

```python
SMOKE_ALLOW_WRITES = os.getenv("SMOKE_ALLOW_WRITES", "1" if not BASE_URL else "0") == "1"

@pytest.mark.skipif(not SMOKE_ALLOW_WRITES, reason="write-path smoke disabled against this env")
def test_create_order_happy_path(client):
    ...
```

Default: writes ON in-process (BASE_URL unset), OFF against any deployed env unless operator opts in with `SMOKE_ALLOW_WRITES=1`. This is the standard prod-smoke posture.

If you can, also tag the created order so the cleanup story is obvious — e.g. `items=["smoke-item-<uuid>"]` instead of the fixed `"smoke-item"` literal. Makes leaked smoke artefacts trivially greppable.

### 2. Inter-test state coupling via `pytest.created_order_id` — replace with a fixture

`test_create_order_happy_path` stuffs the id onto the `pytest` module (`pytest.created_order_id = body["id"]`) and the next test reads it via `getattr(pytest, ...)`. This works but is fragile:

- Tests must run in source order. With `pytest-randomly` or `-p no:cacheprovider --tb=short --last-failed-no-failures=all` reordering, the round-trip skips silently.
- The "skip if id missing" branch hides real regressions: if the create test breaks, the round-trip never fails — it just skips. The gate goes green on a half-broken build.
- `pytest` module monkey-patching is an anti-pattern flagged by most linters.

**Edit:** make a session-scoped fixture that creates the order once and yields the id; round-trip consumes it. If the fixture errors, the round-trip is reported as ERROR (not SKIP) — which is what you want.

```python
@pytest.fixture(scope="session")
def created_order_id(client_factory):
    if not SMOKE_ALLOW_WRITES:
        pytest.skip("writes disabled")
    with client_factory() as c:
        r = c.post("/orders",
                   json={"user_id": 1, "items": [f"smoke-{uuid.uuid4()}"]},
                   headers={"authorization": f"Bearer {TOKEN}"})
        assert r.status_code in (200, 201), r.text
        return r.json()["id"]
```

(Note: the existing `client` fixture is function-scoped, so you'll need a `client_factory` helper or promote `client` to session scope for the deployed-URL branch.)

### 3. `client` fixture is function-scoped — wasteful and not how the skill template runs

Function scope means a new `TestClient` (and lifespan startup/shutdown) per test. For FastAPI with `with TestClient(app)` this triggers startup events 6 times. Fine for an in-memory app, real cost against a deployed env (new `httpx.Client`, new TCP connection per test). The `fastapi-pytest.md` template uses session scope.

**Edit:** `@pytest.fixture(scope="session")` on `client`. Two-line change.

### 4. Failure diagnostics are thin — capture correlation id / request id

`assert r.status_code == 200, r.text` is the minimum acceptable. The skill's "Tell the user how to fail well" step wants correlation ids surfaced so the on-call engineer at 3 AM doesn't go fishing.

**Edit:** add a small helper that on failure dumps status, the `x-request-id` / `x-correlation-id` header if present, and the truncated body:

```python
def _diag(r):
    return (f"status={r.status_code} "
            f"req_id={r.headers.get('x-request-id') or r.headers.get('x-correlation-id') or '-'} "
            f"body={r.text[:500]}")

assert r.status_code == 200, _diag(r)
```

Drop-in replacement for the trailing `, r.text` on each assert. Cheap, big payoff against a real deploy.

## Nice-to-haves

### 5. Add a per-request timeout assertion

The 5-second `httpx.Client(timeout=5.0)` is fine as a hard ceiling, but the smoke gate's selling point is "fast" — if `/health` starts taking 4 seconds the gate still passes, silently. Consider a soft-budget assert on `r.elapsed.total_seconds() < 1.0` for `/health` only. Don't apply it broadly; flaky budgets get muted, then ignored.

### 6. Drop `pytest-asyncio` from `pyproject.toml` test extras

It's listed in `[project.optional-dependencies].test` but nothing in `test_smoke.py` is async — `TestClient` is sync, `httpx.Client` is sync. One less install dep.

### 7. The `conftest.py` `sys.path` hack is fine but worth a one-line comment

`conftest.py` mutates `sys.path` to make `app` importable. That works but reads as a smell on first encounter. A single-line comment "TODO: replace with proper package layout once `app/` becomes a real package" prevents the next person from cargo-culting this into a larger project.

## Not-a-problem (verified, leaving alone)

- `r.status_code in (200, 201)` for create — correct hedge; the app returns 200 by default but a future change to `status_code=201` shouldn't break the smoke gate.
- `pytest.skip` on missing id — wrong tool (see Issue #2), but the *intent* (don't fail the round-trip if create already failed) is sound. Fixture refactor preserves intent without the silent-skip footgun.
- Reading `body.get("id"), int)` rather than asserting on a specific id — correct; smoke shouldn't pin id values.

## Suggested edit order

1. **Issue #2 + #3 together** — refactor to a session-scoped `client` and a `created_order_id` fixture. One commit, removes the `pytest.*` monkey-patch and the function-scope waste at once.
2. **Issue #1** — add the `SMOKE_ALLOW_WRITES` gate. Required before pointing this at any deployed env.
3. **Issue #4** — `_diag()` helper. 5 minutes, applies to every assertion.
4. **Items 5–7** — when convenient.

## Runtime budget after edits

Still well under 2 s in-process. Against a deployed env with session-scoped client and writes enabled, expect ~1–3 s for 6 HTTP round-trips on a healthy service — comfortably inside the <2 min budget. No threat to the gate's "fast" property.

## What I did not touch

- The `app.py` fixture itself — out of scope; smoke tests adapt to the API, not vice versa.
- CI wiring — you didn't ask, and the skill says don't stuff CI config the user didn't request.
- Adding *more* tests — 6 checks against 4 routes is already at the right density. Resist the urge to grow this suite; that's how smoke turns into regression.
