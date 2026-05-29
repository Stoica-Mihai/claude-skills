# Template: FastAPI / Starlette + pytest + httpx

Use for FastAPI or Starlette services with `pytest` as the test
runner. Runs in-process via FastAPI's `TestClient` for sub-second smoke,
or against a deployed URL via `httpx.Client(base_url=...)`.

## File location

`tests/smoke/test_smoke.py` if the project already uses `tests/`. Use
`tests/smoke/` as a directory so the runner can pick the smoke subset
with `pytest tests/smoke`.

## Imports + fixtures

```python
"""
Smoke tests — verify the build is stable enough to test further.
Runtime budget: < 2 s in-process, < 30 s against a deployed URL.

Run locally (in-process):     pytest tests/smoke -q
Run against an environment:   SMOKE_BASE_URL=https://api.example.com \
                              SMOKE_TOKEN=eyJ... pytest tests/smoke -q
"""
import importlib
import os
import sys
import pytest
import httpx

# When SMOKE_BASE_URL is set, hit the deployed service.
# Otherwise drive the app in-process for sub-second runs.
BASE_URL = os.getenv("SMOKE_BASE_URL")
TOKEN = os.getenv("SMOKE_TOKEN", "smoke-token-placeholder")  # TODO: real token in CI

# SMOKE_APP_MODULE picks where the FastAPI app object lives. Defaults to
# `app` (a flat-layout repo with `app.py` at the root). For layered repos
# set SMOKE_APP_MODULE=src.main or similar. We also push the repo root
# onto sys.path so flat-layout imports resolve without a conftest hack.
APP_MODULE = os.getenv("SMOKE_APP_MODULE", "app")
APP_ATTR = os.getenv("SMOKE_APP_ATTR", "app")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def _load_app():
    module = importlib.import_module(APP_MODULE)
    obj = getattr(module, APP_ATTR, None)
    if obj is None and hasattr(module, "create_app"):
        obj = module.create_app()
    if obj is None:
        raise RuntimeError(
            f"Could not find FastAPI app object — set SMOKE_APP_MODULE / "
            f"SMOKE_APP_ATTR (looked for {APP_MODULE}.{APP_ATTR})."
        )
    return obj


@pytest.fixture
def client():
    if BASE_URL:
        with httpx.Client(base_url=BASE_URL, timeout=5.0) as c:
            yield c
    else:
        from fastapi.testclient import TestClient
        with TestClient(_load_app()) as c:
            yield c
```

## Body — one assertion per check, max 10 checks

```python
def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json().get("status") == "ok"


def test_get_known_user(client):
    r = client.get("/users/1")
    assert r.status_code == 200
    assert r.json()["id"] == 1


def test_missing_user_returns_404(client):
    r = client.get("/users/99999")
    assert r.status_code == 404


def test_create_order_requires_auth(client):
    r = client.post("/orders", json={"user_id": 1, "items": ["a"]})
    assert r.status_code == 401


def test_create_order_happy_path(client):
    r = client.post(
        "/orders",
        json={"user_id": 1, "items": ["smoke-item"]},
        headers={"authorization": f"Bearer {TOKEN}"},
    )
    assert r.status_code in (200, 201)
    body = r.json()
    assert body["user_id"] == 1
    # Pinned for the round-trip check below.
    pytest.created_order_id = body["id"]


def test_get_created_order_roundtrip(client):
    oid = getattr(pytest, "created_order_id", None)
    if oid is None:
        pytest.skip("create-order test did not pin an id")
    r = client.get(f"/orders/{oid}")
    assert r.status_code == 200
    assert r.json()["id"] == oid
```

## Notes

- The `TestClient` path is recommended for CI gates inside the repo: no
  network, no flakiness, runs in <1 s on a typical service.
- The `BASE_URL` path is the production-smoke path: same assertions,
  hits the deployed instance. Use it post-deploy.
- Pinning a created id on `pytest` is a quick hack for round-trip; if
  the project has its own fixture style, prefer that.
- For idempotency in prod runs, either gate the POST behind
  `if BASE_URL is None` or have the service accept an idempotency-key
  header.
