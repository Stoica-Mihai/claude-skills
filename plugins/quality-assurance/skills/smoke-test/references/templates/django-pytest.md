# Template: Django + pytest-django

Use for Django (with or without DRF) using `pytest-django`. Runs
in-process via Django's bundled `Client` (no real socket), or against a
deployed URL via `requests` when `SMOKE_BASE_URL` is set.

## Dependencies (add to dev/test extras)

```
pytest>=8
pytest-django>=4
requests>=2.32  # only needed for the deployed-URL path
```

`pytest-django` needs `DJANGO_SETTINGS_MODULE` either via `pytest.ini`
or env. Most Django repos already configure this.

## File location

`tests/smoke/test_smoke.py`. If the project keeps tests inside the app
package, mirror that — but `tests/smoke/` as a directory lets you run
the smoke subset with `pytest tests/smoke`.

## Body

```python
"""
Smoke tests — verify the build is stable enough to test further.
Runtime budget: < 5 s in-process, < 30 s against a deployed URL.

Run locally (in-process):     pytest tests/smoke -q
Run against an environment:   SMOKE_BASE_URL=https://api.example.com \
                              SMOKE_TOKEN=eyJ... pytest tests/smoke -q
"""
import os
import pytest

BASE_URL = os.getenv("SMOKE_BASE_URL")
TOKEN = os.getenv("SMOKE_TOKEN", "smoke-token-placeholder")  # TODO


@pytest.fixture
def client(db):
    """In-process Django test client; pytest-django supplies it.
    `db` fixture gives access to the test database."""
    if BASE_URL:
        import requests
        sess = requests.Session()
        sess.headers.update({"Authorization": f"Bearer {TOKEN}"})
        yield sess
        sess.close()
    else:
        from django.test import Client
        yield Client(HTTP_AUTHORIZATION=f"Bearer {TOKEN}")


def _get(client, path):
    if BASE_URL:
        return client.get(BASE_URL.rstrip("/") + path, timeout=5)
    return client.get(path)


def _post(client, path, json):
    if BASE_URL:
        return client.post(BASE_URL.rstrip("/") + path, json=json, timeout=5)
    return client.post(path, data=json, content_type="application/json")


def _status(r):
    return getattr(r, "status_code", None)


def _json(r):
    if BASE_URL:
        return r.json()
    return r.json() if hasattr(r, "json") and callable(r.json) else None


def test_health(client):
    r = _get(client, "/health/")
    assert _status(r) == 200
    body = _json(r)
    assert body and body.get("status") == "ok"


def test_known_record_returns_200(client):
    # TODO: replace /users/1/ with a known seeded resource.
    r = _get(client, "/users/1/")
    assert _status(r) == 200


def test_missing_returns_404(client):
    r = _get(client, "/users/999999/")
    assert _status(r) == 404


def test_protected_route_requires_auth(client):
    # Django test Client carries the auth header by default; for the
    # unauth probe build a fresh client without it.
    if BASE_URL:
        import requests
        r = requests.get(BASE_URL.rstrip("/") + "/orders/", timeout=5)
    else:
        from django.test import Client
        r = Client().get("/orders/")
    assert _status(r) in (401, 403)


def test_create_record_happy_path(client):
    r = _post(client, "/orders/", {"items": ["smoke"]})
    assert _status(r) in (200, 201)
```

## Notes

- `pytest-django` auto-loads settings if `pytest.ini` declares
  `DJANGO_SETTINGS_MODULE`. If your project doesn't have that, add it
  to `setup.cfg` or `pyproject.toml [tool.pytest.ini_options]`.
- The `db` fixture is required to get a transactional test database.
  In smoke mode against a deployed URL this is unused — the body's
  branch short-circuits.
- DRF returns `401` for missing auth on token-protected routes; vanilla
  Django often returns `302` (redirect to login) — adjust the assertion
  accordingly. The `in (401, 403)` covers both common cases.
- For Django Channels / async views, swap `Client` for
  `AsyncClient` and mark tests `@pytest.mark.asyncio`.
