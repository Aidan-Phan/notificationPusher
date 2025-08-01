import os
from fastapi import FastAPI, Query
from fastapi.responses import PlainTextResponse
from fastapi.openapi.utils import get_openapi
from spotipy.oauth2 import SpotifyOAuth
from typing import Optional

from mcp.tools import thepusherrr, spotify
from mcp.config import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_URI, validate as validate_spotify_config

# validate Spotify config on startup so /auth/start fails with a clear error if something is missing
try:
    validate_spotify_config()
except Exception as e:
    print("Spotify config validation error:", e)
    raise

app = FastAPI(
    title="MCP (Multi-Control Panel) API",
    description="An interface to control Spotify and send notifications. You can play playlists, tracks, start radios, resume/skip, get current song, and push custom messages.",
    version="1.0.0",
)





@app.get("/auth/start", summary="Start Spotify OAuth", description="Begin Spotify authorization; returns a URL to visit.")
def auth_start():
    auth_manager = SpotifyOAuth(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri=SPOTIFY_REDIRECT_URI,
        scope="user-read-playback-state user-modify-playback-state playlist-read-private playlist-modify-private playlist-modify-public user-read-private",
        cache_path=os.path.join(os.getcwd(), "mcp_spotify_token_cache"),
        show_dialog=True,
    )
    # Fail fast if config missing to give clearer error
    try:
        validate_spotify_config()
    except Exception as e:
        # This will show up in logs if config is incomplete
        print("Spotify config validation error:", e)
    auth_url = auth_manager.get_authorize_url()
    return {"auth_url": auth_url}

@app.get("/auth/callback", summary="Spotify OAuth callback", description="Callback endpoint Spotify redirects to after user authorizes.")
def auth_callback(code: str):
    auth_manager = SpotifyOAuth(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri=SPOTIFY_REDIRECT_URI,
        scope="user-read-playback-state user-modify-playback-state playlist-read-private playlist-modify-private playlist-modify-public user-read-private",
        cache_path=os.path.join(os.getcwd(), "mcp_spotify_token_cache"),
        show_dialog=False,
    )
    token_info = auth_manager.get_access_token(code, as_dict=True)
    return {"status": "authenticated", "token_info": token_info}


@app.get("/auth/callback", summary="Spotify OAuth callback", description="Callback endpoint Spotify redirects to after user authorizes.")
def auth_callback(code: str):
    auth_manager = SpotifyOAuth(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri=SPOTIFY_REDIRECT_URI,
        scope="user-read-playback-state user-modify-playback-state playlist-read-private playlist-modify-private playlist-modify-public user-read-private",
        cache_path=os.path.join(os.getcwd(), "mcp_spotify_token_cache"),
        show_dialog=False,
    )
    # This will exchange the code and cache tokens for subsequent calls
    token_info = auth_manager.get_access_token(code, as_dict=True)
    return {"status": "authenticated", "token_info": token_info}

@app.head("/", include_in_schema=False)
def head_root():
    return PlainTextResponse("", status_code=200)

@app.get("/", summary="Root")
def root():
    """Health check endpoint."""
    return {"status": "MCP API is running"}

@app.get("/notify", summary="Send Notification", description="Send a push notification message to a Pushover-registered device.")
def notify(msg: str = Query("hello world", description="Message to send via Pushover")):
    result = thepusherrr.send_notification("MCP Notification", msg)
    return {"message_sent": msg, "result": result}

@app.get("/song", summary="Get Current Song", description="Retrieve the currently playing Spotify song.")
def current_song():
    song, artist = spotify.get_current_song()
    if song and artist:
        return {"song": song, "artist": artist}
    return {"message": "No song currently playing"}

@app.get("/play", summary="Play a Spotify playlist", description="Start playback from a given Spotify playlist URI.")
def play(playlist: str = Query(..., description="Spotify playlist URI (e.g., spotify:playlist:37i9dQZF1DXcBWIGoYBM5M)")):
    return spotify.play_playlist(playlist)

@app.get("/play_song_radio", summary="Play radio for a specific song", description="Start Spotify radio based on a given song URI.")
def play_song_radio(song: str = Query(..., description="Spotify song URI (e.g., spotify:track:3n3Ppam7vgaVa1iaRUc9Lp)")):
    return spotify.play_song_radio(song)

@app.get("/next", summary="Skip to next track", description="Advance playback to the next track in the current queue.")
def next_track():
    return spotify.next_track()

