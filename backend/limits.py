"""
Guardrails for the chat endpoint: a bounded wait and a turn budget.

Two problems this solves.

**A hung model call used to hang the browser.** `agent.run()` had no timeout, so
if the gateway stalled the request never returned and the widget spun forever
with no way to recover but a reload. A bounded wait turns that into a clear
message in a few seconds.

**Every turn costs real money.** The gateway bills per call, so an open chat
endpoint with no ceiling is a budget anyone can drain with a loop. The limiter
caps turns per shopper over a sliding window.

The limiter is in-process, which is right for a single-worker course project
and explicitly not right for a multi-process deployment — see the note in
harness.md.
"""

from __future__ import annotations

import threading
import time
from collections import deque

# How long to wait for the agent before giving up. Observed turns run 2-20s;
# 45 leaves generous headroom while still bounding the worst case.
AGENT_TIMEOUT_SECONDS = 45.0

# Sliding window: at most MAX_TURNS in WINDOW_SECONDS, per shopper.
WINDOW_SECONDS = 300.0
MAX_TURNS = 25


class RateLimiter:
    """Sliding-window counter keyed by caller identity."""

    def __init__(self, max_events: int = MAX_TURNS, window: float = WINDOW_SECONDS) -> None:
        self.max_events = max_events
        self.window = window
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def check(self, key: str) -> tuple[bool, int]:
        """
        Record an attempt.

        Returns (allowed, retry_after_seconds). When allowed, retry_after is the
        seconds remaining in the current window, for the caller's information.
        """
        now = time.monotonic()
        with self._lock:
            hits = self._hits.setdefault(key, deque())

            cutoff = now - self.window
            while hits and hits[0] < cutoff:
                hits.popleft()

            if len(hits) >= self.max_events:
                retry_after = int(hits[0] + self.window - now) + 1
                return False, max(retry_after, 1)

            hits.append(now)

            # Opportunistic cleanup so idle keys do not accumulate forever.
            if len(self._hits) > 512:
                for k in [k for k, v in self._hits.items() if not v or v[-1] < cutoff]:
                    self._hits.pop(k, None)

            return True, int(self.window - (now - hits[0]))

    def reset(self, key: str | None = None) -> None:
        """Clear one key, or all of them. Used by tests."""
        with self._lock:
            if key is None:
                self._hits.clear()
            else:
                self._hits.pop(key, None)


chat_limiter = RateLimiter()


def caller_key(user_id: int | None, client_host: str | None) -> str:
    """
    Identity for rate limiting.

    A signed-in shopper is limited by account, so the limit follows them across
    devices. A guest is limited by IP, which is coarse — people behind one
    network share a budget — but it is the only identifier available without
    tracking them.
    """
    if user_id is not None:
        return f"user:{user_id}"
    return f"ip:{client_host or 'unknown'}"
