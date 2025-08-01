import os
import logging
from typing import Optional

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from . import utils  # adjust if your import path differs

logger = logging.getLogger(__name__)

# Scopes you need; expand if you add more functionality
SCOPE = ",".join(
    [
        "user-read-playback-state",
        "user-modify-playback-state",
        "playlist-modify-private",
        "playlist-modify-public",
        "user-read-currently-playing",
    ]
)

# Use environment or fallback
CACHE_PATH = os.getenv("SPOTIFY_CACHE_PATH", ".cache-spotify")  # file persisted across restarts if directory is writable
CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "")
REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI", "")

def _make_oauth():
    return SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=SCOPE,
        cache_path=CACHE_PATH,
        show_dialog=False,  # set True if you want forced consent occasionally
    )

def get_spotify_client() -> Optional[spotipy.Spotify]:
    oauth = _make_oauth()
    token_info = oauth.get_cached_token()
    if not token_info:
        # Not yet authenticated
        return None
    # Spotipy will auto-refresh if expired when calling get_access_token
    try:
        access_token = oauth.get_access_token(as_dict=False)
    except Exception as e:
        logger.error("Failed getting access token: %s", e)
        return None
    return spotipy.Spotify(auth=access_token)

# === OAuth helpers ===
def get_auth_url():
    oauth = _make_oauth()
    return oauth.get_authorize_url()

def handle_callback(code: str):
    oauth = _make_oauth()
    token_info = oauth.get_access_token(code=code)
    # This writes to cache_path automatically
    return token_info

# === Wrapped actions ===
def get_current_song():
    sp = get_spotify_client()
    if not sp:
        return None, None
    playback = sp.current_playback()
    if not playback or not playback.get("item"):
        return None, None
    item = playback["item"]
    name = item.get("name")
    artists = ", ".join([a.get("name") for a in item.get("artists", [])])
    return name, artists

def play_playlist(playlist_uri: str):
    sp = get_spotify_client()
    if not sp:
        return {"error": "not authenticated"}
    try:
        sp.start_playback(context_uri=playlist_uri)
        return {"status": "playing playlist", "uri": playlist_uri}
    except Exception as e:
        logger.exception("play_playlist failed")
        return {"error": str(e)}

def play_track(track_uri: str):
    sp = get_spotify_client()
    if not sp:
        return {"error": "not authenticated"}
    try:
        sp.start_playback(uris=[track_uri])
        return {"status": "playing track", "uri": track_uri}
    except Exception as e:
        logger.exception("play_track failed")
        return {"error": str(e)}

def play_song_radio(song_uri: str):
    sp = get_spotify_client()
    if not sp:
        return {"error": "not authenticated"}
    try:
        # Spotify doesn’t have an explicit “radio” endpoint; seed a recommendation and play
        recs = sp.recommendations(seed_tracks=[song_uri.split(":")[-1]], limit=10)
        uris = [t["uri"] for t in recs.get("tracks", [])]
        if not uris:
            return {"error": "no recommendations found"}
        sp.start_playback(uris=uris)
        return {"status": "started song radio", "seed": song_uri, "played": uris[:3]}
    except Exception as e:
        logger.exception("play_song_radio failed")
        return {"error": str(e)}

def play_next_track():
    sp = get_spotify_client()
    if not sp:
        return {"error": "not authenticated"}
    try:
        sp.next_track()
        return {"status": "skipped"}
    except Exception as e:
        logger.exception("play_next_track failed")
        return {"error": str(e)}

def resume_playback():
    sp = get_spotify_client()
    if not sp:
        return {"error": "not authenticated"}
    try:
        sp.start_playback()
        return {"status": "resumed"}
    except Exception as e:
        logger.exception("resume_playback failed")
        return {"error": str(e)}

def pause_playback():
    sp = get_spotify_client()
    if not sp:
        return {"error": "not authenticated"}
    try:
        sp.pause_playback()
        return {"status": "paused"}
    except Exception as e:
        logger.exception("pause_playback failed")
        return {"error": str(e)}

def previous_track():
    sp = get_spotify_client()
    if not sp:
        return {"error": "not authenticated"}
    try:
        sp.previous_track()
        return {"status": "previous"}
    except Exception as e:
        logger.exception("previous_track failed")
        return {"error": str(e)}

def set_volume(level: int):
    sp = get_spotify_client()
    if not sp:
        return {"error": "not authenticated"}
    try:
        sp.volume(level)
        return {"status": "volume set", "level": level}
    except Exception as e:
        logger.exception("set_volume failed")
        return {"error": str(e)}

def search_tracks(query: str):
    sp = get_spotify_client()
    if not sp:
        return None
    try:
        result = sp.search(q=query, type="track", limit=10)
        return result.get("tracks", {}).get("items", [])
    except Exception as e:
        logger.exception("search_tracks failed")
        return None

def get_recommendations(seed_tracks=None, seed_artists=None, seed_genres=None, limit=10):
    sp = get_spotify_client()
    if not sp:
        return []
    kwargs = {"limit": limit}
    if seed_tracks:
        kwargs["seed_tracks"] = [t.split(":")[-1] for t in seed_tracks]
    if seed_artists:
        kwargs["seed_artists"] = [a.split(":")[-1] for a in seed_artists]
    if seed_genres:
        kwargs["seed_genres"] = seed_genres
    try:
        recs = sp.recommendations(**kwargs)
        return recs.get("tracks", [])
    except Exception as e:
        logger.exception("get_recommendations failed")
        return []

def create_playlist(name: str, description: str = "", public: bool = False):
    sp = get_spotify_client()
    if not sp:
        return {"error": "not authenticated"}
    try:
        user = sp.current_user()
        playlist = sp.user_playlist_create(
            user=user["id"], name=name, public=public, description=description
        )
        return playlist
    except Exception as e:
        logger.exception("create_playlist failed")
        return {"error": str(e)}

def add_tracks_to_playlist(playlist_id: str, uris: list[str]):
    sp = get_spotify_client()
    if not sp:
        return {"error": "not authenticated"}
    try:
        sp.playlist_add_items(playlist_id, uris)
        return {"status": "added", "playlist_id": playlist_id, "uris": uris}
    except Exception as e:
        logger.exception("add_tracks_to_playlist failed")
        return {"error": str(e)}

def get_user_playlists(limit=20):
    sp = get_spotify_client()
    if not sp:
        return []
    try:
        playlists = sp.current_user_playlists(limit=limit)
        return playlists.get("items", [])
    except Exception as e:
        logger.exception("get_user_playlists failed")
        return []

def get_playlist_tracks(playlist_id: str):
    sp = get_spotify_client()
    if not sp:
        return []
    try:
        results = sp.playlist_tracks(playlist_id)
        return [item["track"] for item in results.get("items", [])]
    except Exception as e:
        logger.exception("get_playlist_tracks failed")
        return []

def get_user_profile():
    sp = get_spotify_client()
    if not sp:
        return {}
    try:
        return sp.current_user()
    except Exception as e:
        logger.exception("get_user_profile failed")
        return {}