"""AI-based DCP chapter extraction — model-agnostic, drop-in for DCPExtractor.extract().

Reads any PDF layout via a document-capable LLM (no per-council regex/config), and
returns section dicts in the SAME shape the regex extractor produces, so the
downstream diff / enqueue / guard pipeline is unchanged.

Enabled by AI_EXTRACTION=1; off by default. Model picked by AI_MODEL
(haiku | mistral). Validated on the watermarked Woollahra c2: Haiku 141 clean /
$0.63, Mistral-small 89 clean / $0.04 (regex got 1 garbage blob).

See ~/.claude/plans/ce-ai-extraction-decision-2026-07.md.

prior-art-checked: reuse not viable because the existing matches are frontend
provision DISPLAY/relevance (ProvisionsByTocStructure.tsx, for-property routes,
formatProvisions.ts) and SEPP markdown/quantitative extractors — none perform
model-agnostic LLM PDF->provision extraction for the DCP pipeline. This is a new
extraction engine behind AI_EXTRACTION, a drop-in for DCPExtractor.extract().
"""
from __future__ import annotations

import base64
import io
import json
import os
import re
import time
import urllib.error
import urllib.request

AI_CHUNK_PAGES = int(os.getenv("AI_CHUNK_PAGES", "12"))
_MAX_RETRIES = 5
_BACKOFF_BASE = 2.0  # seconds; exponential

PROMPT = (
    "This is part of a NSW council Development Control Plan. Extract every numbered "
    "provision (objectives, controls, clauses). Return a JSON object "
    '{"provisions": [{"code","title","text"}]}. Split each individual objective '
    "(O1, O2...) and control (C1, C2...) into its own provision where they are "
    "separately numbered. IGNORE running page headers, footers, page numbers, and "
    "any faint rotated watermark/date characters in the margins. Do not invent "
    "provisions. Output ONLY the JSON object."
)


# ── chunking ─────────────────────────────────────────────────────────────────
def chunk_ranges(total_pages: int, chunk: int = AI_CHUNK_PAGES) -> list[tuple[int, int]]:
    """0-indexed [start, end) page ranges covering total_pages. Pure."""
    if total_pages <= 0 or chunk <= 0:
        return []
    return [(s, min(s + chunk, total_pages)) for s in range(0, total_pages, chunk)]


def _subset_bytes(reader, a: int, b: int) -> bytes:
    from pypdf import PdfWriter
    w = PdfWriter()
    for i in range(a, min(b, len(reader.pages))):
        w.add_page(reader.pages[i])
    buf = io.BytesIO()
    w.write(buf)
    return buf.getvalue()


# ── parsing (pure) ───────────────────────────────────────────────────────────
def parse_provisions(text: str) -> list[dict]:
    """Parse a model response into a list of {code,title,text}. Tolerant of code
    fences, an object wrapper, or a bare array. Pure."""
    if not text:
        return []
    t = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.M).strip()
    try:
        d = json.loads(t)
        if isinstance(d, dict):
            d = d.get("provisions", [])
        return [p for p in d if isinstance(p, dict)] if isinstance(d, list) else []
    except Exception:
        m = re.search(r"\[.*\]", t, re.S)
        if not m:
            return []
        try:
            d = json.loads(m.group(0))
            return [p for p in d if isinstance(p, dict)] if isinstance(d, list) else []
        except Exception:
            return []


def dedupe_provisions(provs: list[dict]) -> list[dict]:
    """Drop provisions with no/blank code; keep the first per code. Pure."""
    seen: set[str] = set()
    out: list[dict] = []
    for p in provs:
        code = str(p.get("code", "")).strip()
        if code and code not in seen:
            seen.add(code)
            out.append(p)
    return out


def provisions_to_sections(provs: list[dict]) -> list[dict]:
    """Map [{code,title,text,page?}] to the section-dict shape DCPExtractor.extract()
    returns, so build_provision_text / diff / enqueue work unchanged. Pure."""
    sections: list[dict] = []
    for p in provs:
        code = str(p.get("code", "")).strip()
        if not code:
            continue
        raw_page = p.get("page")
        try:
            page = int(raw_page) if raw_page is not None else 1
        except (TypeError, ValueError):
            page = 1
        sections.append({
            "section_number": code,
            "section_title": str(p.get("title", "")).strip(),
            "content": str(p.get("text", "")),
            "tables": [],
            "page_start": page,
            "page_end": page,
            "pages": [page],
        })
    return sections


# ── providers ────────────────────────────────────────────────────────────────
def _call_haiku(pdf_bytes: bytes) -> str:
    import anthropic
    client = anthropic.Anthropic()
    data = base64.standard_b64encode(pdf_bytes).decode()
    msg = client.messages.create(
        model=os.getenv("AI_MODEL_ID", "claude-haiku-4-5"),
        max_tokens=8000,
        messages=[{"role": "user", "content": [
            {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": data}},
            {"type": "text", "text": PROMPT}]}],
    )
    return msg.content[0].text


def _call_mistral(pdf_bytes: bytes) -> str:
    key = os.environ["MISTRAL_API_KEY"]
    b64 = base64.standard_b64encode(pdf_bytes).decode()
    body = {
        "model": os.getenv("AI_MODEL_ID", "mistral-small-latest"),
        "max_tokens": 8000,
        "response_format": {"type": "json_object"},
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": PROMPT},
            {"type": "document_url", "document_url": f"data:application/pdf;base64,{b64}"}]}],
    }
    req = urllib.request.Request(
        "https://api.mistral.ai/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.load(r)["choices"][0]["message"]["content"]


_PROVIDERS = {"haiku": _call_haiku, "mistral": _call_mistral}


def _is_retryable(exc: Exception) -> bool:
    if isinstance(exc, urllib.error.HTTPError):
        return exc.code in (429, 500, 502, 503, 529)
    name = type(exc).__name__
    status = getattr(exc, "status_code", None)
    return name in ("RateLimitError", "OverloadedError", "APIStatusError") or status in (429, 500, 502, 503, 529)


def _call_with_retry(model: str, pdf_bytes: bytes) -> str:
    fn = _PROVIDERS.get(model)
    if fn is None:
        raise ValueError(f"Unknown AI_MODEL={model!r}. Known: {', '.join(_PROVIDERS)}")
    last: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            return fn(pdf_bytes)
        except Exception as exc:  # noqa: BLE001 — provider SDKs raise varied types
            last = exc
            if not _is_retryable(exc) or attempt == _MAX_RETRIES - 1:
                raise
            time.sleep(_BACKOFF_BASE * (2 ** attempt))
    raise last  # pragma: no cover


# ── entrypoint ───────────────────────────────────────────────────────────────
def ai_extract_chapter(pdf_path, council: str | None = None, model: str | None = None) -> list[dict]:
    """Extract a chapter's provisions via an LLM. Returns section dicts matching
    DCPExtractor.extract(). `council` is accepted for signature parity (the model
    needs no per-council config)."""
    from pypdf import PdfReader
    model = (model or os.getenv("AI_MODEL", "haiku")).strip().lower()
    reader = PdfReader(str(pdf_path))
    total = len(reader.pages)
    collected: list[dict] = []
    for (a, b) in chunk_ranges(total):
        raw = _call_with_retry(model, _subset_bytes(reader, a, b))
        for p in parse_provisions(raw):
            p.setdefault("page", a + 1)  # approximate: first page of the chunk
            collected.append(p)
    return provisions_to_sections(dedupe_provisions(collected))
