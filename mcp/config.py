import os
from dotenv import load_dotenv

load_dotenv()

# Spotify
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")

# Pushover
PUSHOVER_API_TOKEN = os.getenv("PUSHOVER_API_TOKEN")
PUSHOVER_USER_KEY = os.getenv("PUSHOVER_USER_KEY")

def validate_spotify():
    missing = []
    if not SPOTIFY_CLIENT_ID:
        missing.append("SPOTIFY_CLIENT_ID")
    if not SPOTIFY_CLIENT_SECRET:
        missing.append("SPOTIFY_CLIENT_SECRET")
    if not SPOTIFY_REDIRECT_URI:
        missing.append("SPOTIFY_REDIRECT_URI")
    if missing:
        raise RuntimeError(f"Missing Spotify config env vars: {', '.join(missing)}")

def validate_pushover():
    missing = []
    if not PUSHOVER_API_TOKEN:
        missing.append("PUSHOVER_API_TOKEN")
    if not PUSHOVER_USER_KEY:
        missing.append("PUSHOVER_USER_KEY")
    if missing:
        raise RuntimeError(f"Missing Pushover config env vars: {', '.join(missing)}")