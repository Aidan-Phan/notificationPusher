import requests
from ..config import PUSHOVER_USER_KEY, PUSHOVER_API_TOKEN

def send_notification(title, message):
    """
    Send a push notification via Pushover.
    """
    data = {
        "token": PUSHOVER_API_TOKEN,
        "user": PUSHOVER_USER_KEY,
        "title": title,
        "message": message
    }

    response = requests.post("https://api.pushover.net/1/messages.json", data=data)
    print("Pushover status:", response.status_code)
    print("Pushover response:", response.json())
    return response.json()