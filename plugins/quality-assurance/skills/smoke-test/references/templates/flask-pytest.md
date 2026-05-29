# Template: Flask + pytest

Use for Flask (with or without Flask-RESTful / Flask-Smorest) using
`pytest`. Runs in-process via Flask's `test_client()`, or against a
deployed URL via `httpx` when `SMOKE_BASE_URL` is set.

## File location

`tests/smoke/test_smoke.py`. Most Flask projects keep `tests/` at repo
root; mirror whatever convention the project already uses.

## Body

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
import pytest

BASE_URL = os.getenv("SMOKE_BASE_URL")
TOKEN = os.getenv("SMOKE_TOKEN", "smoke-token-placeholder")  # TODO
# TODO: confirm the module path that exposes your Flask `app` object.
APP_MODULE = os.getenv("SMOKE_APP_MODULE", "app")


@pytest.fixture
def client():
    if BASE_URL:
        import httpx
        with httpx.Client(base_url=BASE_URL, timeout=5.0) as c:
            yield c
        return
    module = importlib.import_module(APP_MODULE)
    # Flask convention: an attribute called `app` or a `create_app()` factory.
    app_obj = getattr(module, "app", None) or module.create_app()
    app_obj.testing = True
    with app_obj.test_client() as c:
        yield c


def _auth():
    return {"Authorization": f"Bearer {TOKEN}"}


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.get_json() if hasattr(r, "get_json") else r.json()
    assert body and body.get("status") == "ok"


def test_known_record_returns_200(client):
    # TODO: replace /users/1 with a known seeded resource.
    r = client.get("/users/1")
    assert r.status_code == 200


def test_missing_returns_404(client):
    r = client.get("/users/999999")
    assert r.status_code == 404


def test_protected_route_requires_auth(client):
    r = client.post("/orders", json={"items": ["smoke"]})
    assert r.status_code in (401, 403)


def test_create_record_happy_path(client):
    r = client.post("/orders", json={"items": ["smoke"]}, headers=_auth())
    assert r.status_code in (200, 201)
```

## Notes

- `Flask.test_client()` is sub-millisecond per request — keep all
  checks under it.
- For app factories (`create_app(config_name="testing")`) the fixture
  falls through to `module.create_app()` automatically. If the factory
  needs args, instantiate the app object directly above the `yield`.
- The `get_json()` vs `json()` branch handles both the Flask test
  response and the httpx response in deployed-URL mode.
- If the app uses blueprints with URL prefixes (e.g. `/api/v1/`), bake
  that into a `BASE_PREFIX` env var rather than hard-coding it.
