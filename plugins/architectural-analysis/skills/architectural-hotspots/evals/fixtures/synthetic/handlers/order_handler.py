from services import order_service
from utils import helpers

def handle_create(req):
    return order_service.place_order(req["user"], req["items"])

def handle_cancel(req):
    return order_service.cancel_order(req["order_id"])

def handle_refund(req):
    return order_service.refund_order(req["order_id"])
