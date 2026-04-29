"""
FastAPI router — RSS proxy for forum monitor.

Registered at: GET /api/proxy/rss?url=<encoded_feed_url>

Fetches the RSS feed server-side (Railway egress) and returns the raw XML.
Exists because Trigger.dev cloud IPs are blocked by PropertyChat; Railway is not.

No auth — only accepts known PropertyChat RSS URLs to prevent open proxy abuse.
"""

import os
from urllib.parse import unquote

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

router = APIRouter(prefix="/api/proxy")

# Allowlist — only PropertyChat RSS feeds accepted
_ALLOWED_HOSTS = {
    "www.propertychat.com.au",
}

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}


@router.get("/rss")
async def rss_proxy(url: str) -> Response:
    """Proxy an RSS feed URL, returning raw XML."""
    decoded = unquote(url)

    # Allowlist check
    try:
        from urllib.parse import urlparse
        host = urlparse(decoded).netloc
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid URL")

    if host not in _ALLOWED_HOSTS:
        raise HTTPException(status_code=403, detail=f"Host not allowed: {host}")

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
            resp = await client.get(decoded, headers=_HEADERS)
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Feed fetch timed out")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Feed fetch failed: {e}")

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=f"Feed returned {resp.status_code}")

    return Response(
        content=resp.content,
        media_type="application/xml",
    )
