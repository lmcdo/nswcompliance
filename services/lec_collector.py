"""
LEC Decision Collector — FastAPI router.

POST /pipeline/lec/probe-year   — probe one year's decisions from AustLII
POST /pipeline/lec/fetch        — fetch + extract + store one decision to R2

AustLII blocks cloud datacenter IPs (AWS/Trigger.dev), but Railway's IP range
is not blocked. This router runs on Railway and is called by the Trigger.dev
tasks (lec-backfill.ts, lec-decision-monitor.ts) which cannot reach AustLII directly.

Storage: Cloudflare R2 (S3-compatible).
R2 layout:
  lec/state.json                   — { seen_ids: list[str], last_checked: ISO }
  lec/decisions/{year}/{id}.json   — structured extracted data per decision

Env vars required:
  R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME
  ANTHROPIC_API_KEY
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Optional

import boto3
import httpx
from anthropic import Anthropic
from botocore.exceptions import ClientError
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pipeline/lec", tags=["lec"])

# ── R2 client ─────────────────────────────────────────────────────────────────

R2_BUCKET = os.environ.get("R2_BUCKET_NAME", "")
R2_ACCOUNT_ID = os.environ.get("R2_ACCOUNT_ID", "")

_r2: Optional[object] = None

def get_r2():
    global _r2
    if _r2 is None:
        _r2 = boto3.client(
            "s3",
            endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
            aws_access_key_id=os.environ.get("R2_ACCESS_KEY_ID", ""),
            aws_secret_access_key=os.environ.get("R2_SECRET_ACCESS_KEY", ""),
            region_name="auto",
        )
    return _r2


STATE_KEY = "lec/state.json"


def read_state() -> dict:
    try:
        resp = get_r2().get_object(Bucket=R2_BUCKET, Key=STATE_KEY)
        return json.loads(resp["Body"].read())
    except ClientError as e:
        if e.response["Error"]["Code"] in ("NoSuchKey", "404"):
            return {"seen_ids": [], "last_checked": "1970-01-01T00:00:00Z"}
        raise


def write_state(state: dict) -> None:
    get_r2().put_object(
        Bucket=R2_BUCKET,
        Key=STATE_KEY,
        Body=json.dumps(state, indent=2).encode(),
        ContentType="application/json",
    )


def store_decision(year: int, case_id: str, decision: dict) -> None:
    key = f"lec/decisions/{year}/{case_id}.json"
    get_r2().put_object(
        Bucket=R2_BUCKET,
        Key=key,
        Body=json.dumps(decision, indent=2).encode(),
        ContentType="application/json",
    )


# ── AustLII fetching ──────────────────────────────────────────────────────────

AUSTLII_HEADERS = {
    "User-Agent": "Mozilla/5.0 (research/lec-collection; contact: plotdetect.com.au)",
    "Accept": "text/html,application/xhtml+xml",
}

AUSTLII_BASE = "https://www.austlii.edu.au"
TOC_LETTERS = list("0ABCDEFGHIJKLMNOPQRSTUVWXYZ")


def case_id_from_url(url: str) -> str:
    m = re.search(r"NSWLEC/(\d+)/(\d+)\.html", url, re.IGNORECASE)
    return f"NSWLEC-{m.group(1)}-{m.group(2)}" if m else url


def html_to_text(html: str) -> str:
    text = re.sub(r"<script[\s\S]*?</script>", "", html, flags=re.IGNORECASE)
    text = re.sub(r"<style[\s\S]*?</style>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&nbsp;", " ").replace("&quot;", '"')
    text = re.sub(r"&#\d+;", " ", text)
    text = re.sub(r"\s{3,}", "\n\n", text)
    return text.strip()


def probe_year(year: int) -> list[str]:
    """Return all decision URLs for a given year via AustLII TOC pages.

    Enumerates all 27 TOC pages (toc-0 through toc-Z), collects every
    viewdoc link that matches the target year. One pass covers the full
    database — much faster and more reliable than sequential HEAD probing.
    """
    year_str = str(year)
    found: list[str] = []

    with httpx.Client(headers=AUSTLII_HEADERS, timeout=15, follow_redirects=True) as client:
        for letter in TOC_LETTERS:
            toc_url = f"{AUSTLII_BASE}/cgi-bin/viewtoc/au/cases/nsw/NSWLEC/toc-{letter}.html"
            try:
                resp = client.get(toc_url)
                if resp.status_code != 200:
                    logger.warning("TOC %s returned %s", toc_url, resp.status_code)
                    continue
            except Exception as exc:
                logger.warning("TOC fetch error %s: %s", toc_url, exc)
                continue

            # Extract decision links matching this year
            for href in re.findall(r'href="(/cgi-bin/viewdoc/au/cases/nsw/NSWLEC/\d+/\d+\.html)"', resp.text):
                if f"/NSWLEC/{year_str}/" in href:
                    found.append(f"{AUSTLII_BASE}{href}")

            time.sleep(0.6)  # ≤ 2 req/sec

    found = list(dict.fromkeys(found))  # deduplicate, preserve order
    logger.info("Year %s: found %s decisions via TOC", year, len(found))
    return found


def fetch_decision_html(url: str) -> str:
    with httpx.Client(headers=AUSTLII_HEADERS, timeout=20, follow_redirects=True) as client:
        resp = client.get(url)
        resp.raise_for_status()
        return resp.text


# ── LLM extraction ────────────────────────────────────────────────────────────

_anthropic: Optional[Anthropic] = None

def get_anthropic() -> Anthropic:
    global _anthropic
    if _anthropic is None:
        _anthropic = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
    return _anthropic


EXTRACTION_PROMPT = """\
You are extracting structured data from a NSW Land and Environment Court (LEC) \
Class 1 appeal judgment.

