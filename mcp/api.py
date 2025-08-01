import os
import sqlite3
from typing import Optional
from fastapi import FastAPI, Query, Header, HTTPException
from fastapi.responses import PlainTextResponse
from fastapi.openapi.utils import get_openapi
from fastapi import Request
from mcp.tools import thepusherrr, spotify
from mcp.config import (
    SPOTIFY_CLIENT_ID,
    SPOTIFY_CLIENT_SECRET,
    SPOTIFY_REDIRECT_URI,
    AIDAN_API_KEY,
)
from mcp.utils import identify_user, log_action, get_user_state, add_to_queue, set_last_played, set_online


app = FastAPI(
    title="MCP (Multi-Control Panel) API",
    description="An interface to control Spotify and send notifications. You can play playlists, tracks, start radios, resume/skip, get current song, and push custom messages.",
    version="1.0.0",
)


@app.head("/", include_in_schema=False)
def head_root():
    return PlainTextResponse("", status_code=200)


@app.get("/", summary="Root")
def root(x_api_key: Optional[str] = Header(default=None)):
    user = identify_user(x_api_key, AIDAN_API_KEY)
    log_action(user, "health_check", "root endpoint hit")
    return {"status": "MCP API is running"}


@app.get("/notify", summary="Send Notification", description="Send a push notification message to a Pushover-registered device.")
def notify(msg: str = Query("hello world", description="Message to send via Pushover"), x_api_key: Optional[str] = Header(default=None)):
    user = identify_user(x_api_key, AIDAN_API_KEY)
    log_action(user, "notify", msg)
    result = thepusherrr.send_notification("MCP Notification", msg)
    return {"message_sent": msg, "result": result}

@app.get("/auth/start", summary="Begin Spotify OAuth")
def auth_start(x_api_key: Optional[str] = Header(default=None)):
    user = identify_user(x_api_key, AIDAN_API_KEY)
    if user != "Aidan":
        return {"error": "only Aidan can initiate auth"}
    url = spotify.get_auth_url()
    return {"auth_url": url}

@app.get("/auth/callback", summary="Handle Spotify OAuth callback")
def auth_callback(code: str, x_api_key: Optional[str] = Header(default=None)):
    user = identify_user(x_api_key, AIDAN_API_KEY)
    if user != "Aidan":
        raise HTTPException(status_code=403, detail="forbidden")
    token_info = spotify.handle_callback(code)
    # you can return minimal safe info; the cache file now contains refresh token
    return {"status": "authenticated", "expires_in": token_info.get("expires_in")}

@app.get("/song", summary="Get Current Song", description="Retrieve the currently playing Spotify song.")
def current_song(x_api_key: Optional[str] = Header(default=None)):
    user = identify_user(x_api_key, AIDAN_API_KEY)
    song, artist = spotify.get_current_song()
    log_action(user, "current_song", f"{song} - {artist}")
    if song and artist:
        # update state for owner
        if user == "Aidan":
            set_last_played("Aidan", song)
            set_online("Aidan", True)
        return {"song": song, "artist": artist}
    return {"message": "No song currently playing"}


@app.get("/play", summary="Play a Spotify playlist", description="Start playback from a given Spotify playlist URI.")
def play(playlist: str = Query(...), x_api_key: Optional[str] = Header(default=None)):
    user = identify_user(x_api_key, AIDAN_API_KEY)
    log_action(user, "play_playlist", playlist)
    if user != "Aidan":
        # add to queue instead of immediate play
        add_to_queue("Aidan", playlist, "playlist", user)
        state = get_user_state("Aidan")
        return {
            "message": f"{user} requested playlist. Added to Aidan's queue.",
            "queue_length": len(state["queue"]),
            "queue": state["queue"],
        }
    return spotify.play_playlist(playlist)


@app.get("/play_song_radio", summary="Play radio for a specific song", description="Start Spotify radio based on a given song URI.")
def play_song_radio(song: str = Query(...), x_api_key: Optional[str] = Header(default=None)):
    user = identify_user(x_api_key, AIDAN_API_KEY)
    log_action(user, "play_song_radio", song)
    if user != "Aidan":
        add_to_queue("Aidan", song, "radio_seed", user)
        state = get_user_state("Aidan")
        return {
            "message": f"{user} requested radio. Added to Aidan's queue.",
            "queue_length": len(state["queue"]),
            "queue": state["queue"],
        }
    return spotify.play_song_radio(song)


@app.get("/next", summary="Skip to next track", description="Advance playback to the next track in the current queue.")
def next_track(x_api_key: Optional[str] = Header(default=None)):
    user = identify_user(x_api_key, AIDAN_API_KEY)
    log_action(user, "next_track", "")
    return spotify.next_track()


@app.get("/play_track", summary="Play a specific track", description="Start playback of a specific Spotify track URI.")
def play_track(track: str = Query(...), x_api_key: Optional[str] = Header(default=None)):
    user = identify_user(x_api_key, AIDAN_API_KEY)
    log_action(user, "play_track", track)
    if user != "Aidan":
        add_to_queue("Aidan", track, "track", user)
        state = get_user_state("Aidan")
        return {
            "message": f"{user} requested track. Added to Aidan's queue.",
            "queue_length": len(state["queue"]),
            "queue": state["queue"],
        }
    return spotify.play_track(track)


@app.get("/resume", summary="Resume Spotify playback", description="Resume Spotify playback if paused.")
def resume(x_api_key: Optional[str] = Header(default=None)):
    user = identify_user(x_api_key, AIDAN_API_KEY)
    log_action(user, "resume_playback", "")
    return spotify.resume_playback()


