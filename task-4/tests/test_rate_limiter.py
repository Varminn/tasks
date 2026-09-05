import os
import tempfile
import time

import pytest

from llm_router.rate_limiter import RateLimiter


@pytest.fixture
def db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    yield path
    os.unlink(path)


class TestRateLimiter:
    def test_allows_within_limit(self, db_path):
        limiter = RateLimiter(db_path, max_tokens_per_window=1000, window_seconds=60)
        allowed, used, remaining = limiter.check_and_record("key1", 500)
        assert allowed is True
        assert used == 500
        assert remaining == 500

    def test_rejects_over_limit(self, db_path):
        limiter = RateLimiter(db_path, max_tokens_per_window=1000, window_seconds=60)
        limiter.check_and_record("key1", 600)
        allowed, used, remaining = limiter.check_and_record("key1", 500)
        assert allowed is False
        assert used == 600
        assert remaining == 400

    def test_exact_limit_boundary(self, db_path):
        limiter = RateLimiter(db_path, max_tokens_per_window=1000, window_seconds=60)
        limiter.check_and_record("key1", 999)
        allowed, _, _ = limiter.check_and_record("key1", 1)
        assert allowed is True

    def test_independent_keys(self, db_path):
        limiter = RateLimiter(db_path, max_tokens_per_window=1000, window_seconds=60)
        limiter.check_and_record("key1", 1000)
        allowed, _, _ = limiter.check_and_record("key2", 500)
        assert allowed is True

    def test_sliding_window_expiry(self, db_path):
        limiter = RateLimiter(db_path, max_tokens_per_window=1000, window_seconds=2)
        limiter._conn.execute(
            "INSERT INTO token_usage (api_key, timestamp, tokens) VALUES (?, ?, ?)",
            ("key1", time.time() - 3, 1000),
        )
        limiter._conn.commit()
        allowed, _, _ = limiter.check_and_record("key1", 500)
        assert allowed is True

    def test_evict_expired(self, db_path):
        limiter = RateLimiter(db_path, max_tokens_per_window=1000, window_seconds=60)
        limiter._conn.execute(
            "INSERT INTO token_usage (api_key, timestamp, tokens) VALUES (?, ?, ?)",
            ("key1", time.time() - 120, 100),
        )
        limiter._conn.commit()
        deleted = limiter.evict_expired()
        assert deleted >= 1

    def test_get_usage(self, db_path):
        limiter = RateLimiter(db_path, max_tokens_per_window=1000, window_seconds=60)
        limiter.check_and_record("key1", 300)
        assert limiter.get_usage("key1") == 300

    def test_on_disk_sqlite(self, db_path):
        limiter1 = RateLimiter(db_path, max_tokens_per_window=1000, window_seconds=60)
        limiter1.check_and_record("key1", 500)
        limiter2 = RateLimiter(db_path, max_tokens_per_window=1000, window_seconds=60)
        assert limiter2.get_usage("key1") == 500
