"""
Smoke tests for the Django REST Framework service.

Purpose: verify a fresh build is stable enough to bother testing further —
broad-but-shallow connectivity + happy-path coverage only. Not a regression
suite. Cap: 6 checks, < 2 minutes wall-clock in CI.

Run locally (in-process, uses Django's test Client):
    pytest tests/smoke -q

Run against a deployed environment (uses requests over the network):
    SMOKE_BASE_URL=https://api.example.com \
    SMOKE_TOKEN=eyJ... \
    pytest tests/smoke -q

Prereqs:
    - pytest-django is installed (already in dev deps per the request).
    - DJANGO_SETTINGS_MODULE is set, either in pytest.ini / pyproject.toml
      [tool.pytest.ini_options], or via env. See TODO below.

On failure: capture the response body + status + any correlation header
(X-Request-ID etc.) — a smoke failure is a stop-the-line event, the
on-call engineer should not have to re-run to see what broke.
"""
import os
import pytest

# TODO: if your project does not already set DJANGO_SETTINGS_MODULE in
# pytest.ini / pyproject.toml, add it there. Example:
#   [tool.pytest.ini_options]
#   DJANGO_SETTINGS_MODULE = "myproject.settings"
# Do NOT set it here — pytest-django must see it before app import.

BASE_URL = os.getenv("SMOKE_BASE_URL")
TOKEN = os.getenv("SMOKE_TOKEN", "smoke-token-placeholder")  # TODO: real token for deployed runs

# TODO: replace with a known seeded resource id that exists in every env.
# For in-process runs, the `seed_user` fixture creates it; for deployed
# runs you must guarantee it exists (data-seed step or a known fixture user).
KNOWN_USER_ID = 1

# TODO: pick one read endpoint and one write endpoint from your ~30 routes
# that best represent the critical path. Defaults below assume DRF
# conventions (/users/, /orders/) — adjust to your URL conf.
READ_PATH = "/api/users/{id}/"
LIST_PATH = "/api/orders/"
WRITE_PATH = "/api/orders/"
HEALTH_PATH = "/health/"  # TODO: confirm — could be /healthz/, /readyz/, or a custom view


@pytest.fixture
def seed_user(db, django_user_model):
    """Create a known user for the in-process read check.
    Skipped automatically when running against a deployed URL."""
    if BASE_URL:
        yield None
        return
    # TODO: adjust fields to match your custom user model if any.
    user, _ = django_user_model.objects.get_or_create(
        pk=KNOWN_USER_ID,
        defaults={"username": "smoke-user", "email": "smoke@example.com"},
    )
    yield user


@pytest.fixture
def client(db):
    """Smoke client. In-process Django test Client by default; switches to
    a `requests.Session` against SMOKE_BASE_URL when that env var is set."""
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
        try:
            return r.json()
        except Exception:
            return None
    if hasattr(r, "json") and callable(r.json):
        try:
            return r.json()
        except Exception:
            return None
    return None


# ---- 6 smoke checks --------------------------------------------------------

def test_health_endpoint_returns_200(client):
    """1. Liveness: the service is up and self-reports healthy."""
    r = _get(client, HEALTH_PATH)
    assert _status(r) == 200, f"health check failed: status={_status(r)}"
    body = _json(r)
    # TODO: adjust expected shape — some teams use {"status": "ok"},
    # others {"healthy": true}, others just an empty 200.
    if body is not None:
        assert body.get("status") in ("ok", "healthy", None) or body.get("healthy") is True


def test_known_record_read_returns_200(client, seed_user):
    """2. Primary read path: a known resource returns shape-correct data."""
    r = _get(client, READ_PATH.format(id=KNOWN_USER_ID))
    assert _status(r) == 200, f"read of known user failed: status={_status(r)}"
    body = _json(r)
    assert body is not None, "expected JSON body on read"
    # TODO: tighten this assertion to a field your API guarantees.
    assert "id" in body or "username" in body or "pk" in body


def test_missing_record_returns_404(client):
    """3. Error path: unknown id returns 404, not 500."""
    r = _get(client, READ_PATH.format(id=999_999_999))
    assert _status(r) == 404, f"expected 404 for missing record, got {_status(r)}"


def test_protected_route_requires_auth(client):
    """4. AuthN gate: anonymous request to a protected route is rejected.
    DRF typically returns 401; SessionAuthentication can return 403 or
    302 (redirect to login). Accept the common rejected-set."""
    if BASE_URL:
        import requests
        r = requests.get(BASE_URL.rstrip("/") + LIST_PATH, timeout=5)
    else:
        from django.test import Client
        r = Client().get(LIST_PATH)
    assert _status(r) in (401, 403, 302), (
        f"expected auth rejection, got {_status(r)}"
    )


def test_list_endpoint_with_auth_returns_200(client, seed_user):
    """5. Authenticated read of a list endpoint — exercises auth wiring +
    a representative DRF ViewSet end-to-end."""
    r = _get(client, LIST_PATH)
    assert _status(r) == 200, f"authenticated list failed: status={_status(r)}"
    body = _json(r)
    # DRF paginated responses wrap in {"results": [...]}; non-paginated
    # return a bare list. Accept either.
    assert body is not None
    assert isinstance(body, list) or "results" in body


def test_create_record_happy_path(client, seed_user):
    """6. Primary write path. Idempotency note: smoke writes must either
    use ephemeral data with cleanup OR be guarded against prod. In-process
    runs roll back via the `db` fixture's transaction; deployed runs hit
    a real DB — set SMOKE_ALLOW_WRITE=1 to opt in.

    TODO: replace the payload below with the minimal valid body your
    serializer accepts."""
    if BASE_URL and os.getenv("SMOKE_ALLOW_WRITE") != "1":
        pytest.skip("write smoke disabled against deployed URL; set SMOKE_ALLOW_WRITE=1 to enable")
    payload = {"items": ["smoke"]}  # TODO: real minimal payload
    r = _post(client, WRITE_PATH, payload)
    assert _status(r) in (200, 201), (
        f"create failed: status={_status(r)} body={_json(r)!r}"
    )
    body = _json(r)
    assert body is not None and ("id" in body or "pk" in body), (
        "expected created record to echo back an id"
    )


# ---- CI wiring (optional) --------------------------------------------------
# Minimal GitHub Actions snippet — drop into .github/workflows/smoke.yml:
#
#   name: smoke
#   on: [push, pull_request]
#   jobs:
#     smoke:
#       runs-on: ubuntu-latest
#       steps:
#         - uses: actions/checkout@v4
#         - uses: actions/setup-python@v5
#           with: { python-version: "3.12" }
#         - run: pip install -e .[dev]
#         - run: pytest tests/smoke -q
#           env:
#             DJANGO_SETTINGS_MODULE: myproject.settings  # TODO
