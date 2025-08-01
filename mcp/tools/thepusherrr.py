import os
import requests
from ..config import PUSHOVER_API_TOKEN, PUSHOVER_USER_KEY

def send_notification(title: str, message: str):
    # validate presence
    if not PUSHOVER_API_TOKEN or not PUSHOVER_USER_KEY:
        raise RuntimeError("Pushover credentials are missing.")

    payload = {
        "token": PUSHOVER_API_TOKEN,
        "user": PUSHOVER_USER_KEY,
        "message": message,
        "title": title,
    }
    resp = requests.post("https://api.pushover.net/1/messages.json", data=payload)
    try:
        resp.raise_for_status()
    except Exception:
        # bubble error with body for debugging
        raise RuntimeError(f"Pushover failed: {resp.status_code} {resp.text}")
    return {"status_code": resp.status_code, "response": resp.json()}