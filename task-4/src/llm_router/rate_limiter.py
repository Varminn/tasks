import sqlite3
import time


class RateLimiter:
    """Token-aware sliding window rate limiter backed by on-disk SQLite."""

    def __init__(self, db_path: str, max_tokens_per_window: int = 50_000, window_seconds: int = 60) -> None:
        self._db_path = db_path
        self._max_tokens = max_tokens_per_window
        self._window = window_seconds
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self) -> None:
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS token_usage ("
            "api_key TEXT NOT NULL, timestamp REAL NOT NULL, tokens INTEGER NOT NULL)"
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_usage_key_time ON token_usage(api_key, timestamp)"
        )
        self._conn.commit()

    def check_and_record(self, api_key: str, tokens: int) -> tuple[bool, int, int]:
        now = time.time()
        window_start = now - self._window

        cursor = self._conn.execute(
            "SELECT SUM(tokens) FROM token_usage WHERE api_key = ? AND timestamp >= ?",
            (api_key, window_start),
        )
        used = cursor.fetchone()[0] or 0

        if used + tokens > self._max_tokens:
            return (False, used, self._max_tokens - used)

        self._conn.execute(
            "INSERT INTO token_usage (api_key, timestamp, tokens) VALUES (?, ?, ?)",
            (api_key, now, tokens),
        )
        self._conn.commit()

        return (True, used + tokens, self._max_tokens - used - tokens)

    def evict_expired(self) -> int:
        now = time.time()
        window_start = now - self._window
        cursor = self._conn.execute(
            "DELETE FROM token_usage WHERE timestamp < ?",
            (window_start,),
        )
        self._conn.commit()
        return cursor.rowcount

    def get_usage(self, api_key: str) -> int:
        now = time.time()
        window_start = now - self._window
        cursor = self._conn.execute(
            "SELECT SUM(tokens) FROM token_usage WHERE api_key = ? AND timestamp >= ?",
            (api_key, window_start),
        )
        return cursor.fetchone()[0] or 0
