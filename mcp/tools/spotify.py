import logging
from typing import Optional, List, Dict, Any

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from mcp.config import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_URI

logger = logging.getLogger(__name__)

SCOPES = [
    "user-read-playback-state",
    "user-modify-playback-state",
    "playlist-modify-private",
    "playlist-modify-public",
    "user-read-currently-playing",
    "user-read-email",
    "user-read-private",
]

CACHE_PATH = ".spotify_token_cache"  # persistent file in working dir

if not (SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET and SPOTIFY_REDIRECT_URI):
    logger.warning("Spotify credentials missing; auth endpoints will fail.")


def _make_oauth() -> SpotifyOAuth:
    return SpotifyOAuth(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri=SPOTIFY_REDIRECT_URI,
        scope=" ".join(SCOPES),
        cache_path=CACHE_PATH,
        show_dialog=False,
    )


def _get_spotify_client() -> Optional[spotipy.Spotify]:
    oauth = _make_oauth()
    token_info = oauth.get_cached_token()
    if not token_info:
        return None
    access_token = None
    try:
        # Newer spotipy returns a string token when as_dict=False
        access_token = oauth.get_access_token(as_dict=False)
    except Exception:
        # Try refreshing manually
        try:
            refresh_token = token_info.get("refresh_token")
            if not refresh_token:
                return None
            token_info = oauth.refresh_access_token(refresh_token)
            access_token = token_info.get("access_token")
        except Exception:
            logger.exception("Failed to refresh Spotify token")
            return None
    if not access_token:
        return None
    return spotipy.Spotify(auth=access_token)


def get_auth_url() -> str:
    return _make_oauth().get_authorize_url()


def handle_callback(code: str) -> Dict[str, Any]:
    oauth = _make_oauth()
    # This stores the token in cache_path
    token_info = oauth.get_access_token(code=code)
    return token_info


def _unauthenticated_response():
    return {"error": "not authenticated", "action": "visit /auth/start to authenticate"}


def _with_client(func):
    def wrapper(*args, **kwargs):
        sp = _get_spotify_client()
        if not sp:
            return _unauthenticated_response()
        try:
            return func(sp, *args, **kwargs)
        except Exception as e:
            logger.exception("%s failed", func.__name__)
            return {"error": str(e)}
    return wrapper


@_with_client
def get_current_song(sp: spotipy.Spotify):
    playback = sp.current_playback()
    if not playback or not playback.get("item"):
        return {"song": None, "artist": None, "playing": False}
    item = playback["item"]
    name = item.get("name")
    artists = [a.get("name") for a in item.get("artists", [])]
    is_playing = playback.get("is_playing", False)
    return {"song": name, "artists": artists, "playing": is_playing}


@_with_client
def play_playlist(sp: spotipy.Spotify, playlist_uri: str):
    sp.start_playback(context_uri=playlist_uri)
    return {"status": "playing playlist", "uri": playlist_uri}


@_with_client
def play_track(sp: spotipy.Spotify, track_uri: str):
    sp.start_playback(uris=[track_uri])
    return {"status": "playing track", "uri": track_uri}


@_with_client
def play_song_radio(sp: spotipy.Spotify, song_uri: str):
    seed_id = song_uri.split(":")[-1]
    recs = sp.recommendations(seed_tracks=[seed_id], limit=10)
    uris = [t.get("uri") for t in recs.get("tracks", []) if t.get("uri")]
    if not uris:
        return {"error": "no recommendations found"}
    sp.start_playback(uris=uris)
    return {"status": "started radio", "seed": song_uri, "played": uris[:3]}


@_with_client
def play_next_track(sp: spotipy.Spotify):
    sp.next_track()
    return {"status": "skipped"}


@_with_client
def resume_playback(sp: spotipy.Spotify):
    sp.start_playback()
    return {"status": "resumed"}


@_with_client
def pause_playback(sp: spotipy.Spotify):
    sp.pause_playback()
    return {"status": "paused"}


@_with_client
def previous_track(sp: spotipy.Spotify):
    sp.previous_track()
    return {"status": "previous"}


@_with_client
def set_volume(sp: spotipy.Spotify, level: int):
    sp.volume(level)
    return {"status": "volume set", "level": level}


@_with_client
def search_tracks(sp: spotipy.Spotify, query: str, limit: int = 10) -> List[Dict[str, Any]]:
    result = sp.search(q=query, type="track", limit=limit)
    items = result.get("tracks", {}).get("items", []) or []
    return [
        {"name": t.get("name"), "artists": [a.get("name") for a in t.get("artists", [])], "uri": t.get("uri"), "id": t.get("id")}
        for t in items
    ]


@_with_client
def get_recommendations(
    sp: spotipy.Spotify,
    seed_tracks: Optional[List[str]] = None,
    seed_artists: Optional[List[str]] = None,
    seed_genres: Optional[List[str]] = None,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    kwargs: Dict[str, Any] = {"limit": limit}
    if seed_tracks:
        kwargs["seed_tracks"] = [t.split(":")[-1] for t in seed_tracks]
    if seed_artists:
        kwargs["seed_artists"] = [a.split(":")[-1] for a in seed_artists]
    if seed_genres:
        kwargs["seed_genres"] = seed_genres
    recs = sp.recommendations(**kwargs)
    tracks = recs.get("tracks", []) or []
    return [
        {"name": t.get("name"), "artists": [a.get("name") for a in t.get("artists", [])], "uri": t.get("uri"), "id": t.get("id")}
        for t in tracks
    ]


@_with_client
def create_playlist(sp: spotipy.Spotify, name: str, description: str = "", public: bool = False):
    user = sp.current_user()
    playlist = sp.user_playlist_create(
        user=user["id"], name=name, public=public, description=description
    )
    return {"id": playlist.get("id"), "name": playlist.get("name"), "url": playlist.get("external_urls", {}).get("spotify")}


@_with_client
def add_tracks_to_playlist(sp: spotipy.Spotify, playlist_id: str, uris: List[str]):
    sp.playlist_add_items(playlist_id, uris)
    return {"status": "added", "playlist_id": playlist_id, "uris": uris}


@_with_client
def get_user_playlists(sp: spotipy.Spotify, limit: int = 20) -> List[Dict[str, Any]]:
    playlists = sp.current_user_playlists(limit=limit)
    items = playlists.get("items", []) or []
    return [
        {"name": p.get("name"), "id": p.get("id"), "uri": p.get("uri"), "tracks": p.get("tracks", {}).get("total")}
        for p in items
    ]


@_with_client
def get_playlist_tracks(sp: spotipy.Spotify, playlist_id: str) -> List[Dict[str, Any]]:
    results = sp.playlist_tracks(playlist_id)
    return [
        {
            "name": item.get("track", {}).get("name"),
            "artists": [a.get("name") for a in (item.get("track", {}).get("artists") or [])],
            "uri": item.get("track", {}).get("uri"),
            "id": item.get("track", {}).get("id"),
        }
        for item in results.get("items", [])
        if item.get("track")
    ]


@_with_client
def get_user_profile(sp: spotipy.Spotify):
    return sp.current_user()