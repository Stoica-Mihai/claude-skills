from models import user
from utils import helpers

def handle_create(req):
    return user.User(req["id"], helpers.title_case(req["name"]))
