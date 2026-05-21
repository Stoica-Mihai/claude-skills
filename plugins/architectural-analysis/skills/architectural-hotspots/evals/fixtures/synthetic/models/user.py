from models import order
from utils import helpers

class User:
    def __init__(self, id, name):
        self.id = id
        self.name = helpers.title_case(name)

    def orders(self):
        return order.find_by_user(self.id)