@app.get("/search", summary="Search Tracks", description="Search Spotify for tracks matching a query.")
def search(query: str = Query(...), x_api_key: Optional[str] = Header(default=None)):
    user = identify_user(x_api_key, AIDAN_API_KEY)
    log_action(user, "search", query)
    tracks = spotify.search_tracks(query)
    if tracks is None:
        return {"tracks": []}
    return {
        "tracks": [
            {"name": t.get("name"), "artists": [a.get("name") for a in t.get("artists", [])], "uri": t.get("uri")}
            for t in tracks
        ]
    }


@app.get("/recommend", summary="Get Recommendations", description="Get recommended tracks based on seed tracks, artists, or genres. Provide comma-separated lists.")
def recommend(
    seed_tracks: Optional[str] = Query(None),
    seed_artists: Optional[str] = Query(None),
    seed_genres: Optional[str] = Query(None),
    limit: int = Query(10),
    x_api_key: Optional[str] = Header(default=None),
):
    user = identify_user(x_api_key, AIDAN_API_KEY)
    log_action(user, "recommend", f"{seed_tracks}|{seed_artists}|{seed_genres}")
    tracks = spotify.get_recommendations(
        seed_tracks=seed_tracks.split(",") if seed_tracks else None,
        seed_artists=seed_artists.split(",") if seed_artists else None,
        seed_genres=seed_genres.split(",") if seed_genres else None,
        limit=limit,
    )
    return {
        "recommendations": [
            {"name": t.get("name"), "artists": [a.get("name") for a in t.get("artists", [])], "uri": t.get("uri")}
            for t in tracks
        ]
    }


@app.get("/create_playlist", summary="Create Playlist", description="Create a new Spotify playlist.")
def create_playlist(name: str = Query(...), description: str = Query(""), public: bool = Query(False), x_api_key: Optional[str] = Header(default=None)):
    user = identify_user(x_api_key, AIDAN_API_KEY)
    log_action(user, "create_playlist", name)
    return spotify.create_playlist(name, description=description, public=public) or {"error": "failed to create playlist"}


@app.get("/add_to_playlist", summary="Add Tracks to Playlist", description="Add track URIs to an existing playlist. Provide comma-separated track URIs.")
def add_to_playlist(playlist_id: str = Query(...), track_uris: str = Query(...), x_api_key: Optional[str] = Header(default=None)):
    user = identify_user(x_api_key, AIDAN_API_KEY)
    uris = [u.strip() for u in track_uris.split(",") if u.strip()]
    log_action(user, "add_to_playlist", f"{playlist_id} <- {uris}")
    result = spotify.add_tracks_to_playlist(playlist_id, uris)
    return result or {"error": "failed to add tracks"}


@app.get("/pause", summary="Pause Playback", description="Pause current Spotify playback.")
def pause(x_api_key: Optional[str] = Header(default=None)):
    user = identify_user(x_api_key, AIDAN_API_KEY)
    log_action(user, "pause_playback", "")
    return spotify.pause_playback()


@app.get("/previous", summary="Previous Track", description="Go to previous track.")
def previous(x_api_key: Optional[str] = Header(default=None)):
    user = identify_user(x_api_key, AIDAN_API_KEY)
    log_action(user, "previous_track", "")
    return spotify.previous_track()


@app.get("/volume", summary="Set Volume", description="Set Spotify playback volume (0-100).")
def volume(level: int = Query(..., ge=0, le=100), x_api_key: Optional[str] = Header(default=None)):
    user = identify_user(x_api_key, AIDAN_API_KEY)
    log_action(user, "set_volume", str(level))
    return spotify.set_volume(level)


@app.get("/me", summary="Get User Profile", description="Retrieve the current Spotify user profile.")
def me(x_api_key: Optional[str] = Header(default=None)):
    user = identify_user(x_api_key, AIDAN_API_KEY)
    log_action(user, "get_profile", "")
    return spotify.get_user_profile()


@app.get("/playlists", summary="List User Playlists", description="Retrieve the current user's playlists.")
def playlists(limit: int = Query(20), x_api_key: Optional[str] = Header(default=None)):
    user = identify_user(x_api_key, AIDAN_API_KEY)
    log_action(user, "list_playlists", "")
    return {"playlists": spotify.get_user_playlists(limit=limit)}


@app.get("/playlist_tracks", summary="Get Playlist Tracks", description="Retrieve all tracks in a playlist.")
def playlist_tracks(playlist_id: str = Query(...), x_api_key: Optional[str] = Header(default=None)):
    user = identify_user(x_api_key, AIDAN_API_KEY)
    log_action(user, "playlist_tracks", playlist_id)
    return {"tracks": spotify.get_playlist_tracks(playlist_id)}

@app.get("/logs", summary="Fetch recent logs")
def fetch_logs(
    limit: int = Query(50, le=200),
    x_api_key: Optional[str] = Header(default=None),
):
    user = identify_user(x_api_key, AIDAN_API_KEY)
    if user != "Aidan":
        raise HTTPException(status_code=403, detail="forbidden")
    db_path = os.path.join(os.getcwd(), "activity_logs.db")
    if not os.path.exists(db_path):
        return {"logs": []}
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM activity_logs ORDER BY timestamp DESC LIMIT ?", (limit,)
        )
        rows = [dict(r) for r in cur.fetchall()]
        return {"logs": rows}
    except Exception as e:
        return {"error": str(e)}
    finally:
        try:
            conn.close()
        except:
            pass

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
        {"url": "https://notificationspotifymcp.onrender.com"}
    ]
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi