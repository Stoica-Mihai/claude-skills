from utils import helpers
from models import user

def notify(user_id, message):
    u = user.User(user_id, "buyer")
    return helpers.truncate(message, 140)
