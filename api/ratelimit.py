"""Small in-memory sliding-window rate limiter (per process) for abuse-prone endpoints.

Client identity: the TCP peer address, or — when FIREWISE_TRUST_PROXY=1 (e.g. behind Render's proxy) — the
RIGHT-most X-Forwarded-For entry, which is the address the trusted proxy itself saw (left-most entries are
client-controlled and can be spoofed).
"""
import os
import threading
import time
from collections import defaultdict, deque

_lock = threading.Lock()
_hits = defaultdict(deque)


def client_id(request):
    if os.environ.get("FIREWISE_TRUST_PROXY") == "1":
        xff = request.headers.get("x-forwarded-for", "")
        parts = [p.strip() for p in xff.split(",") if p.strip()]
        if parts:
            return parts[-1]
    return request.client.host if request.client else "unknown"


def allow(bucket, key, limit, window_s):
    """True if this call is within `limit` calls per `window_s` seconds for (bucket, key)."""
    now = time.monotonic()
    with _lock:
        q = _hits[(bucket, key)]
        while q and now - q[0] > window_s:
            q.popleft()
        if len(q) >= limit:
            return False
        q.append(now)
        return True


def reset():
    with _lock:
        _hits.clear()
