"""
Anti-doublon persistant.
Utilise SQLite pour tracker les événements traités.
NOTE: Sur Railway, /tmp est éphémère. Pour un anti-doublon parfait,
il faudrait stocker dans Google Sheets ou Redis.
"""
import sqlite3
import time
import os
import threading
from config import SQLITE_DB_PATH, MEMORY_DIR


_lock = threading.Lock()


def _ensure_db():
    """Crée la base et la table si nécessaire."""
    os.makedirs(MEMORY_DIR, exist_ok=True)
    with _lock:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS processed_events (
                event_key TEXT PRIMARY KEY,
                processed_at REAL
            )
        """)
        # Nettoyer les entrées de plus de 24h
        conn.execute(
            "DELETE FROM processed_events WHERE processed_at < ?",
            (time.time() - 86400,)
        )
        conn.commit()
        conn.close()


def is_duplicate(event_key: str) -> bool:
    """Vérifie si un événement a déjà été traité."""
    _ensure_db()
    with _lock:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.execute(
            "SELECT 1 FROM processed_events WHERE event_key = ?",
            (event_key,)
        )
        exists = cursor.fetchone() is not None
        if not exists:
            conn.execute(
                "INSERT INTO processed_events (event_key, processed_at) VALUES (?, ?)",
                (event_key, time.time())
            )
            conn.commit()
        conn.close()
    return exists


def mark_processed(event_key: str):
    """Marque un événement comme traité."""
    _ensure_db()
    with _lock:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        conn.execute(
            "INSERT OR REPLACE INTO processed_events (event_key, processed_at) VALUES (?, ?)",
            (event_key, time.time())
        )
        conn.commit()
        conn.close()
