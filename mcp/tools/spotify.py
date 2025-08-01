import os
import logging
from typing import List, Optional

import spotipy
from spotipy.oauth2 import SpotifyOAuth

# Configuration from env; expected to be set in your deployment env vars
CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "")
REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI", "")
SCOPE = ",".join(
    [
        "user-read-playback-state",
        "user-modify-playback-state",
        "user-read-currently-playing",
        "playlist-read-private",
        "playlist-modify-private",
        "playlist-modify-public",
        "user-read-email",
        "user-read-private",
    ]
)
CACHE_PATH = os.getenv("SPOTIFY_CACHE_PATH", ".spotifycache")  # persistent cache file

_logger = logging.getLogger(__name__)


def _get_oauth():
    if not CLIENT_ID or not CLIENT_SECRET or not REDIRECT_URI:
        raise RuntimeError("Spotify credentials (CLIENT_ID/SECRET/REDIRECT_URI) not configured.")
    return SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=SCOPE,
        cache_path=CACHE_PATH,
        show_dialog=False,
    )


def _get_client():
    auth_manager = _get_oauth()
    token_info = auth_manager.get_cached_token()
    if not token_info:
        return None  # caller must trigger auth flow
    sp = spotipy.Spotify(auth_manager=auth_manager)
    return sp


def get_auth_url() -> str:
    oauth = _get_oauth()
    return oauth.get_authorize_url()


def handle_callback(code: str) -> dict:
    oauth = _get_oauth()
    token_info = oauth.get_access_token(code)
    return token_info


def _ensure_client():
    sp = _get_client()
    if sp is None:
        raise RuntimeError("No Spotify token cached. Authenticate via /auth/start and /auth/callback first.")
    return sp


def get_current_song():
    sp = _ensure_client()
    playback = sp.current_playback()
    if not playback or not playback.get("item"):
        return None, None
    item = playback["item"]
    song = item.get("name")
    artists = [a.get("name") for a in item.get("artists", [])]
    artist = ", ".join(artists)
    return song, artist


def play_playlist(playlist_uri: str):
    sp = _ensure_client()
    return sp.start_playback(context_uri=playlist_uri)


def play_song_radio(seed_track_uri: str):
    sp = _ensure_client()
    recs = sp.recommendations(seed_tracks=[seed_track_uri], limit=20)
    uris = [t["uri"] for t in recs.get("tracks", [])]
    if not uris:
        return {"error": "no recommendations found"}
    return sp.start_playback(uris=uris)


def play_next_track():
    sp = _ensure_client()
    return sp.next_track()


def play_track(track_uri: str):
    sp = _ensure_client()
    return sp.start_playback(uris=[track_uri])


def resume_playback():
    sp = _ensure_client()
    return sp.start_playback()


def pause_playback():
    sp = _ensure_client()
    return sp.pause_playback()


def previous_track():
    sp = _ensure_client()
    return sp.previous_track()


def set_volume(volume_percent: int):
    sp = _ensure_client()
    return sp.volume(volume_percent)


def search_tracks(query: str, limit: int = 10):
    sp = _ensure_client()
    result = sp.search(q=query, type="track", limit=limit)
    return result.get("tracks", {}).get("items", [])


def get_recommendations(
    seed_tracks: Optional[List[str]] = None,
    seed_artists: Optional[List[str]] = None,
    seed_genres: Optional[List[str]] = None,
    limit: int = 10,
):
    sp = _ensure_client()
    params = {}
    if seed_tracks:
        params["seed_tracks"] = seed_tracks[:5]
    if seed_artists:
        params["seed_artists"] = seed_artists[:5]
    if seed_genres:
        params["seed_genres"] = seed_genres[:5]
    params["limit"] = limit
    recs = sp.recommendations(**params)
    return recs.get("tracks", [])


def create_playlist(name: str, description: str = "", public: bool = False):
    sp = _ensure_client()
    user = sp.current_user()
    user_id = user.get("id")
    if not user_id:
        return None
    return sp.user_playlist_create(user_id, name, public=public, description=description)


def add_tracks_to_playlist(playlist_id: str, track_uris: List[str]):
    sp = _ensure_client()
    return sp.playlist_add_items(playlist_id, track_uris)


def get_user_profile():
    sp = _ensure_client()
    return sp.current_user()


def get_user_playlists(limit: int = 20):
    sp = _ensure_client()
    pls = sp.current_user_playlists(limit=limit)
    items = pls.get("items", [])
    return [{"name": p.get("name"), "id": p.get("id"), "uri": p.get("uri")} for p in items]


def get_playlist_tracks(playlist_id: str):
    sp = _ensure_client()
    all_tracks = []
    results = sp.playlist_items(playlist_id)
    all_tracks.extend(results.get("items", []))
    while results.get("next"):
        results = sp.next(results)
        all_tracks.extend(results.get("items", []))
    simplified = []
    for entry in all_tracks:
        t = entry.get("track") or {}
        simplified.append(
            {
                "name": t.get("name"),
                "artists": [a.get("name") for a in t.get("artists", [])],
                "uri": t.get("uri"),
            }
        )
    return simplified