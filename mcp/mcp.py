# mcp.py
from tools import thepusherrr as pushover
from tools import spotify
import schedule
from tools.scheduler import run_scheduled_tasks
import threading

# === Demo Task ===

def notify_hello():
    pushover.send_notification("MCP Test", "hello world")

def play_music():
    spotify.play_playlist("spotify:playlist:YOUR_PLAYLIST_URI")

def alert_on_specific_song():
    song, artist = spotify.get_current_song()
    if song == "YOUR_SONG_NAME":
        pushover.send_notification("🎵 Now Playing", f"{song} by {artist}")

# === Schedule ===

schedule.every().day.at("09:00").do(play_music)
schedule.every(30).seconds.do(alert_on_specific_song)

# Optional manual test
notify_hello()

# Start scheduler in separate thread
threading.Thread(target=run_scheduled_tasks).start()