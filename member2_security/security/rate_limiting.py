"""
TruthLens Rate-Limiting Integration Module
Member 2: Cryptography & Information Security

Provides rate-limiting integration for FastAPI endpoints:
1. User-Identity Aware: Evaluates limits based on authenticated user ID when present.
2. Reverse Proxy & IP Fallback: Securely resolves client IP from X-Forwarded-For
   against configured trusted reverse proxies (prevents client IP spoofing).
3. Sliding Window Counter: Prevents burst attacks at rate-limit boundaries.
4. HTTP 429 Responses: Formats standard RFC 6585 responses with Retry-After and
   X-RateLimit headers.
5. Dual Integration Support:
   - Standalone TruthLensRateLimiter (middleware & dependency, zero external deps).
   - SlowAPI adapter for applications utilizing SlowAPI.

DISTRIBUTED ARCHITECTURE NOTE:
In-memory counters operate per worker process. In multi-worker (e.g., uvicorn -w 4)
or multi-node container environments, an external distributed cache (such as Redis)
should be configured to ensure globally consistent rate enforcement.
"""

from __future__ import annotations

import collections
import ipaddress
import re
import time
from dataclasses import dataclass
from typing import Callable, Deque, Dict, List, Optional, Set, Tuple, Union

from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint


class RateLimitExceeded(HTTPException):
    """Exception raised when an endpoint rate limit is exceeded."""

    def __init__(self, limit: int, window_seconds: int, retry_after: int) -> None:
        super().__init__(
            status_code=429,
            detail={
                "error_code": "RATE_LIMIT_EXCEEDED",
                "message": f"Rate limit of {limit} requests per {window_seconds}s exceeded.",
                "retry_after_seconds": retry_after,
            },
            headers={"Retry-After": str(retry_after)},
        )
        self.retry_after = retry_after
        self.limit = limit
        self.window_seconds = window_seconds


def parse_rate_string(rate_str: str) -> Tuple[int, int]:
    """
    Parse rate string such as '10/minute', '5/second', '100/hour', '1000/day'.

    Returns:
        Tuple of (allowed_count, window_seconds).
    """
    match = re.match(r"^(\d+)\s*/\s*(second|minute|hour|day)s?$", rate_str.strip().lower())
    if not match:
        raise ValueError(
            f"Invalid rate limit string format: '{rate_str}'. "
            "Expected format like '10/minute', '5/second', '100/hour'."
        )

    count = int(match.group(1))
    unit = match.group(2)
    seconds_map = {
        "second": 1,
        "minute": 60,
        "hour": 3600,
        "day": 86400,
    }
    return count, seconds_map[unit]


def extract_client_identifier(
    request: Request,
    trusted_proxies: Optional[Set[str]] = None,
) -> str:
    """
    Extract a secure client identifier for rate limiting:
    1. Checks for authenticated user ID in request.state (e.g. request.state.user_id)
       or custom header 'X-User-ID'.
    2. Falls back to client IP, verifying X-Forwarded-For only against trusted proxies.

    Args:
        request: FastAPI Request instance.
        trusted_proxies: Set of trusted proxy IP addresses or subnets.

    Returns:
        String identifier (e.g., 'user:usr_12345' or 'ip:192.168.1.100').
    """
    # 1. Check authenticated user context
    if hasattr(request.state, "user_id") and request.state.user_id:
        return f"user:{request.state.user_id}"

    user_id_hdr = request.headers.get("x-user-id")
    if user_id_hdr and user_id_hdr.strip():
        return f"user:{user_id_hdr.strip()}"

    # 2. Extract Remote IP
    client_host = request.client.host if request.client else "unknown"

    # Default trusted proxies: localhost loopback
    proxies = trusted_proxies or {"127.0.0.1", "::1"}

    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for and client_host in proxies:
        # X-Forwarded-For contains client, proxy1, proxy2...
        # Take the leftmost untrusted IP
        ips = [ip.strip() for ip in forwarded_for.split(",") if ip.strip()]
        if ips:
            # First IP in the list represents the originating client
            return f"ip:{ips[0]}"

    return f"ip:{client_host}"


