"""
Thread-safe sliding window rate limiter for RULLY API endpoints.
Provides bounded in-memory eviction (maxsize) to prevent memory leaks in production.
"""

import os
import time
from collections import deque, OrderedDict
from threading import Lock
from typing import Dict, Tuple, Optional, Any, Generic, TypeVar

class SlidingWindowRateLimiter:
    def __init__(self, maxsize: int = 5000):
        self._records: Dict[str, deque] = {}
        self._maxsize = maxsize
        self._rejections_total = 0
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
                self._rejections_total += 1
                earliest = q[0]
                retry_after = max(0.1, earliest + window_seconds - now)
                return False, 0, retry_after

            q.append(now)
            remaining = max(0, max_requests - len(q))
            return True, remaining, 0.0

    def stats(self) -> Dict[str, int]:
        with self._lock:
            return {
                "tracked_keys": len(self._records),
                "maxsize": self._maxsize,
                "rejections_total": self._rejections_total,
            }

    def reset(self, key: Optional[str] = None):
        """Clears records for a key or all keys."""
        with self._lock:
            if key:
                self._records.pop(key, None)
            else:
                self._records.clear()


import ipaddress
import os as _os


def _parse_valid_ip(raw_val: Optional[str]) -> Optional[str]:
    if not raw_val:
        return None
    candidate = str(raw_val).strip()
    try:
        return str(ipaddress.ip_address(candidate))
    except ValueError:
        return None


_TRUSTED_PROXY_NETS = (
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
)


def _is_trusted_proxy_peer(peer_ip: Optional[str]) -> bool:
    if not peer_ip or peer_ip in ("testclient", "localhost", "unknown"):
        return True
    extra_proxies = {p.strip() for p in _os.getenv("TRUSTED_PROXY_IPS", "").split(",") if p.strip()}
    if peer_ip in extra_proxies:
        return True
    try:
        addr = ipaddress.ip_address(peer_ip)
        return any(addr in net for net in _TRUSTED_PROXY_NETS)
    except ValueError:
        return False


def get_client_ip(request: Any) -> str:
    """Extracts true caller IP safely behind trusted Vercel/Render/Cloudflare proxies."""
    headers = getattr(request, "headers", None) or {}
    client = getattr(request, "client", None)
    peer_host = getattr(client, "host", None) if client else None
    peer_ip = _parse_valid_ip(peer_host) or (str(peer_host or "unknown")[:64])

    # Platform edge header overwritten strictly by Vercel edge
    if _os.getenv("VERCEL"):
        vercel_ip = _parse_valid_ip(headers.get("x-vercel-forwarded-for"))
        if vercel_ip:
            return vercel_ip

    # Only honor forwarding headers when direct TCP peer is a trusted proxy hop
    if _is_trusted_proxy_peer(peer_host):
        cf_ip = _parse_valid_ip(headers.get("cf-connecting-ip"))
        if cf_ip:
            return cf_ip

        xff = headers.get("x-forwarded-for")
        if xff:
            parts = [p.strip() for p in str(xff).split(",") if p.strip()]
            # Walk right-to-left picking the rightmost non-proxy hop to defeat client spoofing
            for part in reversed(parts):
                parsed = _parse_valid_ip(part)
                if parsed and not _is_trusted_proxy_peer(parsed):
                    return parsed
            for part in parts:
                parsed = _parse_valid_ip(part)
                if parsed:
                    return parsed

        real_ip = _parse_valid_ip(headers.get("x-real-ip"))
        if real_ip:
            return real_ip

    return str(peer_ip or "unknown")[:64]

rate_limiter = SlidingWindowRateLimiter()

K = TypeVar("K")
V = TypeVar("V")

class BoundedTTLCache(Generic[K, V]):
    """
    Thread-safe Bounded LRU Cache with Time-To-Live (TTL) eviction.
    Protects server RAM from unbounded dictionary growth.
    """
    def __init__(self, maxsize: int = 2000, ttl_seconds: float = 60.0):
        self._cache: OrderedDict[K, Tuple[float, V]] = OrderedDict()
        self._maxsize = maxsize
        self._ttl = ttl_seconds
        self._lock = Lock()

    def get(self, key: K, default: Any = None) -> Optional[V]:
        now = time.time()
        with self._lock:
            if key not in self._cache:
                return default
            ts, val = self._cache[key]
            if now - ts > self._ttl:
                del self._cache[key]
                return default
            self._cache.move_to_end(key)
            return val

    def set(self, key: K, val: V):
        now = time.time()
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = (now, val)
            while len(self._cache) > self._maxsize:
                self._cache.popitem(last=False)

    def pop(self, key: K, default: Any = None) -> Optional[V]:
        with self._lock:
            if key in self._cache:
                _, val = self._cache.pop(key)
                return val
            return default

    def clear(self):
        with self._lock:
            self._cache.clear()

    def prune_expired(self):
        """Remove all entries whose TTL has passed."""
        now = time.time()
        with self._lock:
            expired_keys = [k for k, (ts, _) in self._cache.items() if now - ts > self._ttl]
            for k in expired_keys:
                del self._cache[k]

    def __contains__(self, key: K) -> bool:
        return self.get(key) is not None

    def __len__(self) -> int:
        with self._lock:
            return len(self._cache)

