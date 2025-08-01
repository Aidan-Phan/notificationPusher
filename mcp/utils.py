import os
import logging
from datetime import datetime
from typing import Optional
import sqlite3
import threading

# file fallback
LOG_FILE = os.path.join(os.getcwd(), "activity.log")
file_logger = logging.getLogger("mcp_activity_file")
file_logger.setLevel(logging.INFO)
if not file_logger.handlers:
    fh = logging.FileHandler(LOG_FILE)
    formatter = logging.Formatter(
        "%(asctime)s | user=%(user)s | action=%(action)s | details=%(details)s"
    )
    fh.setFormatter(formatter)
    file_logger.addHandler(fh)

# --- Identity helpers ---
def identify_user(api_key: Optional[str], known_owner_key: str) -> str:
    if api_key and known_owner_key and api_key.strip() == known_owner_key.strip():
        return "Aidan"
    if api_key:
        return f"User({api_key[:6]})"
    return "Anonymous"

# --- In-memory state ---
STATE: dict[str, dict] = {}

def get_user_state(user: str) -> dict:
    if user not in STATE:
        STATE[user] = {"queue": [], "last_played": None, "online": False}
    return STATE[user]

def add_to_queue(user: str, track_uri: str, track_name: str, requester: str):
    st = get_user_state(user)
    st["queue"].append(
        {
            "uri": track_uri,
            "name": track_name,
            "requested_by": requester,
            "added_at": datetime.utcnow().isoformat(),
        }
    )

def set_last_played(user: str, track_name: str):
    st = get_user_state(user)
    st["last_played"] = {"track": track_name, "timestamp": datetime.utcnow().isoformat()}

def set_online(user: str, online: bool):
    st = get_user_state(user)
    st["online"] = online

# --- SQLite logging backend ---
DB_PATH = os.path.join(os.getcwd(), "activity_logs.db")
_DB_LOCK = threading.Lock()

def _ensure_table():
    with _DB_LOCK:
        conn = sqlite3.connect(DB_PATH)
        try:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS activity_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    user TEXT,
                    action TEXT,
                    details TEXT,
                    origin_ip TEXT,
                    request_headers TEXT,
                    extra TEXT
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

# ensure table exists at import
_ensure_table()

def log_to_sqlite(
    user: str,
    action: str,
    details: str = "",
    origin_ip: Optional[str] = None,
    headers: Optional[dict] = None,
    extra: Optional[dict] = None,
):
    timestamp = datetime.utcnow().isoformat()
    with _DB_LOCK:
        conn = sqlite3.connect(DB_PATH)
        try:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO activity_logs
                  (timestamp, user, action, details, origin_ip, request_headers, extra)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    timestamp,
                    user,
                    action,
                    details,
                    origin_ip or "",
                    str(headers or {}),
                    str(extra or {}),
                ),
            )
            conn.commit()
        finally:
            conn.close()

def log_action(user: str, action: str, details: str, origin_ip: Optional[str] = None, headers: Optional[dict] = None, extra: Optional[dict] = None):
    # file fallback (for local readable)
    file_logger.info("", extra={"user": user, "action": action, "details": details})
    # sqlite persistence
    try:
        log_to_sqlite(user, action, details, origin_ip=origin_ip, headers=headers, extra=extra)
    except Exception:
        pass  # swallow errors so logging never breaks main flow