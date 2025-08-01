import requests
from ..config import PUSHOVER_USER_KEY, PUSHOVER_API_TOKEN

def send_notification(title, message):
    data = {
        "token": PUSHOVER_API_TOKEN,
        "user": PUSHOVER_USER_KEY,
        "title": title,
        "message": message
    }

    response = requests.post("https://api.pushover.net/1/messages.json", data=data)
    print("Status:", response.status_code)
    print("Response:", response.json())
    return response.json()