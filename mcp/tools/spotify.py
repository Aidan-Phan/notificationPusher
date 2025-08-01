import os
import logging
from typing import Optional

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from mcp.config import (
    SPOTIFY_CLIENT_ID,
    SPOTIFY_CLIENT_SECRET,
    SPOTIFY_REDIRECT_URI,
)

# === internal client retrieval ===
_TOKEN_CACHE_PATH = os.path.join(os.getcwd(), "mcp_spotify_token_cache")


def _get_auth_manager(show_dialog: bool = False) -> SpotifyOAuth:
    return SpotifyOAuth(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri=SPOTIFY_REDIRECT_URI,
        scope=(
            "user-read-playback-state user-modify-playback-state "
            "playlist-read-private playlist-modify-private playlist-modify-public user-read-private"
        ),
        cache_path=_TOKEN_CACHE_PATH,
        show_dialog=show_dialog,
    )


def _get_spotify_client() -> spotipy.Spotify:
    auth_manager = _get_auth_manager()
    token_info = auth_manager.get_cached_token()
    if not token_info:
        # Force interactive auth if none cached
        auth_manager = _get_auth_manager(show_dialog=True)
    return spotipy.Spotify(auth_manager=auth_manager)


# === Spotify operations ===

def get_track(track_uri: str) -> dict:
    try:
        sp = _get_spotify_client()
        return sp.track(track_uri)
    except Exception as e:
        logging.error("get_track error: %s", e)
        return {"name": track_uri, "error": str(e)}


def search_tracks(query: str, limit: int = 10) -> Optional[list]:
    try:
        sp = _get_spotify_client()
        res = sp.search(q=query, type="track", limit=limit)
        return res.get("tracks", {}).get("items", [])
    except Exception as e:
        logging.error("Error in search_tracks: %s", e)
        return None


def get_recommendations(
    seed_tracks: Optional[list] = None,
    seed_artists: Optional[list] = None,
    seed_genres: Optional[list] = None,
    limit: int = 10,
) -> list:
    try:
        sp = _get_spotify_client()
        return (
            sp.recommendations(
                seed_tracks=seed_tracks or [],
                seed_artists=seed_artists or [],
                seed_genres=seed_genres or [],
                limit=limit,
            )
            .get("tracks", [])
        )
    except Exception as e:
        logging.error("get_recommendations error: %s", e)
        return []


def play_track(track_uri: str):
    try:
        sp = _get_spotify_client()
        return sp.start_playback(uris=[track_uri])
    except Exception as e:
        logging.error("play_track error: %s", e)
        return {"error": str(e)}


def next_track():
    try:
        sp = _get_spotify_client()
        return sp.next_track()
    except Exception as e:
        logging.error("next_track error: %s", e)
        return {"error": str(e)}


def previous_track():
    try:
        sp = _get_spotify_client()
        return sp.previous_track()
    except Exception as e:
        logging.error("previous_track error: %s", e)
        return {"error": str(e)}


def pause_playback():
    try:
        sp = _get_spotify_client()
        return sp.pause_playback()
    except Exception as e:
        logging.error("pause_playback error: %s", e)
        return {"error": str(e)}


def resume_playback():
    try:
        sp = _get_spotify_client()
        return sp.start_playback()
    except Exception as e:
        logging.error("resume_playback error: %s", e)
        return {"error": str(e)}


def play_playlist(playlist_uri: str):
    try:
        sp = _get_spotify_client()
        return sp.start_playback(context_uri=playlist_uri)
    except Exception as e:
        logging.error("play_playlist error: %s", e)
        return {"error": str(e)}


def play_song_radio(track_uri: str):
    try:
        sp = _get_spotify_client()
        # Spotify's recommendation radio can be approximated via seed track recommendations
        recs = sp.recommendations(seed_tracks=[track_uri], limit=20)
        uris = [t["uri"] for t in recs.get("tracks", [])]
        if uris:
            return sp.start_playback(uris=uris)
        return {"message": "no radio recommendations available"}
    except Exception as e:
        logging.error("play_song_radio error: %s", e)
        return {"error": str(e)}


def create_playlist(name: str, description: str = "", public: bool = False):
    try:
        sp = _get_spotify_client()
        user = sp.current_user()
        return sp.user_playlist_create(
            user=user.get("id"), name=name, public=public, description=description
        )
    except Exception as e:
        logging.error("create_playlist error: %s", e)
        return None


def add_tracks_to_playlist(playlist_id: str, track_uris: list):
    try:
        sp = _get_spotify_client()
        return sp.playlist_add_items(playlist_id, track_uris)
    except Exception as e:
        logging.error("add_tracks_to_playlist error: %s", e)
        return None


def get_user_playlists(limit: int = 20):
    try:
        sp = _get_spotify_client()
        res = sp.current_user_playlists(limit=limit)
        return res.get("items", [])
    except Exception as e:
        logging.error("get_user_playlists error: %s", e)
        return []


def get_playlist_tracks(playlist_id: str):
    try:
        sp = _get_spotify_client()
        items = []
        results = sp.playlist_items(playlist_id)
        items.extend(results.get("items", []))
        while results.get("next"):
            results = sp.next(results)
            items.extend(results.get("items", []))
        return items
    except Exception as e:
        logging.error("get_playlist_tracks error: %s", e)
        return []


def get_current_song():
    try:
        sp = _get_spotify_client()
        playback = sp.current_playback()
        if not playback or not playback.get("item"):
            return None, None
        item = playback["item"]
        name = item.get("name")
        artists = ", ".join(a.get("name") for a in item.get("artists", []))
        return name, artists
    except Exception as e:
        logging.error("get_current_song error: %s", e)
        return None, None


def set_volume(level: int):
    try:
        sp = _get_spotify_client()
        return sp.volume(level)
    except Exception as e:
        logging.error("set_volume error: %s", e)
        return {"error": str(e)}


def get_user_profile():
    try:
        sp = _get_spotify_client()
        return sp.current_user()
    except Exception as e:
        logging.error("get_user_profile error: %s", e)
        return None