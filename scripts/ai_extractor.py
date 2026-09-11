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
_EMPTY_PARSE_MAX_RETRIES = 2  # a non-trivial response parsing to 0 provisions is
                               # very likely a truncated/malformed body, not a
                               # genuine empty chunk -- see ai_extract_chapter.

PROMPT = (
    "This is part of a NSW council Development Control Plan. Extract every numbered "
    "provision (objectives, controls, clauses). Return a JSON object "
    '{"provisions": [{"code","title","text"}]}. Split each individual objective '
    "(O1, O2...) and control (C1, C2...) into its own provision where they are "
    "separately numbered. Each provision's \"code\" MUST be fully section-qualified: "
    "the section number followed by the objective/control label, e.g. \"C4.9 O1\", "
    "\"C4.9 C2\" — NEVER a bare \"O1\" or \"C1\" without its section number. IGNORE "
    "running page headers, footers, page numbers, and any faint rotated watermark/date "
    "characters in the margins. Do not invent provisions. Output ONLY the JSON object."
)


def _build_prompt(current_section: str | None = None) -> str:
    """PROMPT plus, when a page range continues a section whose heading fell in an
    earlier chunk, the section number so the model still qualifies those codes."""
    if current_section:
        return PROMPT + (
            f" These pages may continue section {current_section} from the previous page: "
            f"any objective/control appearing before the next section heading belongs to "
            f"{current_section}, so qualify it as \"{current_section} O1\", "
            f"\"{current_section} C1\", etc."
        )
    return PROMPT


# a section code looks like "C4.9" / "3.1" / "A2.10.1" — an optional letter then
# dotted numbers; used to carry the current section across chunk boundaries.
_SECTION_RE = re.compile(r"^[A-Za-z]?\d+(?:\.\d+)+$")


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


# ── AI-path railguards (absolute-quality; robust to LLM non-determinism) ──────
# LLM extraction can silently drop whole sections or truncate a provision mid-text
# (observed in the Haiku/Mistral head-to-head). These guards catch those without
# relying on a diff, and feed the existing SUSPECT surface (suspect_reason ->
# build_suspect_alert -> Telegram). Advisory only — they never block a commit.
COVERAGE_MIN_TOC = 8       # only judge coverage when the TOC lists >= this many codes
COVERAGE_MISS_RATIO = 0.25  # flag when > this fraction of TOC sections are missing
TRUNCATION_MIN_CHARS = 40   # a provision shorter than this (and not a bare ref) is thin
TRUNCATION_RATIO = 0.10     # flag when > this fraction of provisions look truncated/thin


def coverage_gap(extracted_codes: set[str], toc_codes: set[str]) -> tuple[float | None, list[str]]:
    """Fraction (and list) of TOC section codes NOT covered by the extraction. A TOC
    code (e.g. "C4.1") is covered if an extracted code:
      - equals it exactly ("C4.1"), OR
      - is a dotted sub-provision of it ("C4.1.2"), OR
      - has it as the leading token before the first space ("C4.1 O1", "C4.1 C3") —
        the AI emits provisions as "<section> <objective/control>", so this is the
        common case and its absence was the source of false coverage_fail alerts.
    Pure.

    Returns **None** as the ratio when the TOC is too small to judge — NOT 0.0.

    WHY THIS CHANGED (2026-09-12)
    -----------------------------
    It returned ``(0.0, [])`` here, which every caller read as "judged, and
    nothing is missing". Combined with a TOC regex that matched 0 of 10 real
    Waverley contents lines, that made this function report a clean pass every
    single time it FAILED TO READ the document — for two and a half months,
    while 11 parts were absent and 54 rows were mislabelled.

    "Could not judge" and "judged and found nothing" are different answers, and
    collapsing them is the defect. None forces the caller to say which it meant;
    the call site in dcp_extract_changed treats it as suspect, not as clean.
    """
    if len(toc_codes) < COVERAGE_MIN_TOC:
        return None, []
    section_tokens = {e.split(" ", 1)[0] for e in extracted_codes}
    missing = [
        c for c in toc_codes
        if c not in extracted_codes
        and c not in section_tokens
        and not any(e.startswith(c + ".") for e in extracted_codes)
    ]
    return len(missing) / len(toc_codes), sorted(missing)


