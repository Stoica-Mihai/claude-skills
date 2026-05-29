"""
Smoke tests — verify the build is stable enough to test further.

Scope: broad, shallow, idempotent-safe. NOT a regression suite.
Runtime budget: < 2 s in-process, < 30 s against a deployed URL.

Run locally (in-process):
    pytest tests/smoke -q

Run against a deployed environment:
    SMOKE_BASE_URL=https://api.example.com \
    SMOKE_TOKEN=eyJ... \
    pytest tests/smoke -q
"""
import os

import httpx
import pytest

# TODO: update import path if the app object lives elsewhere.
from app import app  # noqa: E402

# When SMOKE_BASE_URL is set, hit the deployed service.
# Otherwise drive the app in-process for sub-second runs.
BASE_URL = os.getenv("SMOKE_BASE_URL")
# TODO: wire a real token in CI; the in-process app only checks the "Bearer " prefix.
TOKEN = os.getenv("SMOKE_TOKEN", "smoke-token-placeholder")


@pytest.fixture
def client():
    if BASE_URL:
        with httpx.Client(base_url=BASE_URL, timeout=5.0) as c:
            yield c
    else:
        from fastapi.testclient import TestClient

        with TestClient(app) as c:
            yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200, r.text
    assert r.json().get("status") == "ok"


def test_get_known_user(client):
    r = client.get("/users/1")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["id"] == 1
    assert "name" in body


def test_missing_user_returns_404(client):
    r = client.get("/users/99999")
    assert r.status_code == 404, r.text


def test_create_order_requires_auth(client):
    r = client.post("/orders", json={"user_id": 1, "items": ["smoke-item"]})
    assert r.status_code == 401, r.text


def test_create_order_happy_path(client):
    r = client.post(
        "/orders",
        json={"user_id": 1, "items": ["smoke-item"]},
        headers={"authorization": f"Bearer {TOKEN}"},
    )
    assert r.status_code in (200, 201), r.text
    body = r.json()
    assert body["user_id"] == 1
    assert isinstance(body.get("id"), int)
    # Pinned for the round-trip check below.
    pytest.created_order_id = body["id"]


def test_get_created_order_roundtrip(client):
    oid = getattr(pytest, "created_order_id", None)
    if oid is None:
        pytest.skip("create-order test did not pin an id")
    r = client.get(f"/orders/{oid}")
    assert r.status_code == 200, r.text
    assert r.json()["id"] == oid
