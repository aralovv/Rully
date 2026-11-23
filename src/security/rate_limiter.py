"""
Thread-safe sliding window rate limiter for RULLY API endpoints.
Provides bounded in-memory eviction (maxsize) to prevent memory leaks in production.
"""

import os
import time
from collections import deque
from threading import Lock
from typing import Dict, Tuple, Optional

class SlidingWindowRateLimiter:
    def __init__(self, maxsize: int = 5000):
        self._records: Dict[str, deque] = {}
        self._maxsize = maxsize
        self._lock = Lock()

    def is_allowed(self, key: str, max_requests: int, window_seconds: float) -> Tuple[bool, int, float]:
        """
        Checks if request under 'key' is permitted within window.
        Returns: (is_allowed, remaining_quota, retry_after_seconds)
        """
        # Testing bypass unless explicitly enabled
        if os.getenv("ENVIRONMENT", "").lower() == "testing" and os.getenv("ENABLE_TEST_RATE_LIMIT", "").lower() != "true":
            return True, max_requests, 0.0

        now = time.time()
        cutoff = now - window_seconds

        with self._lock:
            # Self-prune if collection exceeds maxsize to protect RAM
            if len(self._records) > self._maxsize:
                stale_keys = [k for k, q in list(self._records.items())[:500] if not q or q[-1] < cutoff]
                for k in stale_keys:
                    self._records.pop(k, None)

            q = self._records.setdefault(key, deque())
            while q and q[0] <= cutoff:
                q.popleft()

            if len(q) >= max_requests:
                earliest = q[0]
                retry_after = max(0.1, earliest + window_seconds - now)
                return False, 0, retry_after

            q.append(now)
            remaining = max(0, max_requests - len(q))
            return True, remaining, 0.0

    def reset(self, key: Optional[str] = None):
        """Clears records for a key or all keys."""
        with self._lock:
            if key:
                self._records.pop(key, None)
            else:
                self._records.clear()

rate_limiter = SlidingWindowRateLimiter()
