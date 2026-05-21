from services import notification_service
from utils import helpers

def handle_send(req):
    return notification_service.notify(req["user"], helpers.truncate(req["message"], 200))