def truncation_rate(texts: list[str]) -> tuple[float, int]:
    """Fraction (and count) of provisions that look truncated or thin — text ending in
    an ellipsis, or shorter than TRUNCATION_MIN_CHARS and not a bare cross-reference.
    Pure. Catches LLM output-token cutoffs and dropped bodies."""
    if not texts:
        return 0.0, 0
    flagged = 0
    for t in texts:
        s = (t or "").strip()
        if s.endswith("...") or s.endswith("…"):
            flagged += 1
        elif len(s) < TRUNCATION_MIN_CHARS and not re.match(r"(?i)^(see|refer|as per)\b", s):
            flagged += 1
    return flagged / len(texts), flagged


def toc_codes_from_pdf(pdf_path, max_scan: int = 14) -> set[str]:
    """Return the set of section codes listed in the chapter's TOC, for the coverage
    guard. Returns an empty set if the PDF can't be read or has no parseable TOC —
    which coverage_gap now reports as "could not judge", not as a pass.

    REPOINTED 2026-09-12 from dcp_extract_changed.parse_toc_entries to
    dcp_toc_parse.parse_contents. The old parser requires dot leaders or double
    spacing before a trailing page number, and real DCP contents pages come in at
    least six shapes — it matched 0 of 10 Waverley lines and could not read
    canterbury_bankstown or ku_ring_gai at all (73 of 113 unreadable chapters
    between them).

    Only this GUARD is repointed. parse_toc_entries still drives EXTRACTION for
    TOC_DRIVEN_COUNCILS (woollahra, leichhardt) and is deliberately untouched:
    changing what those councils extract is Phase C work, gated on each chapter
    having a measured state first.
    """
    try:
        import pdfplumber

        from scripts.dcp_toc_parse import parse_contents
    except Exception:
        return set()
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            texts = [(p.extract_text() or "") for p in pdf.pages[:max_scan]]
        _status, codes, _entries = parse_contents(texts, max_scan=max_scan)
        return codes
    except Exception:
        return set()


