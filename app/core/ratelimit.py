"""A small in-process sliding-window rate limiter.

Keyed per client (IP for login, user id for orders) and applied as FastAPI
dependencies. It is deliberately dependency-free: state lives in the process,
which is exact for the single Uvicorn deployment described in the README, and
a front-side Nginx ``limit_req`` (or Redis) is the documented next step for
multi-process/multi-host deployments.
"""

import time
from collections import defaultdict, deque
from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status

from app.core.config import settings

_WINDOW = settings.RATE_LIMIT_WINDOW_SECONDS


class SlidingWindowLimiter:
    """history of allowed hits; a caller is limited to `limit` per window."""

    def __init__(self, limit: int, window_seconds: float = _WINDOW) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def hit(self, key: str, *, now: float | None = None) -> None:
        """Register one hit for `key`; raise 429 when over the limit."""
        if self.limit <= 0:
            return
        moment = time.monotonic() if now is None else now
        history = self._hits[key]
        cutoff = moment - self.window_seconds
        while history and history[0] <= cutoff:
            history.popleft()
        if len(history) >= self.limit:
            retry_after = max(0.0, history[0] + self.window_seconds - moment)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests, slow down",
                headers={"Retry-After": str(int(retry_after) + 1)},
            )
        history.append(moment)

    def reset(self) -> None:
        self._hits.clear()


def client_ip(request: Request) -> str:
    """Trust only what the trusted proxy set (Uvicorn's forwarded-allow-ips
    already filters this); fall back to the direct peer."""
    host = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
    return host or (request.client.host if request.client else "unknown")


def rate_limit(
    limiter: SlidingWindowLimiter, key_from: Callable[[Request], str]
) -> Callable:
    """Build a dependency that applies `limiter` to the per-request key."""

    def dependency(request: Request) -> None:
        limiter.hit(key_from(request))

    return Depends(dependency)