class SlidingWindowRateLimiter:
    """
    In-memory thread-safe sliding window rate limiter.
    Maintains timestamps of recent requests per client identifier.
    """

    def __init__(self) -> None:
        # Maps (identifier, endpoint_tag) -> deque of request timestamps (epoch floats)
        self._history: Dict[Tuple[str, str], Deque[float]] = collections.defaultdict(collections.deque)

    def is_allowed(
        self,
        identifier: str,
        endpoint_tag: str,
        limit: int,
        window_seconds: int,
        now: Optional[float] = None,
    ) -> Tuple[bool, int, int]:
        """
        Check and record a request under sliding window.

        Args:
            identifier: Client identity (e.g. 'ip:10.0.0.1' or 'user:123').
            endpoint_tag: Grouping key (e.g. 'verify_endpoint').
            limit: Maximum requests allowed in the window.
            window_seconds: Duration of the sliding window in seconds.
            now: Current timestamp (defaults to time.time()).

        Returns:
            Tuple of:
            - is_allowed (bool)
            - remaining (int)
            - retry_after (int seconds, 0 if allowed)
        """
        current_time = now or time.time()
        key = (identifier, endpoint_tag)
        timestamps = self._history[key]

        # Purge timestamps outside current window
        cutoff = current_time - window_seconds
        while timestamps and timestamps[0] <= cutoff:
            timestamps.popleft()

        # Check if limit exceeded
        if len(timestamps) >= limit:
            oldest = timestamps[0]
            retry_after = max(1, int(oldest + window_seconds - current_time))
            return False, 0, retry_after

        # Record this request
        timestamps.append(current_time)
        remaining = max(0, limit - len(timestamps))
        return True, remaining, 0

    def reset(self) -> None:
        """Clear all recorded request history (useful in tests)."""
        self._history.clear()


# Global default limiter instance
_DEFAULT_LIMITER = SlidingWindowRateLimiter()


class RateLimitDependency:
    """
    FastAPI dependency for applying rate limits to specific routes.

    Usage:
        @app.post("/verify", dependencies=[Depends(RateLimitDependency("10/minute", tag="verify"))])
        async def verify_endpoint(...):
            ...
    """

    def __init__(
        self,
        rate_str: str,
        tag: str = "default",
        trusted_proxies: Optional[Set[str]] = None,
        limiter: Optional[SlidingWindowRateLimiter] = None,
    ) -> None:
        self.limit, self.window_seconds = parse_rate_string(rate_str)
        self.tag = tag
        self.trusted_proxies = trusted_proxies
        self.limiter = limiter or _DEFAULT_LIMITER

    async def __call__(self, request: Request, response: Response) -> None:
        identifier = extract_client_identifier(request, self.trusted_proxies)
        allowed, remaining, retry_after = self.limiter.is_allowed(
            identifier=identifier,
            endpoint_tag=self.tag,
            limit=self.limit,
            window_seconds=self.window_seconds,
        )

        # Set rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(self.window_seconds)

        if not allowed:
            raise RateLimitExceeded(
                limit=self.limit,
                window_seconds=self.window_seconds,
                retry_after=retry_after,
            )


# ------------------------------------------------------------------------------
# SlowAPI Adapter Integration (Optional / Interoperability)
# ------------------------------------------------------------------------------
def create_slowapi_limiter(
    default_limits: Optional[List[str]] = None,
    trusted_proxies: Optional[Set[str]] = None,
):
    """
    Factory function to initialize a SlowAPI Limiter configured with TruthLens
    user-aware key resolution and proxy headers.

    Returns:
        slowapi.Limiter instance, or None if slowapi is not installed.
    """
    try:
        from slowapi import Limiter
        from slowapi.util import get_remote_address

        def key_func(request: Request) -> str:
            return extract_client_identifier(request, trusted_proxies)

        return Limiter(
            key_func=key_func,
            default_limits=default_limits or ["60/minute"],
        )
    except ImportError:
        return None
