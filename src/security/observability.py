"""
Bounded in-memory structured observability & latency telemetry for RULLY API.
Designed for $0 free-tier constraints (512 MB Render / Vercel serverless):
fixed-size deques per route group, zero PII storage, thread-safe p50/p95 metrics.
"""

import json
import logging
import os
import time
from collections import deque
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Deque, Dict, List, Optional

logger = logging.getLogger("rully.observability")


def classify_route_group(path: str) -> str:
    """Maps concrete request URL paths to bounded telemetry buckets."""
    p = (path or "/").lower()
    if p.startswith("/api/auth") or p.startswith("/api/user"):
        return "auth_user"
    if p.startswith("/api/ai"):
        return "ai_ustoz"
    if p.startswith("/api/payment"):
        return "payment"
    if p.startswith("/api/amaliy"):
        return "practical"
    if p.startswith("/api/admin"):
        return "admin"
    if p.startswith(("/api/categories", "/api/tickets", "/api/session", "/api/srs", "/api/mistakes", "/api/bookmarks", "/api/learning", "/api/theory", "/api/quiz")):
        return "theory_quiz"
    if p.startswith(("/api/health", "/api/ping", "/healthz")):
        return "health"
    if p.startswith(("/static/", "/images/", "/admin")) or p in ("/", "/index.html", "/favicon.ico"):
        return "static_shell"
    return "other"


def _percentile(sorted_vals: List[float], pct: float) -> float:
    if not sorted_vals:
        return 0.0
    idx = min(len(sorted_vals) - 1, max(0, int(round((pct / 100.0) * (len(sorted_vals) - 1)))))
    return round(sorted_vals[idx], 2)


def _read_process_rss_mb() -> Optional[float]:
    """Reads RSS memory on Linux containers (/proc/self/statm) without extra dependencies."""
    try:
        with open("/proc/self/statm", "r", encoding="utf-8") as fh:
            parts = fh.read().split()
            if len(parts) >= 2:
                rss_pages = int(parts[1])
                page_size = os.sysconf("SC_PAGE_SIZE")
                return round((rss_pages * page_size) / (1024.0 * 1024.0), 1)
    except Exception:
        pass
    return None


class ObservabilityRegistry:
    """Thread-safe bounded HTTP latency & error counter store."""

    def __init__(self, latency_window: int = 300, recent_cap: int = 25):
        self._lock = Lock()
        self._started_monotonic = time.monotonic()
        self._started_iso = datetime.now(timezone.utc).isoformat()
        self._cold_start_ms: Optional[float] = None
        self._router_mode: str = "full"
        self._latency_window = latency_window
        self._total_requests = 0
        self._errors_4xx = 0
        self._errors_5xx = 0
        self._latencies: Dict[str, Deque[float]] = {}
        self._group_counts: Dict[str, Dict[str, int]] = {}
        self._slow_requests: Deque[Dict[str, Any]] = deque(maxlen=recent_cap)
        self._recent_errors: Deque[Dict[str, Any]] = deque(maxlen=recent_cap)

    def set_boot_metadata(self, router_mode: str, cold_start_ms: float) -> None:
        with self._lock:
            self._router_mode = router_mode
            self._cold_start_ms = round(float(cold_start_ms), 2)

    def record_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        request_id: str,
    ) -> None:
        group = classify_route_group(path)
        dur = round(float(duration_ms), 2)
        now_iso = datetime.now(timezone.utc).isoformat()

        with self._lock:
            self._total_requests += 1
            if 400 <= status_code < 500:
                self._errors_4xx += 1
            elif status_code >= 500:
                self._errors_5xx += 1

            dq = self._latencies.get(group)
            if dq is None:
                dq = deque(maxlen=self._latency_window)
                self._latencies[group] = dq
            dq.append(dur)

            counts = self._group_counts.setdefault(group, {"count": 0, "errors_4xx": 0, "errors_5xx": 0})
            counts["count"] += 1
            if 400 <= status_code < 500:
                counts["errors_4xx"] += 1
            elif status_code >= 500:
                counts["errors_5xx"] += 1

            if dur >= 500.0:
                self._slow_requests.append(
                    {
                        "ts": now_iso,
                        "request_id": request_id,
                        "method": method,
                        "path": path[:120],
                        "group": group,
                        "status": status_code,
                        "duration_ms": dur,
                    }
                )
            if status_code >= 500:
                self._recent_errors.append(
                    {
                        "ts": now_iso,
                        "request_id": request_id,
                        "method": method,
                        "path": path[:120],
                        "group": group,
                        "status": status_code,
                        "duration_ms": dur,
                    }
                )

        if status_code >= 500 or dur >= 1000.0:
            logger.warning(
                json.dumps(
                    {
                        "event": "http_anomaly",
                        "request_id": request_id,
                        "method": method,
                        "path": path[:120],
                        "group": group,
                        "status": status_code,
                        "duration_ms": dur,
                    }
                )
            )

    def reset(self) -> None:
        with self._lock:
            self._total_requests = 0
            self._errors_4xx = 0
            self._errors_5xx = 0
            self._latencies.clear()
            self._group_counts.clear()
            self._slow_requests.clear()
            self._recent_errors.clear()

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            routes_out: Dict[str, Any] = {}
            all_vals: List[float] = []
            for group, dq in sorted(self._latencies.items()):
                vals = sorted(dq)
                all_vals.extend(vals)
                cnts = self._group_counts.get(group, {})
                routes_out[group] = {
                    "count": int(cnts.get("count", 0)),
                    "errors_4xx": int(cnts.get("errors_4xx", 0)),
                    "errors_5xx": int(cnts.get("errors_5xx", 0)),
                    "p50_ms": _percentile(vals, 50.0),
                    "p95_ms": _percentile(vals, 95.0),
                }
            all_vals.sort()
            total = self._total_requests
            err_rate = round((self._errors_5xx / total) * 100.0, 2) if total > 0 else 0.0
            global_p50 = _percentile(all_vals, 50.0)
            global_p95 = _percentile(all_vals, 95.0)
            top_routes = sorted(
                [{"route": k, **v} for k, v in routes_out.items()],
                key=lambda item: item["count"],
                reverse=True,
            )
            return {
                "started_at": self._started_iso,
                "uptime_seconds": round(time.monotonic() - self._started_monotonic, 1),
                "router_mode": self._router_mode,
                "cold_start_ms": self._cold_start_ms,
                "memory_rss_mb": _read_process_rss_mb(),
                "total_requests": total,
                "errors_4xx": self._errors_4xx,
                "errors_5xx": self._errors_5xx,
                "error_5xx_rate_pct": err_rate,
                "global_p50_ms": global_p50,
                "global_p95_ms": global_p95,
                "latency_p50_ms": global_p50,
                "latency_p95_ms": global_p95,
                "routes": routes_out,
                "top_routes": top_routes,
                "slow_requests": list(self._slow_requests),
                "recent_errors": list(self._recent_errors),
            }


observability = ObservabilityRegistry()