Case ID: {case_id}

Return ONLY a valid JSON object — no markdown fences, no prose, no explanation:

{{
  "case_ref": "<citation e.g. [2024] NSWLEC 1 123, or empty string>",
  "judgment_date": "<ISO date YYYY-MM-DD, or empty string>",
  "property_address": "<street address if mentioned, otherwise empty string>",
  "lga": "<council or LGA name if mentioned, otherwise empty string>",
  "application_type": "<dwelling-house | dual-occupancy | multi-dwelling | subdivision | commercial | industrial | mixed-use | other>",
  "council_refusal_grounds": ["<refusal ground 1>"],
  "outcome": "<exactly one of: appellant_won | council_won | settled | remitted | unknown>",
  "appeal_grounds": ["<ground raised by appellant>"],
  "key_swing_factors": ["<factor that most influenced the outcome>"],
  "confidence": "<high if outcome clearly stated in ORDERS section; low if inferred>"
}}

Rules:
- ORDERS section is at the end of every LEC judgment. Appeal upheld/allowed → \
appellant_won. Dismissed → council_won.
- confidence: high only when you found and read the ORDERS section.
- If a field cannot be determined, use empty string or empty array.

Judgment text (first 6000 chars):
{text}"""


def extract_decision(text: str, case_id: str, source_url: str) -> dict | None:
    try:
        msg = get_anthropic().messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": EXTRACTION_PROMPT.format(
                    case_id=case_id,
                    text=text[:6000],
                ),
            }],
        )
        raw = msg.content[0].text.strip()
        result = json.loads(raw)
        result["source_url"] = source_url
        if not result.get("case_ref"):
            result["case_ref"] = case_id
        return result
    except Exception as exc:
        logger.warning("Extraction failed for %s: %s", case_id, exc)
        return None


# ── Request / response models ─────────────────────────────────────────────────

class ProbeYearRequest(BaseModel):
    year: int
    skip_seen: bool = True  # skip URLs already in state.json seen_ids


class ProbeYearResponse(BaseModel):
    year: int
    urls: list[str]
    skipped: int


class FetchDecisionRequest(BaseModel):
    url: str
    year: int  # used for R2 storage path


class FetchDecisionResponse(BaseModel):
    case_id: str
    stored: bool
    confidence: str
    outcome: str


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/probe-year", response_model=ProbeYearResponse)
def probe_year_endpoint(req: ProbeYearRequest):
    """
    Probe AustLII for all valid decision URLs in a given year.
    Returns the URL list — caller (Trigger.dev) iterates and calls /fetch for each.
    Filters out already-seen IDs if skip_seen=True.
    """
    if req.year < 1990 or req.year > 2030:
        raise HTTPException(status_code=400, detail="year out of range")

    urls = probe_year(req.year)

    skipped = 0
    if req.skip_seen:
        state = read_state()
        seen = set(state.get("seen_ids", []))
        original_count = len(urls)
        urls = [u for u in urls if case_id_from_url(u) not in seen]
        skipped = original_count - len(urls)

    return ProbeYearResponse(year=req.year, urls=urls, skipped=skipped)


@router.post("/fetch", response_model=FetchDecisionResponse)
def fetch_decision_endpoint(req: FetchDecisionRequest):
    """
    Fetch one AustLII decision URL, extract structured data via Claude, store to R2.
    Updates state.json seen_ids.
    """
    case_id = case_id_from_url(req.url)

    try:
        html = fetch_decision_html(req.url)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AustLII fetch failed: {exc}")

    text = html_to_text(html)
    decision = extract_decision(text, case_id, req.url)

    if decision is None:
        raise HTTPException(status_code=422, detail="Extraction failed — low quality or parse error")

    # Store decision to R2
    store_decision(req.year, case_id, decision)

    # Update state.json
    state = read_state()
    seen = set(state.get("seen_ids", []))
    seen.add(case_id)
    state["seen_ids"] = list(seen)
    write_state(state)

    if decision.get("confidence") == "low":
        logger.warning("Low-confidence extraction — flag for manual review: %s", case_id)

    return FetchDecisionResponse(
        case_id=case_id,
        stored=True,
        confidence=decision.get("confidence", "low"),
        outcome=decision.get("outcome", "unknown"),
    )


@router.post("/update-last-checked")
def update_last_checked(last_checked: str):
    """Update the last_checked timestamp in state.json (called by monitor after each run)."""
    state = read_state()
    state["last_checked"] = last_checked
    write_state(state)
    return {"ok": True, "last_checked": last_checked}


@router.get("/test-austlii")
def test_austlii():
    """Debug: make a single HEAD request to AustLII and return the result."""
    url = f"{AUSTLII_BASE}/cgi-bin/viewdoc/au/cases/nsw/NSWLEC/2024/100.html"
    try:
        with httpx.Client(headers=AUSTLII_HEADERS, timeout=15, follow_redirects=True) as client:
            resp = client.head(url)
            return {"url": url, "status": resp.status_code, "headers": dict(resp.headers)}
    except Exception as exc:
        return {"url": url, "error": str(exc)}


@router.get("/state")
def get_state():
    """Return current state (seen_ids count + last_checked). For debugging."""
    state = read_state()
    return {
        "seen_ids_count": len(state.get("seen_ids", [])),
        "last_checked": state.get("last_checked"),
    }
