"""
FinGuard AI — Phase 32: Sliding-Window Rate Limiter.
Enforces request rate limits across client IPs and tenants using an in-memory sliding-window log.
"""
from __future__ import annotations

import threading
import time
from typing import Dict, List, Tuple


class SlidingWindowRateLimiter:
    def __init__(self, default_limit: int = 60, default_window_seconds: int = 60):
        self._lock = threading.RLock()
        self._windows: Dict[str, List[float]] = {}
        self.default_limit = default_limit
        self.default_window_seconds = default_window_seconds

    def is_allowed(
        self,
        key: str,
        limit: Optional[int] = None,
        window_seconds: Optional[int] = None,
    ) -> Tuple[bool, int, int]:
        """
        Evaluates whether a request for 'key' is permitted under the sliding-window threshold.
        Returns:
            (is_allowed: bool, remaining_tokens: int, retry_after_seconds: int)
        """
        max_requests = limit if limit is not None else self.default_limit
        window_sec = window_seconds if window_seconds is not None else self.default_window_seconds

        now = time.time()
        cutoff = now - window_sec

        with self._lock:
            timestamps = self._windows.get(key, [])
            # Filter timestamps outside sliding window
            valid_timestamps = [t for t in timestamps if t > cutoff]

            if len(valid_timestamps) >= max_requests:
                # Rate limit exceeded
                oldest_in_window = valid_timestamps[0]
                retry_after = max(1, int(oldest_in_window + window_sec - now))
                self._windows[key] = valid_timestamps
                return False, 0, retry_after

            # Request allowed: append current timestamp
            valid_timestamps.append(now)
            self._windows[key] = valid_timestamps
            remaining = max(0, max_requests - len(valid_timestamps))
            return True, remaining, 0

    def reset(self, key: Optional[str] = None):
        """Resets the rate limiter window (useful for tests)."""
        with self._lock:
            if key:
                self._windows.pop(key, None)
            else:
                self._windows.clear()


# Global singleton instance
rate_limiter = SlidingWindowRateLimiter()

