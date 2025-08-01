# config.py
import os

# Pushover
PUSHOVER_USER_KEY = os.getenv("PUSHOVER_USER_KEY", "uwszt9xo39jbsyk97devir32oibdqt")
PUSHOVER_API_TOKEN = os.getenv("PUSHOVER_API_TOKEN", "aqs7ermxrs3t1h9ojfn1nzd7moqk9m")

# Spotify
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "8b6ba557b3d448d7a4e028711be38abc")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "8732f3bea44d4411b3d55398a0059446")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI", "https://notificationspotifymcp.onrender.com/auth/callback")

