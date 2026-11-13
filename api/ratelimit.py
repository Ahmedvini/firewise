"""Small in-memory sliding-window rate limiter (per process) for abuse-prone endpoints.

Client identity (choose to match the real proxy chain in front of the app — verify after deploying):
- default: the TCP peer address (request.client.host);
- FIREWISE_CLIENT_IP_HEADER=<name>: a dedicated client-IP header set by the operator's edge proxy
  (e.g. cf-connecting-ip); only safe when that proxy always overwrites it;
- FIREWISE_TRUST_PROXY=1 with FIREWISE_TRUSTED_HOPS=N (default 1): the X-Forwarded-For entry appended by the
  N-th trusted proxy counting from the right, i.e. parts[-N]. Entries further left are client-controlled.
If the chain is misconfigured, all clients may share one bucket — fail-safe for abuse, but noisy; check it.
"""
import os
import threading
import time
from collections import defaultdict, deque

_lock = threading.Lock()
_hits = defaultdict(deque)


def client_id(request):
    header = os.environ.get("FIREWISE_CLIENT_IP_HEADER", "").strip().lower()
    if header:
        v = request.headers.get(header, "").strip()
        if v:
            return v
    if os.environ.get("FIREWISE_TRUST_PROXY") == "1":
        try:
            hops = max(1, int(os.environ.get("FIREWISE_TRUSTED_HOPS", "1")))
        except ValueError:
            hops = 1
        parts = [p.strip() for p in request.headers.get("x-forwarded-for", "").split(",") if p.strip()]
        if len(parts) >= hops:
            return parts[-hops]
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
