"""AI-based DCP chapter extraction — model-agnostic, drop-in for DCPExtractor.extract().

Reads any PDF layout via a document-capable LLM (no per-council regex/config), and
returns section dicts in the SAME shape the regex extractor produces, so the
downstream diff / enqueue / guard pipeline is unchanged.

Enabled by default since 2026-09-21 (#1155); set AI_EXTRACTION=0 to disable.
Model picked by AI_MODEL
(haiku | sonnet | mistral | sol). Validated on the watermarked Woollahra c2: Haiku 141
clean / $0.63, Mistral-small 89 clean / $0.04 (regex got 1 garbage blob). sol (OpenAI
gpt-5.6-sol, OPENAI_API_KEY) added 2026-09-13 when Anthropic credit ran out.

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

# DQ-111. The previous prompt ORDERED a section-qualified code ("MUST be fully
# section-qualified ... e.g. "C4.9 O1"") and gave a concrete example. Where the
# council prints no section number the model had to produce one anyway, and it
# produced the example: Woollahra E2 and Leichhardt Appendix B served "C4.9",
# and Wollongong B1 came back with a "C" on every one of its 61 section codes.
# So: no concrete code anywhere in this prompt, copy only what is printed, and
# when no number is printed give the printed heading words -- never an empty
# code, because an empty code is DROPPED (provisions_to_sections). The fidelity
# gate proves every code against the page (scripts/citation_proof.py); this
# prompt is the first line of defence, not the guarantee.
PROMPT = (
    "This is part of a NSW council Development Control Plan. Extract every provision "
    "(objectives, controls, clauses, requirements, performance criteria, design "
    "solutions). Return a JSON object "
    '{"provisions": [{"code","title","text"}]}. Split each separately labelled '
    "objective or control into its own provision. "
    "The \"code\" is the provision's citation and must be COPIED from the page, never "
    "composed: the section number printed in the heading above the provision, then a "
    "space, then the provision's own label exactly as the page prints it. Copy every "
    "character as printed -- keep the council's own letters, numbers, full stops and "
    "brackets, never add a letter or number the page does not show, never renumber, "
    "and never convert a label into a different style. If no section number is "
    "printed above the provision, use the nearest section number printed above it on "
    "these pages; if the page prints no section number at all, use the words of the "
    "heading printed above the provision instead, followed by its label. If the "
    "provision has no printed label of its own, give the section number or heading "
    "words alone. The code is never empty and never contains anything you cannot see "
    "printed. IGNORE running page headers, footers, page numbers, and any faint "
    "rotated watermark/date characters in the margins. Do not invent provisions. "
    "Output ONLY the JSON object."
)


def _build_prompt(current_section: str | None = None) -> str:
    """PROMPT plus, when a page range continues a section whose heading fell in an
    earlier chunk, that section's printed number -- real data from the previous
    chunk, never an example."""
    if current_section:
        return PROMPT + (
            f" These pages may continue section {current_section} from earlier pages: a "
            f"provision that appears before the next printed section heading belongs to "
            f"it, so its code starts with {current_section}."
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
    """Drop provisions with no/blank code, and exact repeats (same code AND text). Pure.

    Keyed on code alone this dropped every later rule that shared a code with an
    earlier one, silently. Councils repeat labels per section ("C1" under every
    heading) and a faithful reader copies them, so two different rules can share
    a code; the extractor downstream already suffixes a repeated number whose
    text differs (``_2``), so keeping both loses nothing.
    """
    seen: set[tuple[str, str]] = set()
    out: list[dict] = []
    for p in provs:
        code = str(p.get("code", "")).strip()
        key = (code, " ".join(str(p.get("text") or "").split()))
        if code and key not in seen:
            seen.add(key)
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
# Below this share of the document's listed sections actually appearing as
# distinct extracted section codes, the extraction has collapsed the chapter
# into a few parent codes. Measured: collapsed 0.05-0.21, healthy 0.85-0.91.
ATTRIBUTION_MIN_RATIO = 0.5


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


def attribution_collapsed(extracted_codes: set[str], toc_codes: set[str]) -> tuple[bool, int, int]:
    """Did this extraction file a whole chapter under a handful of section codes?

    -> (collapsed, distinct_sections_extracted, sections_listed)

    MARRICKVILLE'S DOMINANT DEFECT, proven 2026-09-12 and invisible to every
    other guard here. part2-s25-stormwater stores 40 provisions against a
    document listing 19 sections, and all 40 carry the code "2.25" with a
    control marker. The 19 real sub-sections -- 2.25.1 through 2.25.3.14 -- were
    never recorded, so not one can be retrieved.

    coverage_gap does NOT catch this. It asks whether TOC codes are covered, and
    a parent code covers its children by the dotted-prefix rule, so a chapter
    filed entirely under 2.25 looks partially covered rather than collapsed.
    truncation_rate does not catch it either: the text is complete, it is the
    ADDRESSING that is gone.

    Measured separation, not a chosen threshold: collapsed chapters carry 5-21%
    of their listed sections, healthy ones 85-91%.

    Returns collapsed=False when the TOC is too small to judge. That is not a
    pass being handed out -- coverage_unknown already covers an unreadable
    contents page, and this guard deliberately does not double-report it.
    """
    if len(toc_codes) < COVERAGE_MIN_TOC:
        return False, 0, len(toc_codes)
    sections = {e.split(" ", 1)[0] for e in extracted_codes if e}
    sections = {s for s in sections if s}
    return (len(sections) / len(toc_codes) < ATTRIBUTION_MIN_RATIO,
            len(sections), len(toc_codes))


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


# AI_MODEL=sol, added 2026-09-13. That day Anthropic answered "Your credit balance is
# too low" and Mistral answered 429; the OPENAI_API_KEY in .env reaches Sol, which read
# a test PDF back verbatim. Same contract as every provider here: one PDF chunk and the
# prompt in, the JSON provisions object out, and nothing commits without review.
# Bounded as a (connect, read) pair rather than one number, and the client does not
# retry by itself -- _call_with_retry owns retries, so a failure is not retried twice.
# prior-art-checked: extends this module's own provider table. scripts/sol_common.py
# (the cross-review tool's OpenAI helper) is not reused: it imports qa_report_path,
# which Dockerfile.monitors does not ship, and it sys.exit()s on any API error, which
# would kill a whole extraction batch instead of failing one chunk into the retry path.
SOL_MODEL = "gpt-5.6-sol"
SOL_CONNECT_TIMEOUT = float(os.getenv("AI_SOL_CONNECT_TIMEOUT", "20"))
SOL_READ_TIMEOUT = float(os.getenv("AI_SOL_READ_TIMEOUT", "900"))


def _call_sol(pdf_bytes: bytes, prompt: str = PROMPT) -> str:
    import httpx
    import openai
    key = (os.environ.get("OPENAI_API_KEY") or "").strip()
    if not key:
        raise RuntimeError("AI_MODEL=sol needs OPENAI_API_KEY in the environment")
    client = openai.OpenAI(
        api_key=key,
        timeout=httpx.Timeout(SOL_READ_TIMEOUT, connect=SOL_CONNECT_TIMEOUT),
        max_retries=0,
    )
    data = base64.standard_b64encode(pdf_bytes).decode()
    response = client.chat.completions.create(
        model=os.getenv("AI_MODEL_ID", SOL_MODEL),
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": [
            {"type": "file", "file": {"filename": "chunk.pdf",
                                      "file_data": f"data:application/pdf;base64,{data}"}},
            {"type": "text", "text": prompt}]}],
    )
    choice = response.choices[0] if response.choices else None
    return getattr(getattr(choice, "message", None), "content", None) or ""


_PROVIDERS = {"haiku": _call_haiku, "sonnet": _call_sonnet, "mistral": _call_mistral,
              "sol": _call_sol}


def _is_retryable(exc: Exception) -> bool:
    if isinstance(exc, urllib.error.HTTPError):
        return exc.code in (429, 500, 502, 503, 529)
    # Read/connect timeouts and transient network errors (urllib URLError wraps
    # socket.timeout; socket.timeout is TimeoutError on 3.10+) — retry them.
    if isinstance(exc, (TimeoutError, urllib.error.URLError)):
        return True
    name = type(exc).__name__
    status = getattr(exc, "status_code", None)
    # APIConnectionError: the OpenAI SDK's dropped-connection error carries no status
    # code, so without its name here a reset socket mid-chapter would fail the chapter.
    return name in ("RateLimitError", "OverloadedError", "APIStatusError", "APITimeoutError",
                    "APIConnectionError") \
        or status in (429, 500, 502, 503, 529)


#: Preference order when AI_MODEL is unset, by EVIDENCE OF WORKING ON A REAL CHAPTER
#: rather than by price. sonnet was hand-verified on marrickville/part7-s3-sex-industry
#: -- 49 of 49 objectives and controls, every section number correct -- and was added
#: on 2026-09-05 precisely because haiku made a real-chapter error. mistral is the
#: cheapest and was the old default, but it answered 429 on both attempts that have
#: ever been made with it, and its key is not present in every environment.
_MODEL_PREFERENCE = (
    ("sonnet", "ANTHROPIC_API_KEY"),
    ("haiku", "ANTHROPIC_API_KEY"),
    ("sol", "OPENAI_API_KEY"),
    ("mistral", "MISTRAL_API_KEY"),
)


def configured_model() -> str | None:
    """The model this environment can actually use, or None when no key is set.

    Callers use this to decide whether the LLM path is available at all, without
    catching an exception to find out. _default_model raises because by the time the
    extractor is choosing a provider there is no sensible answer but to stop; this is
    the question asked one step earlier, where "not available here" is a real state.
    """
    try:
        return _default_model()
    except RuntimeError:
        return None


def _default_model() -> str:
    """The first model whose key is actually present.

    AI_MODEL used to default to "mistral" unconditionally and _call_mistral reads
    os.environ["MISTRAL_API_KEY"] with no guard. That was survivable while extraction
    was opt-in: nobody reached it without choosing to. #1155 made extraction the
    default on 2026-09-21, which put a bare KeyError on the path every chapter now
    takes, in an environment where that key is not set -- the same shape as the
    data-watch job that died on os.environ["PGHOST"] the same night and blocked every
    merge for three days.

    Choosing by what is configured, rather than failing on what is not, means a
    correctly-provisioned environment just works. An environment with NO provider key
    still fails -- it must -- but it fails naming every key it looked for instead of
    the one that happened to be read first.
    """
    for name, env_key in _MODEL_PREFERENCE:
        if (os.getenv(env_key) or "").strip():
            return name
    raise RuntimeError(
        "AI extraction is enabled but no provider key is set. Looked for: "
        + ", ".join(sorted({k for _n, k in _MODEL_PREFERENCE}))
        + ". Set one, or set AI_EXTRACTION=0 to use the regex reader (which needs "
          "per-council config and is why the LLM path is the default).")


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


# ── silent chunk loss: the marrickville cause, proven 2026-09-12 ─────────────
# ai_extract_chapter splits a chapter into AI_CHUNK_PAGES-page chunks. A chunk
# could return zero provisions and this function simply collected nothing for it
# and moved on -- no count, no flag, no error. The chapter was then committed
# missing that chunk's entire content, and nothing anywhere recorded it.
#
# PROVEN, not inferred. marrickville/part4-s1-low-density (55pp, chunks 1-30 and
# 31-55): every stored row sits on page 31, so chunk 1 produced nothing. All 14
# of its sampled "missing" sections -- 4.1.1, 4.1.10 … 4.1.15.1 -- are present in
# the PDF on pages 3-29, inside that empty chunk. Across three chapters, 42 of 42
# checked missing sections were in the document, inside a chunk that yielded
# nothing; ZERO were absent from the PDF. The contents page was not lying.
#
# Chapters affected (2026-09-12): 15 across 7 councils, 558 pages of source
# document never extracted, of which marrickville is 4 chapters and 94 pages.
#
# A chunk that is genuinely blank -- a cover, a plate of maps, a scanned image
# run -- SHOULD return nothing, so emptiness alone is not the signal. The signal
# is emptiness from a chunk that demonstrably contains text.
CHUNK_LOSS_MIN_TEXT_CHARS = 1500   # a 30-page chunk of controls is far above this


class ChunkLoss(Exception):
    """A chunk containing substantial text returned no provisions."""


#: Words a page must carry to be able to hold a rule. A page with none of them
#: -- a contents page, a suburb history, a glossary -- legitimately yields no
#: provisions, and an empty answer for it is not content loss.
_RULE_LANGUAGE = re.compile(
    r"\b(shall|must|should|required|requirements?|minimum|maximum|controls?|objectives?|"
    r"not permitted|is to be|are to be)\b", re.IGNORECASE)


def _is_contents_page(text: str) -> bool:
    """Most lines end in a page number: a table of contents, not rules."""
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    if len(lines) < 8:
        return False
    return sum(1 for ln in lines if ln[-1:].isdigit()) / len(lines) >= 0.5


def _chunk_rule_chars(reader, a: int, b: int) -> int:
    """Characters in pages [a, b) that COULD hold a rule: not a contents page,
    and carrying rule language. What the chunk-loss guard should weigh.

    Leichhardt part-c-s2 was refused twice (2026-09-24) for pages 1-12: five
    contents pages and seven suburb-history profiles, 31,028 characters and not
    one control -- the model was right to return nothing. Counting all text made
    that indistinguishable from the marrickville loss this guard exists for. A
    page pypdf cannot read still counts in full, as before.
    """
    total = 0
    for i in range(a, min(b, len(reader.pages))):
        try:
            text = reader.pages[i].extract_text() or ""
        except Exception:
            total += CHUNK_LOSS_MIN_TEXT_CHARS
            continue
        if _is_contents_page(text) or not _RULE_LANGUAGE.search(text):
            continue
        total += len(text)
    return total


# ── entrypoint ───────────────────────────────────────────────────────────────
def ai_extract_chapter(pdf_path, council: str | None = None, model: str | None = None) -> list[dict]:
    """Extract a chapter's provisions via an LLM. Returns section dicts matching
    DCPExtractor.extract(). `council` is accepted for signature parity (the model
    needs no per-council config)."""
    from pypdf import PdfReader
    model = (model or os.getenv("AI_MODEL") or _default_model()).strip().lower()
    reader = PdfReader(str(pdf_path))
    total = len(reader.pages)
    collected: list[dict] = []
    current_section: str | None = None
    lost: list[dict] = []
    for (a, b) in chunk_ranges(total):
        pdf_bytes = _subset_bytes(reader, a, b)
        prompt = _build_prompt(current_section)
        chunk_provs = _call_and_parse_with_empty_retry(model, pdf_bytes, prompt)
        if not chunk_provs:
            # FAIL CLOSED. Zero provisions from a chunk that holds real text is
            # content loss, and accepting it silently is what cost marrickville
            # 94 pages of source document. A genuinely blank chunk has no text
            # and is passed over without complaint.
            chars = _chunk_rule_chars(reader, a, b)
            if chars >= CHUNK_LOSS_MIN_TEXT_CHARS:
                lost.append({"pages": (a + 1, b), "text_chars": chars})
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
    if lost:
        pages = ", ".join(str(x["pages"][0]) + "-" + str(x["pages"][1]) for x in lost)
        chars = sum(x["text_chars"] for x in lost)
        raise ChunkLoss(
            str(len(lost)) + " of " + str(len(chunk_ranges(total))) + " chunks "
            "returned NO provisions while holding " + str(chars) + " characters "
            "of rule-bearing text (pages " + pages + "). Refusing to return a partial chapter: "
            "committing it would silently drop those pages, which is how "
            "marrickville lost 94 pages of source across 4 chapters.")
    return provisions_to_sections(dedupe_provisions(collected))