@app.get("/play_track", summary="Play a specific track", description="Start playback of a specific Spotify track URI.")
def play_track(track: str = Query(..., description="Spotify track URI (e.g., spotify:track:3n3Ppam7vgaVa1iaRUc9Lp)")):
    return spotify.play_track(track)

@app.get("/resume", summary="Resume Spotify playback", description="Resume Spotify playback if paused.")
def resume():
    return spotify.resume_playback()


# === New endpoints for advanced Spotify control ===
def search(query: str = Query(..., description="Search query string (e.g., 'lofi beats')")):
    tracks = spotify.search_tracks(query) or []
    return {
        "tracks": [
            {
                "name": t.get("name"),
                "artists": [a.get("name") for a in t.get("artists", [])],
                "uri": t.get("uri"),
            }
            for t in tracks
        ]
    }

@app.get("/recommend", summary="Get Recommendations", description="Get recommended tracks based on seed tracks, artists, or genres. Provide comma-separated lists.")
def recommend(seed_tracks: Optional[str] = Query(None, description="Comma-separated seed track URIs"),
              seed_artists: Optional[str] = Query(None, description="Comma-separated seed artist URIs"),
              seed_genres: Optional[str] = Query(None, description="Comma-separated seed genres"),
              limit: int = Query(10, description="Number of recommendations to return")):
    tracks = spotify.get_recommendations(
        seed_tracks=seed_tracks.split(",") if seed_tracks else None,
        seed_artists=seed_artists.split(",") if seed_artists else None,
        seed_genres=seed_genres.split(",") if seed_genres else None,
        limit=limit,
    )
    return {"recommendations": [{"name": t.get('name'), "artists": [a.get('name') for a in t.get('artists', [])], "uri": t.get('uri')} for t in tracks]}

@app.get("/create_playlist", summary="Create Playlist", description="Create a new Spotify playlist.")
def create_playlist(name: str = Query(..., description="Playlist name"),
                    description: str = Query("", description="Playlist description"),
                    public: bool = Query(False, description="Whether the playlist is public")):
    playlist = spotify.create_playlist(name, description=description, public=public)
    return playlist or {"error": "failed to create playlist"}

@app.get("/add_to_playlist", summary="Add Tracks to Playlist", description="Add track URIs to an existing playlist. Provide comma-separated track URIs.")
def add_to_playlist(playlist_id: str = Query(..., description="Target playlist ID"),
                    track_uris: str = Query(..., description="Comma-separated Spotify track URIs")):
    uris = [u.strip() for u in track_uris.split(",") if u.strip()]
    result = spotify.add_tracks_to_playlist(playlist_id, uris)
    return result or {"error": "failed to add tracks"}

@app.get("/pause", summary="Pause Playback", description="Pause current Spotify playback.")
def pause():
    return spotify.pause_playback()

@app.get("/previous", summary="Previous Track", description="Go to previous track.")
def previous():
    return spotify.previous_track()

@app.get("/volume", summary="Set Volume", description="Set Spotify playback volume (0-100).")
def volume(level: int = Query(..., ge=0, le=100, description="Volume percent")):
    return spotify.set_volume(level)

@app.get("/me", summary="Get User Profile", description="Retrieve the current Spotify user profile.")
def me():
    return spotify.get_user_profile()

@app.get("/playlists", summary="List User Playlists", description="Retrieve the current user's playlists.")
def playlists(limit: int = Query(20, description="Max number of playlists to fetch")):
    return {"playlists": spotify.get_user_playlists(limit=limit)}

@app.get("/playlist_tracks", summary="Get Playlist Tracks", description="Retrieve all tracks in a playlist.")
def playlist_tracks(playlist_id: str = Query(..., description="Spotify playlist ID")):
    return {"tracks": spotify.get_playlist_tracks(playlist_id)}

# === OpenAPI customization ===
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="MCP (Multi-Control Panel) API",
        version="1.0.0",
        description="""
An interface for controlling Spotify and sending notifications.

You can:
- Play playlists, tracks, or song-based radio
- Resume or skip playback
- Retrieve the current playing song
- Push custom messages to a Pushover-connected device
""",
        routes=app.routes,
    )
    openapi_schema["servers"] = [
        {"url": "https://notificationspotifymcp.onrender.com"}  # <- replace with your actual Render URL
    ]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi