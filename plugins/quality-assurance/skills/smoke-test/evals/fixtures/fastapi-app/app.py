"""Tiny FastAPI fixture for smoke-test eval — orders + users API."""
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel

app = FastAPI(title="orders-api")

_USERS = {1: {"id": 1, "name": "alice"}, 2: {"id": 2, "name": "bob"}}
_ORDERS: dict[int, dict] = {}
_NEXT_ORDER_ID = 1


class OrderIn(BaseModel):
    user_id: int
    items: list[str]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/users/{user_id}")
def get_user(user_id: int):
    user = _USERS.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="user not found")
    return user


@app.post("/orders")
def create_order(payload: OrderIn, authorization: str = Header(default="")):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing token")
    if payload.user_id not in _USERS:
        raise HTTPException(status_code=400, detail="unknown user")
    global _NEXT_ORDER_ID
    oid = _NEXT_ORDER_ID
    _NEXT_ORDER_ID += 1
    _ORDERS[oid] = {"id": oid, "user_id": payload.user_id, "items": payload.items}
    return _ORDERS[oid]


@app.get("/orders/{order_id}")
def get_order(order_id: int):
    o = _ORDERS.get(order_id)
    if not o:
        raise HTTPException(status_code=404, detail="order not found")
    return o
