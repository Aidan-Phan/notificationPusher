import os
import time
import logging
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from requests.exceptions import RequestException
from typing import List, Tuple, Optional, Dict

from ..config import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_URI

# Scope needed for playback control, playlist management, and recommendations
SCOPE = "user-read-playback-state user-modify-playback-state playlist-read-private playlist-modify-private playlist-modify-public user-read-private"

# Lazy singleton pattern for Spotify client with token caching
_sp_client: Optional[Spotify] = None

def get_spotify_client() -> Spotify:
    global _sp_client
    if _sp_client is None:
        auth_manager = SpotifyOAuth(
            client_id=SPOTIFY_CLIENT_ID,
            client_secret=SPOTIFY_CLIENT_SECRET,
            redirect_uri=SPOTIFY_REDIRECT_URI,
            scope=SCOPE,
            cache_path=os.path.expanduser("~/.cache/mcp_spotify_token"),
            show_dialog=False,
        )
        _sp_client = Spotify(auth_manager=auth_manager)
    return _sp_client

# Helper for retries with exponential backoff
def retry(func):
    def wrapper(*args, **kwargs):
        delay = 1
        for attempt in range(4):
            try:
                return func(*args, **kwargs)
            except RequestException as e:
                logging.warning(f"Spotify network error on {func.__name__}: {e}, retrying in {delay}s")
                time.sleep(delay)
                delay *= 2
            except Exception as e:
                logging.error(f"Error in {func.__name__}: {e}")
                break
        return None
    return wrapper

@retry
def get_current_song() -> Tuple[Optional[str], Optional[str]]:
    sp = get_spotify_client()
    playback = sp.current_playback()
    if not playback or not playback.get("item"):
        return None, None
    item = playback["item"]
    song = item.get("name")
    artists = item.get("artists", [])
    artist = artists[0]["name"] if artists else None
    return song, artist

@retry
def search_tracks(query: str, limit: int = 5) -> List[Dict]:
    sp = get_spotify_client()
    result = sp.search(q=query, type="track", limit=limit)
    tracks = result.get("tracks", {}).get("items", [])
    return tracks

@retry
def get_user_profile() -> Dict:
    sp = get_spotify_client()
    return sp.current_user()

@retry
def get_user_playlists(limit: int = 20) -> List[Dict]:
    sp = get_spotify_client()
    playlists = []
    response = sp.current_user_playlists(limit=limit)
    playlists.extend(response.get("items", []))
    while response.get("next"):
        response = sp.next(response)
        playlists.extend(response.get("items", []))
    return playlists

@retry
def get_playlist_tracks(playlist_id: str, limit: int = 100) -> List[Dict]:
    sp = get_spotify_client()
    tracks = []
    response = sp.playlist_items(playlist_id, limit=limit)
    tracks.extend(response.get("items", []))
    while response.get("next"):
        response = sp.next(response)
        tracks.extend(response.get("items", []))
    return tracks

@retry
def create_playlist(name: str, description: str = "", public: bool = False) -> Optional[Dict]:
    sp = get_spotify_client()
    user = sp.current_user()
    playlist = sp.user_playlist_create(user["id"], name, public=public, description=description)
    return playlist

@retry
def add_tracks_to_playlist(playlist_id: str, track_uris: List[str]) -> Optional[Dict]:
    sp = get_spotify_client()
    return sp.playlist_add_items(playlist_id, track_uris)

@retry
def get_recommendations(seed_tracks: List[str] = None, seed_artists: List[str] = None, seed_genres: List[str] = None, limit: int = 10) -> List[Dict]:
    sp = get_spotify_client()
    seeds = {}
    if seed_tracks:
        seeds["seed_tracks"] = seed_tracks[:5]
    if seed_artists:
        seeds["seed_artists"] = seed_artists[:5]
    if seed_genres:
        seeds["seed_genres"] = seed_genres[:5]
    recs = sp.recommendations(limit=limit, **seeds)
    return recs.get("tracks", [])

@retry
def play_playlist(uri: str) -> Dict:
    sp = get_spotify_client()
    sp.start_playback(context_uri=uri)
    return {"status": "playing playlist", "uri": uri}

@retry
def play_track(uri: str) -> Dict:
    sp = get_spotify_client()
    sp.start_playback(uris=[uri])
    return {"status": "playing track", "uri": uri}

@retry
def play_song_radio(track_uri: str) -> Dict:
    # Spotify removed dedicated radio; emulate with recommendations based on the track
    recs = get_recommendations(seed_tracks=[track_uri], limit=20)
    uris = [t["uri"] for t in recs[:5]]
    if uris:
        sp = get_spotify_client()
        sp.start_playback(uris=uris)
        return {"status": "playing radio-like from", "seed": track_uri, "played": uris}
    return {"status": "no recommendations found for", "seed": track_uri}

@retry
def next_track() -> Dict:
    sp = get_spotify_client()
    sp.next_track()
    return {"status": "skipped to next track"}

@retry
def previous_track() -> Dict:
    sp = get_spotify_client()
    sp.previous_track()
    return {"status": "went to previous track"}

@retry
def resume_playback() -> Dict:
    sp = get_spotify_client()
    sp.start_playback()
    return {"status": "resumed playback"}

@retry
def pause_playback() -> Dict:
    sp = get_spotify_client()
    sp.pause_playback()
    return {"status": "paused playback"}

@retry
def set_volume(volume_percent: int) -> Dict:
    sp = get_spotify_client()
    sp.volume(volume_percent)
    return {"status": "volume set", "volume": volume_percent}