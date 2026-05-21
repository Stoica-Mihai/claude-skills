from core import config, db
from models import user, order, audit
from utils import helpers


def place_order(user_id, items):
    db.connect()
    u = user.User(user_id, "buyer")
    o = order.find_by_user(u.id)
    audit.log({"event": "place_order", "user": u.id})
    total = sum(i["price"] for i in items)
    return helpers.format_currency(total)


def cancel_order(order_id):
    audit.log({"event": "cancel", "order": order_id})
    return True


def refund_order(order_id):
    if config.DEBUG:
        print("refunding", order_id)
    audit.log({"event": "refund", "order": order_id})
    return True
