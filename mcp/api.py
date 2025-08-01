from fastapi import FastAPI, Query
from tools import thepusherrr, spotify

app = FastAPI(title="MCP API", description="Multi-Control Panel API", version="1.0.0")

@app.get("/", summary="Root")
def root():
    """Health check endpoint."""
    return {"status": "MCP API is running"}

@app.get("/notify", summary="Send Notification", description="Send a push notification message to a Pushover-connected device.")
def notify(msg: str = Query("hello world", description="Message to send via Pushover")):
    """Send a push notification using Pushover."""
    result = thepusherrr.send_notification("MCP Notification", msg)
    return {"message_sent": msg, "result": result}

@app.get("/song", summary="Get Current Song", description="Retrieve the currently playing song on Spotify along with the artist name.")
def current_song():
    """Retrieve the currently playing Spotify song."""
    song, artist = spotify.get_current_song()
    if song and artist:
        return {"song": song, "artist": artist}
    return {"message": "No song currently playing"}

from fastapi.openapi.utils import get_openapi

@app.get("/play", summary="Play a Spotify playlist", description="Start playback from a given Spotify playlist URI.")
def play(playlist: str = Query(..., description="Spotify playlist URI (e.g., spotify:playlist:37i9dQZF1DXcBWIGoYBM5M)")):
    return spotify.play_playlist(playlist)

@app.get("/play_song_radio", summary="Play radio for a specific song", description="Start Spotify radio based on a given song URI.")
def play_song_radio(song: str = Query(..., description="Spotify song URI (e.g., spotify:track:3n3Ppam7vgaVa1iaRUc9Lp)")):
    return spotify.play_song_radio(song)

@app.get("/next", summary="Skip to next track", description="Advance playback to the next track in the current queue.")
def next_track():
    return spotify.play_next_track()

@app.get("/play_track", summary="Play a specific track", description="Start playback of a specific Spotify track URI.")
def play_track(track: str = Query(..., description="Spotify track URI (e.g., spotify:track:3n3Ppam7vgaVa1iaRUc9Lp)")):
    return spotify.play_track(track)

@app.get("/resume", summary="Resume Spotify playback", description="Resume Spotify playback if paused.")
def resume():
    return spotify.resume_playback()

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
        {"url": "https://9fbd00630987.ngrok-free.app"}  # 👈 Add your ngrok URL here
    ]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi