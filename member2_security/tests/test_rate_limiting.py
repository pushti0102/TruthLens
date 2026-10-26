"""
Unit and Integration Tests for Rate-Limiting Module
Member 2: Cryptography & Information Security
"""

import time
from unittest.mock import MagicMock

import pytest
from fastapi import Depends, FastAPI, Request
from fastapi.testclient import TestClient

from member2_security.security.rate_limiting import (
    RateLimitDependency,
    RateLimitExceeded,
    SlidingWindowRateLimiter,
    extract_client_identifier,
    parse_rate_string,
)


class TestRateStringParsing:
    """Tests parsing of rate strings like '10/minute', '5/second'."""

    def test_parse_valid_rate_strings(self):
        assert parse_rate_string("10/minute") == (10, 60)
        assert parse_rate_string("5/second") == (5, 1)
        assert parse_rate_string("100/hour") == (100, 3600)
        assert parse_rate_string("1000/day") == (1000, 86400)

    def test_parse_invalid_rate_strings(self):
        with pytest.raises(ValueError):
            parse_rate_string("unlimited")
        with pytest.raises(ValueError):
            parse_rate_string("10/decade")


class TestSlidingWindowRateLimiter:
    """Tests for the sliding window counter algorithm."""

    def test_limiter_allows_under_threshold(self):
        limiter = SlidingWindowRateLimiter()
        # Limit: 3 requests per 10 seconds
        for i in range(3):
            allowed, remaining, retry_after = limiter.is_allowed("client-1", "test", limit=3, window_seconds=10)
            assert allowed is True
            assert retry_after == 0

    def test_limiter_blocks_above_threshold(self):
        limiter = SlidingWindowRateLimiter()
        # 2 requests allowed
        limiter.is_allowed("client-1", "test", limit=2, window_seconds=10)
        limiter.is_allowed("client-1", "test", limit=2, window_seconds=10)

        # 3rd request should be blocked
        allowed, remaining, retry_after = limiter.is_allowed("client-1", "test", limit=2, window_seconds=10)
        assert allowed is False
        assert remaining == 0
        assert retry_after > 0

    def test_user_isolation(self):
        """User A exhausting quota must not affect User B."""
        limiter = SlidingWindowRateLimiter()
        # Exhaust user-A
        for _ in range(2):
            limiter.is_allowed("user:A", "test", limit=2, window_seconds=60)

        # User A is blocked
        allowed_a, _, _ = limiter.is_allowed("user:A", "test", limit=2, window_seconds=60)
        assert allowed_a is False

        # User B is NOT blocked
        allowed_b, _, _ = limiter.is_allowed("user:B", "test", limit=2, window_seconds=60)
        assert allowed_b is True

    def test_sliding_window_expiration(self):
        """Requests must be permitted again after window expires."""
        limiter = SlidingWindowRateLimiter()
        t0 = 1000.0

        # Record 2 requests at t0
        limiter.is_allowed("client-1", "test", limit=2, window_seconds=5, now=t0)
        limiter.is_allowed("client-1", "test", limit=2, window_seconds=5, now=t0 + 1)

        # Blocked at t0 + 2
        allowed_blocked, _, _ = limiter.is_allowed("client-1", "test", limit=2, window_seconds=5, now=t0 + 2)
        assert allowed_blocked is False

        # Permitted again at t0 + 6 (window elapsed)
        allowed_reset, _, _ = limiter.is_allowed("client-1", "test", limit=2, window_seconds=5, now=t0 + 6)
        assert allowed_reset is True


class TestFastAPIRateLimitingIntegration:
    """Integration tests using FastAPI TestClient with rate-limiting dependency."""

    @pytest.fixture
    def test_app(self):
        app = FastAPI()
        limiter = SlidingWindowRateLimiter()

        @app.get("/api/verify", dependencies=[Depends(RateLimitDependency("2/minute", tag="test_verify", limiter=limiter))])
        def verify_route():
            return {"status": "ok"}

        return app

    def test_fastapi_rate_limit_enforced_429(self, test_app):
        client = TestClient(test_app)

        # First request -> 200 OK
        resp1 = client.get("/api/verify", headers={"X-User-ID": "tester1"})
        assert resp1.status_code == 200
        assert resp1.headers["X-RateLimit-Limit"] == "2"
        assert resp1.headers["X-RateLimit-Remaining"] == "1"

        # Second request -> 200 OK
        resp2 = client.get("/api/verify", headers={"X-User-ID": "tester1"})
        assert resp2.status_code == 200
        assert resp2.headers["X-RateLimit-Remaining"] == "0"

        # Third request -> 429 Too Many Requests
        resp3 = client.get("/api/verify", headers={"X-User-ID": "tester1"})
        assert resp3.status_code == 429
        assert "Retry-After" in resp3.headers
        data = resp3.json()
        assert data["detail"]["error_code"] == "RATE_LIMIT_EXCEEDED"
        assert data["detail"]["retry_after_seconds"] > 0

        # Different user -> 200 OK (isolated)
        resp_user2 = client.get("/api/verify", headers={"X-User-ID": "tester2"})
        assert resp_user2.status_code == 200
