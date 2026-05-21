from models import user
from utils import helpers

def find_by_user(user_id):
    return []

def total(order):
    return helpers.format_currency(order.amount)

def owner(order_id):
    return user.User(1, "alice")
