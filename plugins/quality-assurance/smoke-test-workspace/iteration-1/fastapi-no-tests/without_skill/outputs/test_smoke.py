"""Smoke tests for the orders-api FastAPI fixture.

Covers every route in app.py: /health, /users/{user_id}, POST /orders,
/orders/{order_id}. Each route is hit on its happy path and on its
documented error paths so a broken deploy fails fast.

Run with:  pytest -q test_smoke.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

FIXTURE_DIR = Path(
    "/home/mcs/Documents/git/claude-skills/plugins/quality-assurance/"
    "skills/smoke-test/evals/fixtures/fastapi-app"
)
if str(FIXTURE_DIR) not in sys.path:
    sys.path.insert(0, str(FIXTURE_DIR))

import app as app_module  # noqa: E402


@pytest.fixture()
def client() -> TestClient:
    """Fresh TestClient with reset in-memory state per test."""
    app_module._ORDERS.clear()
    app_module._NEXT_ORDER_ID = 1
    return TestClient(app_module.app)


# ---------- /health ----------

def test_health_ok(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


# ---------- /users/{user_id} ----------

def test_get_user_happy(client: TestClient) -> None:
    r = client.get("/users/1")
    assert r.status_code == 200
    assert r.json() == {"id": 1, "name": "alice"}


def test_get_user_not_found(client: TestClient) -> None:
    r = client.get("/users/999")
    assert r.status_code == 404
    assert r.json()["detail"] == "user not found"


def test_get_user_bad_type(client: TestClient) -> None:
    # path param is typed int → FastAPI returns 422 on non-int
    r = client.get("/users/not-a-number")
    assert r.status_code == 422


# ---------- POST /orders ----------

def test_create_order_happy(client: TestClient) -> None:
    r = client.post(
        "/orders",
        json={"user_id": 1, "items": ["book", "pen"]},
        headers={"Authorization": "Bearer test-token"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body == {"id": 1, "user_id": 1, "items": ["book", "pen"]}


def test_create_order_missing_auth(client: TestClient) -> None:
    r = client.post("/orders", json={"user_id": 1, "items": ["book"]})
    assert r.status_code == 401
    assert r.json()["detail"] == "missing token"


def test_create_order_wrong_auth_scheme(client: TestClient) -> None:
    r = client.post(
        "/orders",
        json={"user_id": 1, "items": ["book"]},
        headers={"Authorization": "Basic abc"},
    )
    assert r.status_code == 401


def test_create_order_unknown_user(client: TestClient) -> None:
    r = client.post(
        "/orders",
        json={"user_id": 9999, "items": ["book"]},
        headers={"Authorization": "Bearer t"},
    )
    assert r.status_code == 400
    assert r.json()["detail"] == "unknown user"


def test_create_order_bad_payload(client: TestClient) -> None:
    # missing required `items`
    r = client.post(
        "/orders",
        json={"user_id": 1},
        headers={"Authorization": "Bearer t"},
    )
    assert r.status_code == 422


def test_create_order_increments_id(client: TestClient) -> None:
    headers = {"Authorization": "Bearer t"}
    r1 = client.post("/orders", json={"user_id": 1, "items": ["a"]}, headers=headers)
    r2 = client.post("/orders", json={"user_id": 2, "items": ["b"]}, headers=headers)
    assert r1.json()["id"] == 1
    assert r2.json()["id"] == 2
    assert r2.json()["user_id"] == 2


# ---------- /orders/{order_id} ----------

def test_get_order_happy(client: TestClient) -> None:
    headers = {"Authorization": "Bearer t"}
    created = client.post(
        "/orders", json={"user_id": 1, "items": ["x"]}, headers=headers
    ).json()
    r = client.get(f"/orders/{created['id']}")
    assert r.status_code == 200
    assert r.json() == created


def test_get_order_not_found(client: TestClient) -> None:
    r = client.get("/orders/424242")
    assert r.status_code == 404
    assert r.json()["detail"] == "order not found"
