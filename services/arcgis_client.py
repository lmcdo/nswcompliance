"""
Shared ArcGIS REST client with retry and circuit breaker.

All new service modules that query government ArcGIS endpoints
should use arcgis_get_with_retry() instead of raw requests.get().

See TIER1_BUILD_SPEC.md §A1.1 and §A1.2.
"""
import logging
import threading
import time
from typing import Optional

import requests

logger = logging.getLogger(__name__)

ARCGIS_TIMEOUT = 8  # seconds
MAX_RETRIES = 2
RETRY_BACKOFF = [1.0, 2.0]  # seconds between retries


# ---------------------------------------------------------------------------
# Circuit breaker — per-endpoint health tracking
# ---------------------------------------------------------------------------

class EndpointHealth:
    """Per-endpoint circuit breaker. After N consecutive failures, skip for cooldown_s."""

    def __init__(self, cooldown_s: int = 60, threshold: int = 3):
        self._failures: dict[str, int] = {}
        self._cooldown_until: dict[str, float] = {}
        self._lock = threading.Lock()
        self._cooldown_s = cooldown_s
        self._threshold = threshold

    def is_healthy(self, endpoint: str) -> bool:
        with self._lock:
            until = self._cooldown_until.get(endpoint, 0)
            if time.monotonic() < until:
                return False
            return True

    def record_success(self, endpoint: str) -> None:
        with self._lock:
            self._failures[endpoint] = 0

    def record_failure(self, endpoint: str) -> None:
        with self._lock:
            count = self._failures.get(endpoint, 0) + 1
            self._failures[endpoint] = count
            if count >= self._threshold:
                self._cooldown_until[endpoint] = time.monotonic() + self._cooldown_s
                logger.warning(
                    "Circuit open for %s — cooling down %ds", endpoint, self._cooldown_s
                )


# Singleton shared across the service layer
endpoint_health = EndpointHealth()


# ---------------------------------------------------------------------------
# Retry-aware GET
# ---------------------------------------------------------------------------

def arcgis_get_with_retry(
    url: str,
    params: dict,
    timeout: int = ARCGIS_TIMEOUT,
) -> dict:
    """GET with retry on timeout/5xx. Returns parsed JSON or empty dict on failure."""
    if not endpoint_health.is_healthy(url):
        logger.warning("Circuit open for %s — skipping request", url)
        return {}

    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = requests.get(url, params=params, timeout=timeout)
            if resp.status_code == 429:
                logger.warning("Rate limited by %s — not retrying", url)
                endpoint_health.record_failure(url)
                return {}
            if resp.status_code >= 500 and attempt < MAX_RETRIES:
                logger.warning("%s returned %d, retry %d", url, resp.status_code, attempt + 1)
                time.sleep(RETRY_BACKOFF[attempt])
                continue
            resp.raise_for_status()
            data = resp.json()
            if "error" in data:
                logger.warning(
                    "ArcGIS error from %s: %s", url, data.get("error", {}).get("message", "")
                )
                endpoint_health.record_failure(url)
                return {}
            endpoint_health.record_success(url)
            return data
        except requests.Timeout:
            if attempt < MAX_RETRIES:
                logger.warning("Timeout on %s, retry %d", url, attempt + 1)
                time.sleep(RETRY_BACKOFF[attempt])
                continue
            logger.error("Final timeout on %s", url)
            endpoint_health.record_failure(url)
            return {}
        except Exception as e:
            logger.error("Error querying %s: %s", url, e)
            endpoint_health.record_failure(url)
            return {}
    return {}