# ── providers ────────────────────────────────────────────────────────────────
def _call_anthropic(pdf_bytes: bytes, prompt: str, default_model: str) -> str:
    """Shared Anthropic Messages API call for both the haiku and sonnet providers
    -- same request shape, only the model differs. AI_MODEL_ID still overrides
    either one explicitly (e.g. pinning an exact dated snapshot)."""
    import anthropic
    client = anthropic.Anthropic()
    data = base64.standard_b64encode(pdf_bytes).decode()
    msg = client.messages.create(
        model=os.getenv("AI_MODEL_ID", default_model),
        # 20000, not 8000: measured live 2026-09-05 on a dense 23-page chunk --
        # extended thinking alone consumed the full 8000-token budget
        # (thinking_tokens=8000, stop_reason='max_tokens') before the model
        # ever wrote an answer, so msg.content held ONLY a ThinkingBlock and
        # _call_anthropic correctly returned "" (empty, not a crash) with
        # nothing to retry into. 20000 left room for both thinking (~16k) and
        # a real 11k-char JSON answer on that same chunk. 32000+ requires
        # streaming (the SDK refuses a >10-minute non-streaming call), which
        # this function does not implement -- stay below that ceiling.
        max_tokens=20000,
        # No explicit temperature: newer Sonnet snapshots reject temperature=0
        # outright ("deprecated for this model"), and the 2026-07 decision doc's
        # own measurement found it "marginal help, no downside" for determinism
        # anyway -- not worth a model-conditional parameter for that.
        messages=[{"role": "user", "content": [
            {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": data}},
            {"type": "text", "text": prompt}]}],
    )
    # Some models (e.g. Sonnet) can prepend a ThinkingBlock before the real
    # text response -- content[0] is not reliably the answer. Take the first
    # block that actually has text.
    for block in msg.content:
        text = getattr(block, "text", None)
        if text is not None:
            return text
    return ""


def _call_haiku(pdf_bytes: bytes, prompt: str = PROMPT) -> str:
    return _call_anthropic(pdf_bytes, prompt, "claude-haiku-4-5")


def _call_sonnet(pdf_bytes: bytes, prompt: str = PROMPT) -> str:
    # AI_MODEL=sonnet: 2026-09-05 -- added after Haiku's own real-chapter error
    # rate proved too high for unreviewed sections (see the 2026-07 decision
    # doc). Same drop-in call shape, no other change; still goes through the
    # same --review -> guards -> human-approval path, nothing auto-commits.
    return _call_anthropic(pdf_bytes, prompt, "claude-sonnet-5")


def _call_mistral(pdf_bytes: bytes, prompt: str = PROMPT) -> str:
    key = os.environ["MISTRAL_API_KEY"]
    b64 = base64.standard_b64encode(pdf_bytes).decode()
    body = {
        "model": os.getenv("AI_MODEL_ID", "mistral-small-latest"),
        "max_tokens": 8000,
        "temperature": 0,  # maximise determinism across quarterly re-extracts
        "response_format": {"type": "json_object"},
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "document_url", "document_url": f"data:application/pdf;base64,{b64}"}]}],
    }
    req = urllib.request.Request(
        "https://api.mistral.ai/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    # 300s: large image-heavy chapter PDFs (20 MB+) can push a single chunk past the
    # old 180s. Read timeouts are also made retryable in _is_retryable.
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.load(r)["choices"][0]["message"]["content"]


_PROVIDERS = {"haiku": _call_haiku, "sonnet": _call_sonnet, "mistral": _call_mistral}


def _is_retryable(exc: Exception) -> bool:
    if isinstance(exc, urllib.error.HTTPError):
        return exc.code in (429, 500, 502, 503, 529)
    # Read/connect timeouts and transient network errors (urllib URLError wraps
    # socket.timeout; socket.timeout is TimeoutError on 3.10+) — retry them.
    if isinstance(exc, (TimeoutError, urllib.error.URLError)):
        return True
    name = type(exc).__name__
    status = getattr(exc, "status_code", None)
    return name in ("RateLimitError", "OverloadedError", "APIStatusError", "APITimeoutError") \
        or status in (429, 500, 502, 503, 529)


def _call_with_retry(model: str, pdf_bytes: bytes, prompt: str = PROMPT) -> str:
    fn = _PROVIDERS.get(model)
    if fn is None:
        raise ValueError(f"Unknown AI_MODEL={model!r}. Known: {', '.join(_PROVIDERS)}")
    last: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            return fn(pdf_bytes, prompt)
        except Exception as exc:  # noqa: BLE001 — provider SDKs raise varied types
            last = exc
            if not _is_retryable(exc) or attempt == _MAX_RETRIES - 1:
                raise
            time.sleep(_BACKOFF_BASE * (2 ** attempt))
    raise last  # pragma: no cover


_EMPTY_PARSE_RAW_LEN_FLOOR = 200  # a genuine empty-chunk response is short; longer
                                   # bodies that still parse to nothing are almost
                                   # certainly truncated/malformed, not intentional


def _call_and_parse_with_empty_retry(model: str, pdf_bytes: bytes, prompt: str) -> list[dict]:
    """Call the model and parse its response, retrying when a non-trivial body
    parses to zero provisions. Measured live 2026-09-05: the identical chunk
    request, re-sent, returned 0 provisions once and 46 correctly-parsed
    provisions the next -- _call_with_retry only retries on HTTP-level
    failures, so a 200 response that fails to parse was previously accepted
    as-is, silently losing a whole chunk's content. A real empty page range
    (e.g. a blank/cover-only chunk) gets a short response and is never
    retried."""
    raw = _call_with_retry(model, pdf_bytes, prompt)
    provs = parse_provisions(raw)
    attempts = 0
    while not provs and len(raw) > _EMPTY_PARSE_RAW_LEN_FLOOR and attempts < _EMPTY_PARSE_MAX_RETRIES:
        attempts += 1
        raw = _call_with_retry(model, pdf_bytes, prompt)
        provs = parse_provisions(raw)
    return provs


# ── entrypoint ───────────────────────────────────────────────────────────────
def ai_extract_chapter(pdf_path, council: str | None = None, model: str | None = None) -> list[dict]:
    """Extract a chapter's provisions via an LLM. Returns section dicts matching
    DCPExtractor.extract(). `council` is accepted for signature parity (the model
    needs no per-council config)."""
    from pypdf import PdfReader
    model = (model or os.getenv("AI_MODEL", "mistral")).strip().lower()
    reader = PdfReader(str(pdf_path))
    total = len(reader.pages)
    collected: list[dict] = []
    current_section: str | None = None
    for (a, b) in chunk_ranges(total):
        pdf_bytes = _subset_bytes(reader, a, b)
        prompt = _build_prompt(current_section)
        chunk_provs = _call_and_parse_with_empty_retry(model, pdf_bytes, prompt)
        for p in chunk_provs:
            p.setdefault("page", a + 1)  # approximate: first page of the chunk
            collected.append(p)
        # carry the last real section seen into the next chunk, so a chunk that opens
        # mid-section (its heading fell in this chunk) still qualifies its codes.
        for p in reversed(chunk_provs):
            token = str(p.get("code", "")).split(" ", 1)[0]
            if _SECTION_RE.match(token):
                current_section = token
                break
    return provisions_to_sections(dedupe_provisions(collected))
