import os
from dotenv import load_dotenv

load_dotenv()

# Spotify credentials (must be set as environment variables on Render or in .env)
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI", "")

# Simple owner API key for identity
AIDAN_API_KEY = os.getenv("AIDAN_API_KEY", "")

# Pushover (if you use it)
PUSHOVER_USER_KEY = os.getenv("PUSHOVER_USER_KEY", "")
PUSHOVER_API_TOKEN = os.getenv("PUSHOVER_API_TOKEN", "")


def validate():
    missing = []
    if not SPOTIFY_CLIENT_ID:
        missing.append("SPOTIFY_CLIENT_ID")
    if not SPOTIFY_CLIENT_SECRET:
        missing.append("SPOTIFY_CLIENT_SECRET")
    if not SPOTIFY_REDIRECT_URI:
        missing.append("SPOTIFY_REDIRECT_URI")
    if not AIDAN_API_KEY:
        missing.append("AIDAN_API_KEY")
    if missing:
        raise ValueError(f"Missing required config values: {', '.join(missing)}")
    if not SPOTIFY_REDIRECT_URI.startswith(("http://", "https://")):
        raise ValueError("SPOTIFY_REDIRECT_URI must be a valid URL starting with http:// or https://")
    return True