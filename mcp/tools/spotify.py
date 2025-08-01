from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from config import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_URI
import os

scope = "user-read-playback-state user-modify-playback-state"

auth_manager = SpotifyOAuth(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET,
    redirect_uri=SPOTIFY_REDIRECT_URI,
    scope=scope,
    cache_path=os.path.expanduser("~/.cache/mcp_spotify_token")
)

# ✅ This must exist
sp = Spotify(auth_manager=auth_manager)

def play_playlist(uri):
    try:
        sp.start_playback(context_uri=uri)
        return {"status": "playing", "uri": uri}
    except Exception as e:
        print("Spotify playback error:", e)
        return {"error": str(e)}

def play_song_radio(song_uri):
    try:
        sp.start_playback(context_uri=f"spotify:radio:{song_uri}")
        return {"status": "playing radio", "uri": song_uri}
    except Exception as e:
        print("Song radio error:", e)
        return {"error": str(e)}

def play_next_track():
    try:
        sp.next_track()
        return {"status": "skipped to next track"}
    except Exception as e:
        print("Next track error:", e)
        return {"error": str(e)}

def play_track(uri):
    try:
        sp.start_playback(uris=[uri])
        return {"status": "playing track", "uri": uri}
    except Exception as e:
        print("Track playback error:", e)
        return {"error": str(e)}

def resume_playback():
    try:
        sp.start_playback()
        return {"status": "resumed playback"}
    except Exception as e:
        print("Resume playback error:", e)
        return {"error": str(e)}