import os
import sqlite3
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, Query, Header, HTTPException
from fastapi.responses import PlainTextResponse
from fastapi.openapi.utils import get_openapi

from mcp.tools import thepusherrr, spotify
from mcp.config import (
    SPOTIFY_CLIENT_ID,
    SPOTIFY_CLIENT_SECRET,
    SPOTIFY_REDIRECT_URI,
)
from mcp.utils import get_user_state, add_to_queue, set_last_played, set_online

# --- Logging / identity setup ------------------------------------------------
DB_PATH = os.getenv("LOG_DB_PATH", "actions.db")
AIDAN_API_KEY = os.environ.get("AIDAN_API_KEY", "")

def _init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS action_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            actor TEXT,
            endpoint TEXT,
            params TEXT,
            result TEXT
        )
        """
    )
    conn.commit()
    return conn

_db_conn = _init_db()

def log_action(actor: str, endpoint: str, params: str, result: str):
    try:
        c = _db_conn.cursor()
        c.execute(
            "INSERT INTO action_log (timestamp, actor, endpoint, params, result) VALUES (?, ?, ?, ?, ?)",
            (datetime.utcnow().isoformat(), actor, endpoint, params, result),
        )
        _db_conn.commit()
    except Exception:
        pass

def identify_actor(api_key: Optional[str]) -> str:
    if api_key and api_key == AIDAN_API_KEY:
        return "Aidan"
    return "other"

app = FastAPI(
    title="MCP (Multi-Control Panel) API",
    description="An interface to control Spotify and send notifications. You can play playlists, tracks, start radios, resume/skip, get current song, and push custom messages.",
    version="1.0.0",
)

# Basic health checks
@app.head("/", include_in_schema=False)
def head_root():
    return PlainTextResponse("", status_code=200)

@app.get("/", summary="Root")
def root(x_api_key: Optional[str] = Header(default=None)):
    actor = identify_actor(x_api_key)
    log_action(actor, "health_check", "", "root endpoint hit")
    return {"status": "MCP API is running"}

# Notification
@app.get("/notify", summary="Send Notification")
def notify(
    msg: str = Query("hello world", description="Message to send via Pushover"),
    x_api_key: Optional[str] = Header(default=None),
):
    actor = identify_actor(x_api_key)
    result = thepusherrr.send_notification("MCP Notification", msg)
    log_action(actor, "notify", msg, str(result))
    return {"message_sent": msg, "result": result}

# Spotify auth flow
@app.get("/auth/start")
def auth_start(x_api_key: Optional[str] = Header(default=None)):
    actor = identify_actor(x_api_key)
    if actor != "Aidan":
        raise HTTPException(status_code=403, detail="only Aidan can initiate auth")
    if not (SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET and SPOTIFY_REDIRECT_URI):
        raise HTTPException(status_code=500, detail="Spotify config missing")
    return {"auth_url": spotify.get_auth_url()}

@app.get("/auth/callback")
def auth_callback(code: str, x_api_key: Optional[str] = Header(default=None)):
    actor = identify_actor(x_api_key)
    if actor != "Aidan":
        raise HTTPException(status_code=403, detail="forbidden")
    token_info = spotify.handle_callback(code)
    log_action(actor, "auth_callback", code, str(token_info))
    return {"status": "authenticated", "expires_in": token_info.get("expires_in")}

# Playback endpoints (examples: song, play, next, etc.)
@app.get("/song", summary="Get Current Song")
def current_song(x_api_key: Optional[str] = Header(default=None)):
    actor = identify_actor(x_api_key)
    try:
        song, artist = spotify.get_current_song()
    except Exception as e:
        log_action(actor, "current_song", "", str(e))
        raise HTTPException(status_code=500, detail=f"spotify error: {e}")
    log_action(actor, "current_song", "", f"{song} - {artist}")
    if song and artist:
        if actor == "Aidan":
            set_last_played("Aidan", song)
            set_online("Aidan", True)
        return {"song": song, "artist": artist}
    return {"message": "No song currently playing"}

# Example of owner vs other logic for playing a playlist
@app.get("/play", summary="Play a Spotify playlist")
def play(playlist: str = Query(...), x_api_key: Optional[str] = Header(default=None)):
    actor = identify_actor(x_api_key)
    if actor != "Aidan":
        add_to_queue("Aidan", playlist, "playlist", actor)
        state = get_user_state("Aidan")
        log_action(actor, "play_playlist", playlist, f"Added to Aidan's queue: {state['queue']}")
        return {
            "message": f"{actor} requested playlist. Added to Aidan's queue.",
            "queue_length": len(state["queue"]),
            "queue": state["queue"],
        }
    try:
        result = spotify.play_playlist(playlist)
        log_action(actor, "play_playlist", playlist, str(result))
        return result
    except Exception as e:
        log_action(actor, "play_playlist", playlist, str(e))
        raise HTTPException(status_code=500, detail=f"spotify error: {e}")

# (Other Spotify endpoints would follow the same pattern...)
# Skipping rewriting all for brevity; keep your existing handlers for next/track/search/etc.

@app.get("/logs", summary="Fetch recent logs")
def fetch_logs(limit: int = Query(50, le=200), x_api_key: Optional[str] = Header(default=None)):
    actor = identify_actor(x_api_key)
    if actor != "Aidan":
        raise HTTPException(status_code=403, detail="forbidden")
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            "SELECT timestamp, actor, endpoint, params, result FROM action_log ORDER BY id DESC LIMIT ?", (limit,)
        )
        rows = [dict(r) for r in cur.fetchall()]
        return {"logs": rows}
    except Exception as e:
        return {"error": str(e)}
    finally:
        try:
            conn.close()
        except Exception:
            pass

# OpenAPI customization
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
    openapi_schema["servers"] = [{"url": "https://notificationspotifymcp.onrender.com"}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi